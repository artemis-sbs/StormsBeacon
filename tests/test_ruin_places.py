"""Every ruin's places, scenes and side stories, read off the SHIPPED relic files.

A place says something when a crew member's suit arrives (`Scene:` on a relic point,
opened in the xESS Act app), its choices roll checks and open ways, and each ruin carries
one side story per job. All of that is data in `relics/*.amd`, so the failures are all of
the silent kind - a scene key with a typo is a place that says nothing, a choice pointing
at a missing scene ends the conversation, a `Leads to:` naming a place in another ruin
marks nothing on the Nav list. This walks the real files rather than a fixture.

What it cannot show: how a scene READS on a bridge, or the art. That is the engine's.

    python -m unittest tests.test_ruin_places        (from the StormsBeacon folder)
"""
import glob
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_MISSION = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.abspath(os.path.join(_MISSION, "..", "sbs_utils")))

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes            # noqa: F401  breaks a circular import
from cosmos_dev.mock import sbs
from sbs_utils.gui import GuiClient
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.procedural import amd_dialogue as D
from sbs_utils.procedural import amd_relics as R
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import boarding_checks as C
from sbs_utils.procedural import eva as E
from sbs_utils.procedural import eva_places as P
from sbs_utils.procedural import rails as RL
from sbs_utils.procedural import volume as V
from sbs_utils.procedural.amd_doc import amd_section
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.quest import document_get_amd_file
from sbs_utils.procedural.signal import signal_observe, signal_unobserve

RELIC_FILES = sorted(glob.glob(os.path.join(_MISSION, "relics", "*.amd")))
JOBS = ("helm", "weapons", "science", "engineering", "comms")
CID = 0x8000000000000001


def _dialogue_keys(path):
    doc = document_get_amd_file(path)
    section = amd_section(doc, "dialogue")
    return {str(n.get("key")).lower(): n for n in (section or {}).get("children", [])}


