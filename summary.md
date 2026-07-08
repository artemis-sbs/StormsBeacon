# Storm's Beacon: AMD vs YAML vs XML

Comparison of the same mission content (`stormsbeacon.amd`) expressed in three
formats: the native AMD source, and 1:1 translations to `stormsbeacon.yaml` and
`stormsbeacon.xml`.

## The scoreboard

| | AMD | YAML | XML |
|---|---|---|---|
| Bytes | **20.5k** | 24.2k | 25.7k |
| Lines | 574 | 553 | 423 |
| Reads as prose/script | **yes** | partly | no |
| Punctuation "just works" | **yes** | no — `,` `?` `:` need quoting | no — `&gt;` `&amp;` escaping |
| Renders in-game as-is (`#` headings) | **yes** | no | no |
| Generic tooling / schema validation | no | yes | **yes (XSD)** |
| Explicit structure (no ambiguity) | no (heading depth) | mostly | **yes** |

## Why AMD wins for this file

This is prose — dialogue, lore, quest copy — authored and edited by a writer, and
rendered straight to the player. On that job AMD dominates:

- **It disappears.** Storm's lines read like a screenplay; the choices read like
  choices. In XML every one of those lines is buried in `<line>...</line>`; in YAML
  they're list items behind `text:`/`lines:` scaffolding.
- **No escaping tax.** Proven during the conversion: in YAML, `"Not today, boys"`
  and `"What do you make of XORN?"` *broke the parse* until quoted; XML needs
  `&gt;=` for `if credits >= 400`. AMD carries all that punctuation for free because
  prose is the default, not a quoted exception.
- **Zero wiring.** The `#` headings *are* the rendered gui_text_area markdown. The
  other two are pure data — something still has to render them.
- **Smallest on disk**, despite being the most readable — the tell that it has the
  least ceremony.

XML's only real wins (schema validation, unambiguous nesting) don't matter for
hand-authored narrative, and it pays for them with the worst readability and the
heaviest escaping. It's the clear *loser* here.

## The caveat

The ranking flips entirely if the job changes. If something *external* has to
consume this — a web editor, a validator, an import pipeline — then you want a data
language, and there **YAML beats XML**: less noise, and it's already the format
`sbs_utils` bundles (`from sbs_utils import yaml`), so it's Python-native with no new
dependency. XML only pulls ahead if you specifically need XSD-enforced schema
guarantees, which this project doesn't.

## Verdict

- **AMD for authoring** (the actual use case) — decisively.
- **YAML** if you ever need a machine-readable sidecar.
- **XML** for neither.

Which is exactly why the format is markdown and not one of the two translations.
