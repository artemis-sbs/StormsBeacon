"""Prof. Storm's Ultra-Beam nudge: a COMMS MESSAGE, not an incoming hail.

stormsbeacon.amd tells the AUTHOR eleven times to "hail her on the Ultra-Beam (no target
selected)". It never told the PLAYER. Storm, Vex, Eddy and Skarr are all host-less
advisors reachable only that way, so a crew who never discover that one menu never meet
the cast at all - and nothing on screen hints that comms does anything with no contact
selected.

So Storm mentions it herself, occasionally, and stops once they have used it.

What this pins, which a headless run CANNOT show (her cadence is 4-7 minutes and
URGE_PASS_SECONDS is 30, so a 60-second conformance run proves only that nothing threw):

* the urges parse off the real shipped .amd,
* the `Urge` marker guard keeps her prose out of her urge list,
* the nudge is gated on the lesson and retires when she is reached,
* and speaking takes urge_speak's UNHOSTED branch - comms_message, her own face and
  color, no hail queue, no choice strip.

    python tests/test_ultra_beam_urges.py        (from the StormsBeacon dir; exits 0/1)
"""
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
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.quest import document_get_amd_file
from sbs_utils.procedural.amd_urge import urges_from_section, urges_install_on
from sbs_utils.procedural.urge import (
    urge_pick, urge_line, urge_speak, urge_teach_note, urge_teach_reset,
    urge_run_one, urge_budget_reset)
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.roles import add_role


def _doc():
    with open(os.path.join(_MISSION, "stormsbeacon.amd"), encoding="utf-8") as f:
        return document_get_amd_file(None, "SB", content=f.read())


def _find(node, key):
    if node.get("key") == key:
        return node
    for c in node.get("children", []) or []:
        found = _find(c, key)
        if found is not None:
            return found
    return None


class AuthoredUrgeTests(unittest.TestCase):
    """Read off the real shipped file, so a rename or a broken fence fails here."""

    @classmethod
    def setUpClass(cls):
        cls.doc = _doc()

    def _urges(self, who):
        rec = _find(self.doc, who)
        self.assertIsNotNone(rec, f"no cast record {who!r} in stormsbeacon.amd")
        return rec, urges_from_section(rec, require_marker=True)

    def test_storm_has_exactly_one_nudge(self):
        _, urges = self._urges("prof_storm")
        self.assertEqual([u.get("key") for u in urges], ["storm_ultra_beam"])

    def test_storm_jitters_in_minutes(self):
        """A character on an exact metronome reads as a machine."""
        _, urges = self._urges("prof_storm")
        self.assertEqual(urges[0].get("every"), (240.0, 420.0))

    def test_storm_is_gated_and_retires(self):
        _, urges = self._urges("prof_storm")
        u = urges[0]
        # Whenever PAUSES her the moment they find the menu at all - even via Eddy.
        self.assertEqual(u.get("whenever"), "not taught ultra_beam")
        # Until retires her for good once they have actually reached HER.
        self.assertEqual(u.get("until"), "taught hail_storm")

    def test_storm_escalates_over_three_stages(self):
        _, urges = self._urges("prof_storm")
        self.assertEqual(urges[0].get("escalates"), "firing")
        self.assertEqual(sorted((urges[0].get("stages") or {}).keys()), [1, 2, 3])

    def test_vex_defers_to_storm(self):
        """Both are eligible at once; urge_pick takes the highest weight."""
        _, storm = self._urges("prof_storm")
        _, vex = self._urges("chief_vex")
        self.assertGreater(storm[0].get("weight"), vex[0].get("weight"))

    def test_vex_needs_no_until(self):
        """Her Whenever alone silences her - she is not chasing a conversation."""
        _, vex = self._urges("chief_vex")
        self.assertIsNone(vex[0].get("until"))

    def test_every_line_says_how(self):
        """The whole point is the instruction, so no line may be pure flavor."""
        for who in ("prof_storm", "chief_vex"):
            _, urges = self._urges(who)
            lines = list(urges[0].get("pool") or [])
            for stage in (urges[0].get("stages") or {}).values():
                lines.extend(stage)
            self.assertTrue(lines)
            for line in lines:
                self.assertIn("ultra-beam", line.lower(), f"{who}: {line!r}")

    def test_lines_are_ascii(self):
        for who in ("prof_storm", "chief_vex"):
            _, urges = self._urges(who)
            for stage in (urges[0].get("stages") or {}).values():
                for line in stage:
                    line.encode("ascii")
            for line in (urges[0].get("pool") or []):
                line.encode("ascii")

    def test_the_marker_guard_keeps_prose_out(self):
        """A cast record's children are not all urges. Without require_marker the first
        person to add a note under a character gives them a nagging urge that says
        whatever that note happens to be."""
        rec = _find(self.doc, "prof_storm")
        guarded = urges_from_section(rec, require_marker=True)
        for u in guarded:
            self.assertEqual(u.get("key"), "storm_ultra_beam")


