---
name: scene-audit
description: "Audit every illustrated scene of a book at the object level: inventory the renders, map 10 to 20 objects per scene, inspect each one zoomed, describe what every character does, check against the production document, verify each finding in an independent second pass, and build a Hebrew report with a decision queue. Use when asked to scan, review or audit book illustrations, renders or scenes, or to recheck a scene after a re-render. גם לביקורת סצנות, סריקת תמונות, בדיקת איורים, פגמים באיורים, תגי «מצאו», פס פריטים, בדיקה חוזרת אחרי רינדור."
---

# Scene audit

You audit illustrated book scenes. Scripts do what can be measured (inventory, crops, boxes, reports). You do the looking. Every finding carries a location, a type, a severity and a confidence, because a defect that reaches print is expensive and a wrong finding costs trust.

The `scene-audit` command must be installed (`pip install -e <path-to>/scene-audit`). Check with `scene-audit --version`. If it is missing, stop and say so.

## What you do and do not do

- You never generate, edit or re-render an image. You write fix instructions; rendering happens in the creation tool.
- You never decide for the owner. Taste, culture and religion are reported as questions.
- You check lettering that appears inside the image only, not the book's text.
- You never write to the `scenes/` folder. Source renders are read only.
- You never start a re-render. You ask.

## Ground rules for accuracy

1. The production document (the spec) outranks every general rule, this skill included.
2. Without the spec there is only opinion. If `scene-audit scan` says the spec is missing, stop and ask for it.
3. Never trust one look at a full frame. Every object gets its own zoomed look, alone and in context.
4. Something too small to judge at the resolution you checked is «לוודא» (`confidence: verify`). It counts neither as a defect nor as fine. Do not guess.
5. Before you write "the spec does not cover this", run `scene-audit spec-search <term>` with the Hebrew term, an alternative spelling, and the English word. Write it only if all searches come back empty.
6. If the spec asked for something and the render delivered it, that is not a defect. A proposal to change the spec is written separately as a `suggestion`.
7. A review by another tool (`paths.prior_reviews`) is a list of claims to check against the image and the spec, never facts.
8. `confidence: certain` only after the second pass confirmed the finding. The validator enforces it.

## Coordinates

Every image you look at is a *view* listed in `work/scene-NN/views.json` (full frame, tiles, object crops, gap views, verify crops). Draw boxes in the pixels of the view you are looking at and name the view. The tool converts to source pixels:

- In `candidates.json`: `"view": "r2c3", "bbox": [x1, y1, x2, y2]`.
- In a finding or a count instance: `"view": "07-03", "view_bbox": [x1, y1, x2, y2]`. `scene-audit validate` fills `bbox` in source pixels.
- One-off conversion: `scene-audit coords --scene 07 --view 07-03 --bbox 120,80,300,260`.

Boxes are `[x1, y1, x2, y2]`, origin top left. The image size of each view is in `views.json` (`view_size`).

## Workflow

Run commands from the book folder (the one with `book.yaml`), or pass `--book`. `scene-audit status` shows every scene's stage and its next step at any time, so the work can stop and resume.

### 0. Set up

If there is no `book.yaml`, run `scene-audit init --scenes <renders folder> --spec <spec file or folder> --layout single|spread`. Ask the owner only what the files cannot answer: page or spread and size in pixels, fix threshold (critical only, or medium too), whether the book has «מצאו» tags, an item strip, a word list. Record the answers in `book.yaml`.

### 1. Inventory and contact sheet

`scene-audit inventory`. Report format issues, files the tracking sheets point at that are not the current renders, and renders the sheets miss. Open `out/contact-sheet.jpg` and judge style consistency across the book (ST) in one look. Note any scene that drifts.

### 2. Rules from the spec

