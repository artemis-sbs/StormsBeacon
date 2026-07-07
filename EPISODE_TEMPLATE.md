# Storm's Beacon — Episode Template

The repeatable unit of the campaign. Adding an episode is **two mechanical edits** and
**no new logic**. This is the "locked" template from STORMS_BEACON.md §12 (Phase 0 step 3);
episodes 1–3 in `stormsbeacon.amd` are the worked examples.

Each episode is: **Storm reveals a heading → you Engage-jump there → the ruin sits in
terrain, contested by guards → you scan it → hail Storm for the next lead.**

---

## The two edits

### Edit 1 — author the episode's chapters + landmark (`stormsbeacon.amd`)

Under the `### The Beacon Hunt (beacon_arc)` arc, add a **go** step and a **scan** step
(`####` headings = nested quest keys `beacon_arc/<key>`). Both start `State: secret` —
Storm's dispatcher flips them active. The `go` step's `When: reach i, j` is the jump goal;
the `scan` step's `When: scan 1 derelict` completes the episode.

```
#### Storm's Lead N (epN_go)
---
Scope: shared
State: secret
When: reach <i>, <j>
Then: reveal beacon_arc/epN_scan
---
<Storm's in-fiction reason this system is the next heading. Engage and jump.>

#### The <Ruin Name> (epN_scan)
---
Scope: shared
State: secret
When: scan 1 derelict
Pays: <credits>            # omit on the terminal episode; use Win instead
---
<What the ruin is; scan it, then hail Storm.>
```

**Terminal (finale) episode.** The campaign's win is **not** a plain `Win: true` on a scan —
it's a **gated assembly** (the "assemble the Beacon" design). The origin's `scan` step just
brings the array online; the win is a separate goal that fires on a signal the dispatcher
emits only when every piece is present:

```
## Goals

### Light the Beacon (goal_light)
---
Scope: shared
State: active
When: signal beacon_lit
Win: true
Citation: <the end-of-run summary shown on the victory screen>
---
<what the player must gather + do>
```

The Storm dispatcher (story.mast) emits `beacon_lit` only when the four scanned pieces are
done AND the `beacon_cradle` flag is set (bought from Eddy) — so a **non-scan piece** (the
Cradle) and the **assembly gate** are the puzzle. To add another required non-scan piece:
set a flag in its acquisition route, check it in the dispatcher's assembly branch, and add a
`get_<piece>` objective revealed via an `also` field on the lead that mentions it.

Then add the episode's **landmark** in `## Landmarks`, pinned to the same `(i, j)`:

```
### <Ruin Name> (<key>)
---
At: <i>, <j>
Kind: derelict
Terrain: nebula <color>   # or `Terrain: asteroids` — wraps the ruin in cover (optional)
Guards: <race> <difficulty>   # a fleet contesting the ruin on arrival (optional)
---
<Flavor: what the ruin is, and who got here first.>
```

- **`Terrain:`** `nebula [color]` (color = a name the engine knows, e.g. `blue`/`violet`/
  `red`) or `asteroids`. Guarantees the ruin sits in terrain regardless of the cell's
  rolled kind. Omit for a bare-space ruin.
- **`Guards:`** `<race> [difficulty]` (e.g. `skaraan 2`, `torgoth 3`) — a
  `prefab_fleet_raider` spawned near the ruin on arrival. **One-shot**: a persisted
  `guards_cleared` flag means a revisit doesn't re-ambush. Omit for an unguarded ruin.
  Difficulty defaults to the mission's if omitted. Both `Terrain:` and `Guards:` are
  `universe_core` landmark features (`universe_landmarks.py`), reusable by any universe.

### Edit 2 — append one row to the dispatcher (`story.mast`)

In the `//signal/storm_check` route, add a row to the `_eps` list (order = play order):

```
{"go": "epN_go", "scan": "epN_scan",
 "lead": "<Storm's line when she reveals this heading>",
 "nudge": "<Storm's line while it's on the map but unscanned>"},
```

That's it. The dispatcher walks `_eps` and hands out the first not-yet-scanned episode, so
no per-episode `if/elif` is ever needed. The first row also clears the opening briefing.

---

## Slots reserved for later phases (author now, wire later)

- **Reputation branch (Phase 2).** A `## Regions` block already gives the episode systems
  geography (skybox/music/map-tint/generation-mix). When reputation lands, gate a `lead`/
  `nudge` variant or an alternate `scan` resolution on a clan standing. Keep the `_eps`
  row shape; add a `lead_low`/`lead_high` pair rather than a new code path.
- **XORN beat (Phase 1).** An episode can carry a scripted XORN confrontation. Likely a
  `When: signal` step or a dwell-timer complication layered on the `go`/`scan` pair — TBD
  when the XORN pursuit mechanic exists.

## Verify

1. `--test` — compiles / doesn't desync (a broken multi-line literal shows as `labels 0/N`).
2. Browser — jump to the episode's `(i, j)`: confirm the ruin sits in its terrain, the
   guards contest it, scanning completes the step, and hailing Storm hands out the next lead
   (or the victory screen on the finale).
