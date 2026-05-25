# FuloFilo Voice Memo → Canga CSV Pipeline

## 1. Objective

Build a stable end-of-day batch pipeline that converts short Voice Memo sales recordings into a structured CSV table for FuloFilo inventory tracking.

The system is not intended for real-time cashier operation in Phase 1.

---

## 2. Agreed Operational Mode

| Area | Decision |
|---|---|
| Operational moment | End-of-day batch processing |
| Input behavior | Several short Voice Memos |
| Voice convention | One memo / transcript line = one sale or item |
| Processing trigger | Manual CLI command |
| Initial transcription method | Hybrid: manual/Shortcut transcript first, Swift ASR later |
| Output format | CSV intermediate layer |
| Matching strictness | Semi-strict: write row, flag/review later in future phase |

---

## 3. Folder Decisions

### Voice Memo Export / Transcript Input Folder

```text
/Volumes/MICRO/VoiceMemo_output
```

Condition: the external disk must be mounted before processing.

### Output CSV Folder

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/VoiceMemo_csv
```

### Catalog Folder

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/catalog
```

---

## 4. Phase 1 Input Format

Use one daily `.txt` file containing multiple transcript lines.

Example:

```text
elastano olho grego três
algodao brasil tropical dois
elastano fitas praia cinco
```

Rule:

```text
One line = one output CSV row
```

After successful processing, the input file is renamed with `_processed` suffix.

Example:

```text
daily_2026-04-30.txt
```

becomes:

```text
daily_2026-04-30_processed.txt
```

---

## 5. Output CSV Schema

Minimal schema selected:

```csv
tipo_canga,estampa,quantidade
```

Example:

```csv
tipo_canga,estampa,quantidade
ELASTANO,Olho Grego,3
ALGODAO,Brasil Tropical,2
```

---

## 6. Catalog Strategy

The catalog is pre-exported from the master Excel workbook.

### Source Workbook

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/excel/FuloFilo_Master.xlsx
```

### Generated Catalog Files

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/catalog/canga_catalog.csv
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/catalog/canga_catalog.json
```

### Catalog Fields

```csv
sku,tipo,estampa_canonical,aliases
```

JSON equivalent:

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

---

## 7. Processing Logic

Pipeline:

```text
Daily TXT → Parse lines → Detect tipo → Parse quantity → Match estampa → Append CSV → Rename input file
```

### Tipo Detection

Keyword-based:

- `elastano`, `lycra` → `ELASTANO`
- `algodão`, `algodao` → `ALGODAO`

### Quantity Detection

Supports:

- digits: `1`, `2`, `3`
- Portuguese words: `um`, `uma`, `dois`, `duas`, `três`, `tres`, etc.

Default if missing:

```text
1
```

### Estampa Matching

Uses catalog aliases + canonical names.

Phase 1 may use Python fuzzy matching. Future phase may add confidence and review queue.

---

## 8. Phase 1 Deliverables

1. Catalog schema document.
2. Excel-to-catalog export script.
3. Voice Memo transcript parser script.
4. Cursor execution prompt.
5. Decision brief.

---

## 9. Future Phases — Not in Current Scope

### Phase 2

- Add confidence column.
- Add review queue.
- Add `source_file` and audit fields.
- Improve fuzzy matching with `rapidfuzz`.

### Phase 3

- Add Swift `SpeechTranscriber` for `.m4a` batch transcription.
- Remove manual transcript step.

### Phase 4

- Integrate with dashboard / DuckDB / Parquet.
- Add Shortcut or `launchd` automation.

---

## 10. Stability Principles

- Do not write directly to `FuloFilo_Master.xlsx` in Phase 1.
- Do not automate folder watching yet.
- Do not introduce Swift ASR yet.
- Use CSV as a safe intermediate layer.
- Keep catalog pre-exported and inspectable.
- Prefer manual CLI execution until the pipeline is validated.
