# Voice memo transcripts → Canga table

Drop daily transcript files here, then run the parser (see [QA workflow](#qa-workflow) below).

## Daily export format

Use **plain UTF-8 text** (`.txt`). Recommended layout:

- One spoken inventory line per paragraph or per line.
- Optional header block per memo (Shortcuts can prepend this):

```
--- memo_begin 2026-04-30T14:22:00 MemoTitle ---
<transcript line 1>
<transcript line 2>
--- memo_end ---
```

If the **memo title** contains `elastano` or `algodão` / `algodao`, lines **until** `--- memo_end ---` use that as the default **Tipo** when a line omits the material word.

If you do not use separators, the parser treats **each non-empty line** as one utterance.

Example lines (Portuguese):

- `elastano olho grego 3`
- `Canga algodão cordel cinco`
- `fitas praia 2 elastano`
- `cordel uma duzia` (12 units)

## Shortcuts on Mac (recommended)

Per Apple’s [Shortcuts User Guide](https://support.apple.com/guide/shortcuts-mac/intro-to-shortcuts-apdf22b0444c/mac), build a shortcut in the Shortcuts app:

1. **Get Voice Memos** (or **Get Latest Voice Memo**, if available) — filter by date if needed.
2. **Repeat with each** memo (if batching).
3. **Transcribe Audio** — set language to **Portuguese (Brazil)** when the action offers it.
4. **Text** — combine: memo name, current date, newline, transcript.
5. **Append to File** — append to a file under this folder, e.g. `data/raw/voice_memo_transcripts/inbox/2026-04-30.txt` (create `inbox` if missing).

Exact action names can vary by macOS build; search the action library for *Voice Memo*, *Transcribe*, *Append*.

**Privacy:** Processing stays on-device when using Apple’s transcription actions.

## End-to-end command sequence (from repo root)

Run in order after you have transcript `.txt` file(s) in `inbox/` (or elsewhere).

1. **Export catalog snapshot** from `data/excel/FuloFilo_Master.xlsx` (do this whenever Catalog SKUs or names change):

   ```bash
   python etl/export_canga_voice_memo_catalog.py
   ```

2. **Parse transcripts** to CSV (default) or XLSX with Parsed + Summary sheets:

   ```bash
   python etl/parse_voice_memo_transcripts.py data/raw/voice_memo_transcripts/inbox/2026-04-30.txt
   ```

   ```bash
   python etl/parse_voice_memo_transcripts.py data/raw/voice_memo_transcripts/inbox/2026-04-30.txt --format xlsx -o data/raw/voice_memo_transcripts/inbox/2026-04-30_parsed.xlsx
   ```

3. **Review** the output: fix or drop rows with low `confidence` or `needs_review` == true (or `"TRUE"` in Excel) before merging.

4. **Merge into Inventory** (dry-run first — prints planned stock changes, does not modify the workbook):

   ```bash
   python etl/merge_voice_memo_parsed_to_inventory.py --parsed-xlsx data/raw/voice_memo_transcripts/inbox/2026-04-30_parsed.xlsx --dry-run
   ```

   To merge only rows that are already cleared (`needs_review` is false — see parser/Excel boolean rules; excludes `TRUE`, `1`, `yes`, `sim`, and Python/Excel `True`):

   ```bash
   python etl/merge_voice_memo_parsed_to_inventory.py --parsed-xlsx data/raw/voice_memo_transcripts/inbox/2026-04-30_parsed.xlsx --dry-run --skip-needs-review
   ```

   Or with CSV:

   ```bash
   python etl/merge_voice_memo_parsed_to_inventory.py --parsed-csv data/raw/voice_memo_transcripts/inbox/2026-04-30_parsed.csv --dry-run
   ```

   ```bash
   python etl/merge_voice_memo_parsed_to_inventory.py --parsed-csv data/raw/voice_memo_transcripts/inbox/2026-04-30_parsed.csv --dry-run --skip-needs-review
   ```

5. **Merge for real** (creates `data/excel/backups/FuloFilo_Master_YYYYMMDD_HHMMSS_before_voice_memo_inventory_merge.xlsx`, then updates **Inventory** only — adds parsed quantities to `current_stock` per SKU 400–438, or appends a row from Catalog if missing):

   ```bash
   python etl/merge_voice_memo_parsed_to_inventory.py --parsed-xlsx data/raw/voice_memo_transcripts/inbox/2026-04-30_parsed.xlsx
   ```

SKUs outside 400–438 or non-numeric quantities in the parsed file are ignored for the merge.

## QA workflow

The steps above are the full workflow. Short checklist:

1. Export catalog → parse → optional `--format xlsx` → review low confidence → merge `--dry-run` (optionally `--skip-needs-review`) → merge without `--dry-run` (with the same flags as you validated).
2. Confirm the backup file exists under `data/excel/backups/` before relying on the updated master.

## Optional: Create ML

If fuzzy matching is often wrong, train an `MLTextClassifier` ([Apple documentation](https://developer.apple.com/documentation/createml/mltextclassifier)) in Xcode with **two columns** `text` and `label` (use `sku` as label). Start from [`createml_training_template.csv`](createml_training_template.csv): replace examples with real transcripts, add rows, then drag the CSV into a Create ML “Text Classification” document. Run predictions from a small Swift CLI or integrate via Core ML; the Python parser does **not** load `.mlmodel` by default.

The default pipeline uses **stdlib fuzzy matching** (`difflib`); no Core ML model is required.