1. `scene-audit rules` extracts the spec to `work/spec.txt` with section numbers in `work/spec-sections.json`, and creates `work/rules.yaml`.
2. Read all of `work/spec.txt`. Fill `rules.yaml`: characters and their locked identity marks, style, forbidden elements, safety, audience, «מצאו» tags with expected counts, the word list, spread rules, and per-scene `must_show` and `expected_objects`. Every rule keeps `spec_ref`, the section number it came from. Delete template rows you do not use.
3. `scene-audit rules --check` until clean.
4. Show the owner a short summary of the rules and ask for approval. Run `scene-audit rules --approve` only after the owner says yes, in this conversation. This happens once per book, again only if the spec changes.

### 3. Scan

`scene-audit scan --all` prepares every scene that is new or changed: a full view and a 3x3 grid of overlapping tiles. Unchanged scenes that are done are skipped by hash.

For a book with more than three scenes, give each scene to its own subagent (steps 4 to 6) so that each one keeps its full attention on one scene. Give it this skill's path, the book folder and the scene id. Run the second pass (step 7) in a different subagent.

### 4. Map the objects (per scene)

1. Open `work/scene-NN/full.png`, then every tile in `work/scene-NN/tiles/`. Look at the edges and the background on purpose.
2. Write `work/scene-NN/candidates.json`, one entry per object you see in any view:

   ```json
   [
     {"view": "full", "bbox": [410, 220, 600, 700], "kind": "character", "label": "הילד", "spec_ref": "3.2"},
     {"view": "r3c1", "bbox": [55, 300, 140, 380], "kind": "find_item", "label": "תפוח"}
   ]
   ```

   `kind` is one of `character`, `animal`, `object`, `furniture`, `find_item`, `text`, `background`, `other`. Use the same label for the same thing across views so the merge works. Aim for every character, every animal, every held or touched object, furniture, every «מצאו» item, and any lettering. Usually 10 to 20 per scene, more in busy scenes.
3. `scene-audit map --scene NN` merges the views and removes duplicates. It reports what the spec expects and the list lacks.
4. Open `work/scene-NN/objects-marked.png`. If anything visible has no box, add it to `candidates.json` and map again.

### 5. Inspect every object (per scene)

`scene-audit crops --scene NN` writes `work/scene-NN/crop-tasks.json`. For every object:

1. Open its `alone` crops (enlarged, at least 768 px on the short side; large objects also have `-p1`, `-p2` parts at full resolution). Check anatomy, completeness, material, color.
2. Open its `context` crop. Check contact with the ground and the hands, scale, gaze direction, shadow.
3. Write into `work/scene-NN.json`, on that object:
   - `checks`: every object code `ID ST FB AN OB AC GZ`, each `pass`, `fail`, `verify` or `na`. A `fail` needs a finding.
   - `action` for every character: `who` · `does` · `with` · `toward`, in Hebrew. Then test it with three questions: is it physically possible (grip, balance, nothing passing through a body)? Does it fit the character per the spec (age, role, signature item)? Is it what the scene should show?

Then open every view in `gaps` (areas no object crop covered) and run `scene-audit seen --scene NN gap-r1c4 ...` for the ones you reviewed. Coverage counts only objects with all seven checks filled and gaps marked seen.

### 6. Scene-level checks (per scene)

Fill `scene_checks` with the scene codes `DU SF SY AU TG WD SP` (`na` where the book has no such feature). Write `summary`, one Hebrew line about the scene.

Count «מצאו» items by marking, never by estimate. Every instance gets a box, edges and background included:

```json
"counts": [
  {"label": "תפוחים", "expected": 5, "spec_ref": "6.1", "result": "wrong",
   "instances": [{"view": "07-12", "view_bbox": [30, 40, 120, 130]}],
   "note": "השישי מוסתר מאחורי הכד"}
]
```

`result` is `correct`, `wrong`, `ambiguous` (unclear what counts), or `unconfirmed`. The number reported is the number of boxes.

### Taxonomy

Object level: ID character identity (locked marks, color family, proportions) · ST style · FB forbidden elements, including any lettering in the image · AN anatomy (hands, fingers, face, eyes, limbs) · OB object integrity (broken, floating, duplicated, merged) · AC action and logic · GZ gaze and connection.

