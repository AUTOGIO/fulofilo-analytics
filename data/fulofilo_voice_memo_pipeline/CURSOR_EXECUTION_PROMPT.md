# Cursor Execution Prompt — FuloFilo Voice Memo → Canga CSV Pipeline

You are operating inside this local repo:

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo
```

Act as a stability-first senior macOS/Python automation engineer. Execute only the agreed Phase 1 scope. Do not expand into Swift ASR, launchd, dashboard integration, or direct Excel write-back unless explicitly requested later.

---

## Objective

Implement a deterministic end-of-day batch pipeline that converts manually prepared Voice Memo transcript lines into a structured CSV table:

```csv
tipo_canga,estampa,quantidade
```

The pipeline must use a pre-exported canga catalog generated from:

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/excel/FuloFilo_Master.xlsx
```

---

## Agreed Decisions

- Operational mode: end-of-day batch processing.
- Input: several short Voice Memos, represented in Phase 1 as one daily `.txt` file with multiple lines.
- One input line = one output CSV row.
- Voice/transcript input folder:

```text
/Volumes/MICRO/VoiceMemo_output
```

- Output CSV folder:

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/VoiceMemo_csv
```

- Output CSV file:

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/VoiceMemo_csv/daily_sales.csv
```

- Catalog outputs:

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/catalog/canga_catalog.csv
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/catalog/canga_catalog.json
```

- Trigger: manual CLI command.
- After successful processing, rename input `.txt` file to `_processed.txt`.

---

## Tasks to Execute

### 1. Create Required Directories

Create if missing:

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/catalog
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/VoiceMemo_csv
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/tools
```

Do not delete existing files.

---

### 2. Create Catalog Export Script

Create:

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/tools/export_canga_catalog.py
```

Requirements:

- Read workbook:

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/excel/FuloFilo_Master.xlsx
```

- Use `openpyxl`.
- Filter products/SKUs in range 400–438.
- Generate both:

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/catalog/canga_catalog.csv
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/catalog/canga_catalog.json
```

- CSV schema:

```csv
sku,tipo,estampa_canonical,aliases
```

- JSON schema:

```json
[
  {
    "sku": "401",
    "tipo": "ELASTANO",
    "estampa_canonical": "Olho Grego",
    "aliases": ["olho grego", "grego"]
  }
]
```

- Detect `tipo` using:
  - `elastano`, `lycra`, `canga_el` → `ELASTANO`
  - `algodao`, `algodão`, `canga_alg` → `ALGODAO`
- Extract estampa from explicit estampa column when available.
- Otherwise extract from product name after `—`, `-`, or after known prefixes like `Canga Elastano` / `Canga Algodão`.
- Print clear success output.
- Fail safely if workbook is missing.
- Warn if any item has `UNKNOWN` tipo.

---

### 3. Create Voice Memo Parser Script

Create:

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/tools/process_voice_memos.py
```

Requirements:

- Read unprocessed `.txt` files from:

```text
/Volumes/MICRO/VoiceMemo_output
```

- Ignore files ending in `_processed.txt`.
- Load catalog JSON:

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/catalog/canga_catalog.json
```

- For each non-empty line:
  - detect `tipo_canga`
  - parse `quantidade`
  - match `estampa` against `estampa_canonical` and aliases
  - append row to output CSV

- Output CSV:

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/VoiceMemo_csv/daily_sales.csv
```

- CSV header:

```csv
tipo_canga,estampa,quantidade
```

- Quantity parsing:
  - digits
  - Portuguese words: `um`, `uma`, `dois`, `duas`, `tres`, `três`, `quatro`, `cinco`, `seis`, `sete`, `oito`, `nove`, `dez`
  - default to `1` if missing

- Tipo parsing:
  - `elastano`, `lycra` → `ELASTANO`
  - `algodao`, `algodão` → `ALGODAO`
  - otherwise `UNKNOWN`

- Estampa matching:
  - normalize accents and lowercase
  - remove obvious tipo words and quantity words before matching
  - compare against canonical names and aliases
  - use Python standard library first (`difflib`) to avoid dependency creep
  - return canonical `estampa_canonical`
  - if no acceptable match, return `UNKNOWN`

- After successful file processing, rename:

```text
filename.txt → filename_processed.txt
```

- Do not rename the input file if processing fails.
- Print summary: files processed, rows written, unknown rows.

---

### 4. Add Lightweight Documentation

Create:

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/docs/voice_memo_pipeline.md
```

Document:

- Objective
- Agreed decisions
- Folder paths
- Input format
- Output schema
- Catalog generation command
- Daily processing command
- Known limitations
- Future phases not implemented now

---

### 5. Add Test Sample

Create a safe sample input file only if `/Volumes/MICRO/VoiceMemo_output` exists:

```text
/Volumes/MICRO/VoiceMemo_output/sample_voice_memo_test.txt
```

Content:

```text
elastano olho grego três
algodao brasil tropical dois
elastano fitas praia 5
```

Do not overwrite an existing file with the same name.

---

### 6. Run Validation

Run from repo root:

```bash
cd /Users/giovannini_nuovo/Documents/GitHub/FuloFilo
python3 tools/export_canga_catalog.py
python3 tools/process_voice_memos.py
```

If dependency `openpyxl` is missing, install only after confirming the project has a virtual environment. Prefer:

```bash
python3 -m pip install openpyxl
```

If there is an existing `requirements.txt` or `pyproject.toml`, add `openpyxl` there instead of ad hoc installation.

---

## Success Criteria

The work is complete only when:

1. Catalog CSV and JSON are generated.
2. `process_voice_memos.py` reads unprocessed `.txt` files.
3. `daily_sales.csv` is created/appended with exactly:

```csv
tipo_canga,estampa,quantidade
```

4. Processed input files are renamed with `_processed.txt`.
5. The script does not crash on malformed or empty lines.
6. The documentation file exists.
7. The terminal output clearly reports what happened.

---

## Constraints

Do not implement:

- Swift SpeechTranscriber.
- Real-time cashier mode.
- Folder watcher automation.
- `launchd` schedule.
- Direct write-back to `FuloFilo_Master.xlsx`.
- Dashboard integration.
- DuckDB/Parquet integration.
- Create ML training.

These are future phases.

---

## Expected Final Report

After execution, report:

- Files created/modified.
- Commands run.
- Whether catalog export succeeded.
- Number of catalog rows exported.
- Number of transcript rows processed.
- Any `UNKNOWN` tipo or estampa rows.
- Any assumptions made because workbook column names were not obvious.