class SpeakingTests(unittest.TestCase):
    """Installed on a real host-less lifeform and driven, because the .amd parsing and
    the SPEAKING are different failures."""

    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        urge_teach_reset()
        urge_budget_reset()
        self.doc = _doc()
        # Host-less, exactly as universe.mast spawns an advisor with no `host`.
        self.storm = lifeform_spawn("Professor Storm", "", "storm", None)
        add_role(self.storm, "storm")
        urges_install_on(self.storm, _find(self.doc, "prof_storm"), require_marker=True)

    def tearDown(self):
        urge_teach_reset()
        urge_budget_reset()

    def test_the_urge_installs_onto_the_lifeform(self):
        picked = urge_pick(to_id(self.storm), now=0)
        self.assertIsNotNone(picked)
        self.assertEqual(picked["rec"].get("key"), "storm_ultra_beam")

    def test_she_stops_once_the_menu_is_used(self):
        """LM's //comms/ultra_beam route stamps this the moment the crew open it."""
        self.assertIsNotNone(urge_pick(to_id(self.storm), now=0))
        urge_teach_note("ultra_beam")
        self.assertIsNone(urge_pick(to_id(self.storm), now=0))

    def test_reaching_her_retires_her_for_good(self):
        """story.mast stamps hail_storm in //shared/signal/storm_check."""
        urge_teach_note("hail_storm")
        self.assertIsNone(urge_pick(to_id(self.storm), now=0))
        urge_teach_reset()          # even if the lesson is somehow dropped
        self.assertIsNone(urge_pick(to_id(self.storm), now=0))

    def test_she_speaks_as_a_comms_message_not_a_hail(self):
        """THE REQUIREMENT. A host-less actor takes urge_speak's unhosted branch:
        comms_message to the player ships. It must not queue an incoming hail - a hail
        interrupts, takes the comms console and wants an answer, and a standing reminder
        has earned none of that."""
        from sbs_utils.procedural import comms as C
        from sbs_utils.procedural import hail as H
        sent = []
        real = C.comms_message
        C.comms_message = lambda msg, *a, **kw: sent.append((msg, a, kw))
        offered = []
        real_offer = H.hail_offer
        H.hail_offer = lambda *a, **kw: offered.append(a)
        try:
            picked = urge_pick(to_id(self.storm), now=0)
            ok = urge_speak(to_id(self.storm), urge_line(picked),
                            title=picked["rec"].get("title"))
        finally:
            C.comms_message = real
            H.hail_offer = real_offer
        self.assertTrue(ok)
        self.assertEqual(len(sent), 1)
        self.assertEqual(offered, [], "a nudge must never become an incoming hail")
        self.assertIn("ultra-beam", sent[0][0].lower())
        self.assertEqual(sent[0][2].get("title"), "Ultra-Beam")

    def test_running_the_urge_stamps_its_cooldown(self):
        """So she does not say it again on the very next pass."""
        state = urge_run_one(to_id(self.storm), now=0)
        self.assertIsNotNone(state)
        self.assertGreaterEqual(state["next"], 240.0)


if __name__ == "__main__":
    unittest.main()
