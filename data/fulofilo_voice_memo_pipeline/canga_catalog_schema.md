# FuloFilo Canga Catalog Schema

## Purpose

This catalog is the normalization source for Voice Memo transcript parsing.
It converts spoken product references into stable catalog names used by the FuloFilo inventory pipeline.

## Source of Truth

Original workbook:

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/excel/FuloFilo_Master.xlsx
```

Generated catalog files:

```text
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/catalog/canga_catalog.csv
/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/catalog/canga_catalog.json
```

## CSV Schema

```csv
sku,tipo,estampa_canonical,aliases
401,ELASTANO,Olho Grego,"olho grego;grego;olho-grego"
403,ELASTANO,Fitas Praia,"fitas praia;fitas;praia"
```

## JSON Schema

```json
[
  {
    "sku": "401",
    "tipo": "ELASTANO",
    "estampa_canonical": "Olho Grego",
    "aliases": [
      "olho grego",
      "grego",
      "olho-grego"
    ]
  }
]
```

## Field Rules

| Field | Type | Required | Description |
|---|---:|---:|---|
| `sku` | string | yes | Product SKU from workbook. Expected range: 400–438. |
| `tipo` | string | yes | Must be `ELASTANO` or `ALGODAO`. |
| `estampa_canonical` | string | yes | Clean display name of the canga print. |
| `aliases` | list/string | no | Alternative spoken spellings for fuzzy matching. |

## Normalization Rules

- Remove accents for matching.
- Lowercase aliases.
- Remove repeated spaces.
- Preserve canonical display spelling in output.
- Do not infer products outside SKU 400–438.

## Stability Rule

The parser must read from the exported CSV/JSON catalog, not directly from the Excel workbook during daily processing.