Scene level: DU the same character twice · SF safety (what a parent would not want a small child to imitate) · SY unintended symbols, reported as seen for the owner · AU audience, cultural and religious details, reported as a question · TG «מצאו» counts · WD every listed word has a visible item, every item-strip item appears in the scene in the same color · SP continuity across a spread, when the spec defines it.

### Findings

Each finding goes in `findings` of `work/scene-NN.json`:

```json
{
  "finding_id": "07-F02",
  "object_id": "07-03",
  "code": "AN",
  "type": "spec_violation",
  "spec_ref": "5.1",
  "severity": "critical",
  "confidence": "likely",
  "view": "07-03",
  "view_bbox": [610, 420, 760, 560],
  "where": "יד ימין של הילד",
  "problem": "שש אצבעות",
  "fix_kind": "local_edit",
  "fix_instruction": "לצייר מחדש את יד ימין עם חמש אצבעות, באותה אחיזה בקנקן"
}
```

- `type`: `spec_violation` cites a section that exists. `spec_conflict` means the spec contradicts itself; it is the owner's decision and the render is not at fault. `suggestion` is taste and never counts as a defect. AU and SY items are `suggestion` phrased as a question.
- `severity`: `critical` must not reach print. `medium` a child or parent will notice. `minor` only a close look finds.
- `confidence`: `likely` or `verify` now. The second pass decides `certain`.
- `fix_kind`: a scene with many defects plus a style problem is cheaper to `rerender` with a detailed instruction than to fix with a series of edits.
- `where`, `problem`, `fix_instruction` in Hebrew. A count in a tag agrees in gender with the noun it counts (חמישה תפוחים, חמש בננות).

`scene-audit validate --scene NN` until it reports zero errors.

### 7. Independent second pass

1. `scene-audit verify-pack --scene NN` writes `work/scene-NN/verify/tasks.json`: one crop per finding and a neutral question per code, without your reasoning.
2. Start a subagent with only this brief: open `tasks.json`, follow its `instructions`, look at each `image` and `context_image`, and write `answers.json` in the format given. Tell it not to open `work/scene-NN.json`. If you have no subagent tool, do the pass yourself from `tasks.json` and the images only, and say in the final message that the second pass was not independent.
3. `scene-audit verify-apply --scene NN`. Confirmed findings may now be raised to `certain` if you are sure. Rejected or uncertain ones are already moved to «לוודא».
4. `scene-audit validate --scene NN`, then `scene-audit done --scene NN`.

### 8. Report and decisions

`scene-audit report` builds, from the scene JSON files only:

- `out/report.html` in Hebrew, right to left: critical items · «מצאו» tags in four groups · other findings · spec conflicts · decisions waiting · a closing line on the resolution checked and what remains unverified.
- `out/scenes.md`: what every character does.
- `out/defects.csv`: one row per defect with a padded box on the source file, for the creation tool.
- `out/marked/scene-NN.png`: numbered boxes for checking by eye.
- `out/prompt-block.md`: lines to add to future prompts so the defects do not come back.
- `out/decisions.csv`: the owner's queue.

Tell the owner the critical items, the tag results and how many decisions wait, with the path to `report.html`. Ask for decisions in the conversation and record each answer with `scene-audit decide --set 07-F02=ok|local|rerender`, or have the owner fill `out/decisions.csv` and run `scene-audit decide --apply`. A dismissed finding is remembered by file hash and position and does not come back on the same file.

### 9. Recheck after a re-render

When a scene file changes, `scene-audit scan --scene NN` archives the old JSON in `work/history/` and starts the scene fresh. Run steps 4 to 7 for that scene only, then `scene-audit recheck --scene NN`: what closed, what remains, what is new. Then `scene-audit report`.

## Before the first full book

Run a pilot on three scenes whose defects the owner already knows. Report two numbers: how many known defects were found, and how many findings turned out wrong. Tune from that before scanning the whole book. A scene with 20 objects takes about 30 to 50 image views.

## Final message

Name the commands that ran, the scenes that are done, coverage per scene, the number of «לוודא» items, and anything not checked. Niqqud produced by any model needs human proofreading before print; say so. Never report a scene as checked that did not reach `done`.