class _Base(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        TickDispatcher.clear()
        V.volume_clear()
        RL.rail_clear()
        E.eva_clear()
        P.eva_places_clear()
        R.relics_clear()
        A.boarding_clear()
        D.dialogue_scenes_registry_clear()
        self._prev = D._METRIC_RESOLVER
        A.boarding_metric_install()
        C.boarding_checks_mode("flat")
        GuiClient(CID)
        self.events = []
        signal_observe(self._watch)

    def tearDown(self):
        signal_unobserve(self._watch)
        A.boarding_clear()
        D.dialogue_set_metric_resolver(self._prev)
        P.eva_places_clear()
        E.eva_clear()
        R.relics_clear()
        RL.rail_clear()
        V.volume_clear()
        TickDispatcher.clear()

    def _watch(self, name, data=None):
        self.events.append((name, dict(data or {})))

    def load(self, path):
        recs = R.relics_load(path)
        for rec in recs:
            R.relic_volume(rec)
            R.relic_rails_ensure(rec.get("key"))
            R.relic_contents_arm(rec.get("key"))
        return recs

    def crew(self, relic, at, skill=7):
        """One crew member who holds every job, very good at all of them - so every
        guard opens and every check passes, and the whole graph can be walked."""
        who = lifeform_spawn("Lt Tester", "terran_male", "boarding," + ",".join(JOBS))
        A.boarding_assign(CID, who)
        C.boarding_skills_set(who, {j: skill for j in JOBS})
        suit = E.eva_suit_spawn(who, relic, at[0], at[1], at[2], hull="tsn_shuttle",
                                side="tsn")
        E.eva_take(CID, suit, relic, volume=relic)
        return who


class TheFilesAreWhole(unittest.TestCase):
    def test_there_are_relic_files(self):
        self.assertTrue(RELIC_FILES)

    def test_every_place_scene_is_in_its_own_file(self):
        for path in RELIC_FILES:
            R.relics_clear()
            keys = _dialogue_keys(path)
            for rec in R.relics_load(path):
                for part, info in (rec.get("part_info") or {}).items():
                    if info.get("scene"):
                        self.assertIn(str(info["scene"]).lower(), keys,
                                      "%s: %s names a scene that is not there"
                                      % (os.path.basename(path), part))

    def test_every_choice_goes_somewhere(self):
        for path in RELIC_FILES:
            keys = _dialogue_keys(path)
            for key, node in keys.items():
                parsed = D.dialogue_parse(node)
                for ch in parsed.get("choices") or []:
                    target = str(ch.get("target") or "").strip().lower()
                    if target:
                        self.assertIn(target, keys, "%s: %s -> %s goes nowhere"
                                      % (os.path.basename(path), key, target))

    def test_side_stories_lead_to_places_in_their_own_ruin(self):
        for path in RELIC_FILES:
            R.relics_clear()
            recs = R.relics_load(path)
            points = set()
            for rec in recs:
                points |= set((rec.get("points") or {}).keys())
            section = amd_section(document_get_amd_file(path), "side_stories")
            for n in (section or {}).get("children", []):
                data = n.get("data") or {}
                self.assertIn(str(data.get("for")).lower(), JOBS,
                              "%s: %s is for nobody aboard" % (path, n.get("key")))
                leads = data.get("leads_to") or ""
                for lead in [x.strip().lower() for x in str(leads).split(",") if x.strip()]:
                    self.assertIn(lead, points, "%s: %s leads to %s, which is not a "
                                  "place in this ruin" % (os.path.basename(path),
                                                          n.get("key"), lead))


class EveryPlaceSpeaks(_Base):
    def walk(self, relic, point, channel):
        """Take every choice of every beat reachable from a place's scene."""
        seen = set()
        frontier = [A.boarding_scene(channel)]
        steps = 0
        while frontier and steps < 200:
            key = frontier.pop()
            if key in seen or key is None:
                continue
            seen.add(key)
            choices = A.boarding_choices(CID)
            for i in range(len(choices)):
                steps += 1
                A.boarding_scene_begin(D.dialogue_registered_scenes(), key, channel=channel)
                A.boarding_channel_join(CID, channel)
                labels = A.boarding_choices(CID)
                self.assertTrue(A.boarding_answer(CID, i),
                                "%s: '%s' refused" % (key, labels[i].get("label")))
                nxt = A.boarding_scene(channel)
                if nxt and A.boarding_is_open(channel):
                    frontier.append(nxt)
            A.boarding_channel_close(channel)
            ch = P.eva_place_channel(relic, point)
            A.boarding_channel_open(ch, [CID])
        return seen

    def test_every_place_opens_and_every_branch_answers(self):
        for path in RELIC_FILES:
            self.setUp()
            for rec in self.load(path):
                relic = rec.get("key")
                for part, info in (rec.get("part_info") or {}).items():
                    if not info.get("scene"):
                        continue
                    pos = R.relic_point(relic, part)
                    self.assertIsNotNone(pos, "%s: a scene on a part that is not a point"
                                         % part)
                    self.crew(relic, pos)
                    ch = P.eva_place_arrive(CID, relic, part)
                    self.assertTrue(ch, "%s: %s did not open" % (relic, part))
                    line = A.boarding_line(ch)
                    self.assertTrue(str(line).strip(), "%s: %s opened silent"
                                    % (relic, part))
                    self.walk(relic, part, ch)
                    A.boarding_clear()
                    A.boarding_metric_install()
                    E.eva_clear()
            self.tearDown()


class TheVoice(_Base):
    def setUp(self):
        super().setUp()
        self.load(os.path.join(_MISSION, "relics", "voice.amd"))

    def pick(self, label):
        labels = [c.get("label") for c in A.boarding_choices(CID)]
        self.assertIn(label, labels)
        return A.boarding_answer(CID, labels.index(label))

    def test_waking_the_consoles_finds_the_alcove(self):
        self.crew("voice", R.relic_point("voice", "at_concourse"))
        self.assertTrue(RL.rail_is_hidden("voice", "voice_dispatch"))
        P.eva_place_arrive(CID, "voice", "at_concourse")
        self.pick("Wake the console bank")
        self.assertFalse(RL.rail_is_hidden("voice", "voice_dispatch"))
        self.assertIn("voice_console_woken", [n for n, _ in self.events])

    def test_a_weak_hand_does_not_find_it(self):
        self.crew("voice", R.relic_point("voice", "at_concourse"), skill=0)
        P.eva_place_arrive(CID, "voice", "at_concourse")
        self.pick("Wake the console bank")         # 5 + 0 < 8
        self.assertTrue(RL.rail_is_hidden("voice", "voice_dispatch"))
        self.assertEqual(A.boarding_scene(P.eva_place_channel("voice", "at_concourse")),
                         "voice_console_sparks")

    def test_the_grate_worked_free_opens_the_shaft(self):
        self.crew("voice", R.relic_point("voice", "at_shaft"))
        self.assertTrue(RL.rail_barriers("voice", shut_only=True))
        P.eva_place_arrive(CID, "voice", "at_shaft")
        self.pick("Work the grate free")
        opened = [d.get("RAIL_BARRIER") for n, d in self.events if n == "rail_opened"]
        self.assertEqual(opened, ["shaft_grate"])

    def test_storm_speaks_in_the_bay_with_her_face(self):
        self.crew("voice", R.relic_point("voice", "at_bay"))
        ch = P.eva_place_arrive(CID, "voice", "at_bay")
        self.pick("Call Storm")
        node = D.dialogue_registered_scenes().get(A.boarding_scene(ch))
        self.assertEqual((node.get("data") or {}).get("speaker"), "prof_storm")


if __name__ == "__main__":
    unittest.main()
