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
| Punctuation "just works" | **yes** | mostly — in block style only `: ` (colon-space) and leading `#` (hex colors) need quoting | no — `&gt;` `&amp;` escaping |
| Structure doubles as display markdown | **yes** | no (fields, or embed markdown) | no (elements, or embed markdown) |
| Generic tooling / schema validation | no | yes | **yes (XSD)** |
| Explicit structure (no ambiguity) | no (heading depth) | mostly | **yes** |

## Why AMD wins for this file

This is prose — dialogue, lore, quest copy — authored and edited by a writer, and
rendered straight to the player. On that job AMD dominates:

- **It disappears.** Storm's lines read like a screenplay; the choices read like
  choices. In XML every one of those lines is buried in `<line>...</line>`; in YAML
  they're list items behind `text:`/`lines:` scaffolding.
- **No escaping tax.** AMD carries all punctuation for free because prose is the
  default, not a quoted exception. XML always pays it — `&gt;=` for
  `if credits >= 400`, `&amp;` for `&`. YAML's tax is smaller but real (see below).
- **One representation for structure and display.** An AMD body *is* the display
  markdown — its `#`/`-`/`image://` lines pass straight to gui_text_area. This isn't
  a rendering *advantage* (all three parse to the same tree, and the same string
  renders the same wherever it came from); it's that AMD needs no second
  representation. The translations either embed the same markdown in a scalar/element
  (renders identically) or decompose it into fields a loader must map back to display.
- **Smallest on disk**, despite being the most readable — the tell that it has the
  least ceremony.

XML's only real wins (schema validation, unambiguous nesting) don't matter for
hand-authored narrative, and it pays for them with the worst readability and the
heaviest escaping. It's the clear *loser* here.

## The YAML tax: flow vs block

YAML's punctuation cost depends entirely on which style you write. In **flow** style
(`{text: ..., target: ...}`), `,` is a structural separator and `?`/`:` are
indicators, so dialogue punctuation breaks — and worse, some of it breaks silently:

- `{text: Not today, boys}` does not error; it parses to
  `{'text': 'Not today', 'boys': None}` — quiet data corruption.
- `{text: ...Skarr?...}` throws a hard parse error on the `?`.

This is standard-spec behavior, not an engine quirk or a weak parser — `sbs_utils`
bundles standard PyYAML, and any compliant parser must treat flow context this way.
In **block** style the problem disappears: commas, question marks, and `>=`
conditions are all fine as plain scalars. Only two cases still need quoting,
independent of style — colon-space (`Dobbs: Hi. Whatever.`) and a value starting
with `#` (hex colors like `"#6cf"`, since `#` begins a comment). `stormsbeacon.yaml`
uses block style throughout, so those are the only quoted values in it.

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
