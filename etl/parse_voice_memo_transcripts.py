"""
Parse voice-memo transcript text files into a Canga inventory table
(Tipo, Estampa, Quantidade) using fuzzy matching against canga_catalog_400_438.csv.

Usage:
    python etl/export_canga_voice_memo_catalog.py   # refresh catalog from Excel
    python etl/parse_voice_memo_transcripts.py path/to/transcript.txt
    python etl/parse_voice_memo_transcripts.py path/to/transcript.txt --format xlsx -o out.xlsx

Depends on: stdlib + openpyxl.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "data" / "raw" / "voice_memo_transcripts" / "canga_catalog_400_438.csv"
EXPORT_SCRIPT = ROOT / "etl" / "export_canga_voice_memo_catalog.py"

# After accent strip, for word matching
_PT_NUMBER_WORDS: dict[str, int] = {
    "zero": 0,
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
    "onze": 11,
    "doze": 12,
    "treze": 13,
    "catorze": 14,
    "quatorze": 14,
    "quinze": 15,
    "dezesseis": 16,
    "dezessete": 17,
    "dezoito": 18,
    "dezenove": 19,
    "vinte": 20,
    "trinta": 30,
    "quarenta": 40,
    "cinquenta": 50,
    "sessenta": 60,
    "setenta": 70,
    "oitenta": 80,
    "noventa": 90,
    "cem": 100,
}


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def _norm(s: str) -> str:
    s = _strip_accents(s.lower())
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


_TIPO_TOKENS_ELASTANO = frozenset({"elastano", "elastico", "elast"})
_TIPO_TOKENS_ALGODAO = frozenset({"algodao", "alg"})


def _norm_tokens(s: str) -> list[str]:
    return [t for t in _norm(s).split() if t]


@dataclass
class CatalogRow:
    sku: int
    tipo: str
    estampa_canonica: str
    aliases: list[str]


def load_catalog(path: Path) -> list[CatalogRow]:
    rows: list[CatalogRow] = []
    with path.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            aliases = [a.strip() for a in row["aliases"].split("|") if a.strip()]
            rows.append(
                CatalogRow(
                    sku=int(row["sku"]),
                    tipo=row["tipo"],
                    estampa_canonica=row["estampa_canonica"],
                    aliases=aliases,
                )
            )
    return rows


def _extract_quantity(tokens: list[str]) -> tuple[int | None, set[str]]:
    """Return (quantity or None, set of token strings consumed as quantity)."""
    consumed: set[str] = set()
    found: list[int] = []
    i = 0
    n = len(tokens)
    while i < n:
        a, b = tokens[i], tokens[i + 1] if i + 1 < n else ""
        # "uma dúzia" / "um duzia" → 12 (plan: Portuguese inventory phrasing)
        if b == "duzia" and a in ("um", "uma"):
            found.append(12)
            consumed.add(a)
            consumed.add(b)
            i += 2
            continue
        if a == "duas" and b == "duzias":
            found.append(24)
            consumed.add(a)
            consumed.add(b)
            i += 2
            continue
        t = tokens[i]
        if t.isdigit():
            found.append(int(t))
            consumed.add(t)
            i += 1
            continue
        if t == "duzia":
            found.append(12)
            consumed.add(t)
            i += 1
            continue
        if t in _PT_NUMBER_WORDS:
            found.append(_PT_NUMBER_WORDS[t])
            consumed.add(t)
        i += 1

    if not found:
        return None, consumed
    # Prefer last explicit number (often at end of phrase)
    return found[-1], consumed


def _detect_tipo(tokens: list[str]) -> tuple[str | None, set[str]]:
    consumed: set[str] = set()
    has_el = any(t in _TIPO_TOKENS_ELASTANO for t in tokens)
    has_alg = any(t in _TIPO_TOKENS_ALGODAO for t in tokens)
    for t in tokens:
        if t in _TIPO_TOKENS_ELASTANO:
            consumed.add(t)
        if t in _TIPO_TOKENS_ALGODAO:
            consumed.add(t)
    if has_el and not has_alg:
        return "ELASTANO", consumed
    if has_alg and not has_el:
        return "ALGODAO", consumed
    if has_el and has_alg:
        return None, consumed
    return None, consumed


def _noise_tokens() -> set[str]:
    return {
        "canga",
        "cangas",
        "unidade",
        "unidades",
        "qtd",
        "qtde",
        "quantidade",
        "pcs",
        "pecas",
    }


def _estampa_candidate(tokens: list[str], consumed: set[str]) -> str:
    noise = _noise_tokens()
    parts: list[str] = []
    for t in tokens:
        if t in consumed or t in noise:
            continue
        parts.append(t)
    return " ".join(parts)


def _match_score(candidate: str, alias: str) -> float:
    if not candidate or not alias:
        return 0.0
    ca, al = _norm(candidate), _norm(alias)
    if not ca or not al:
        return 0.0
    if ca == al:
        return 1.0
    if ca in al or al in ca:
        return max(0.88, SequenceMatcher(None, ca, al).ratio())
    return SequenceMatcher(None, ca, al).ratio()


def _tipo_from_memo_header(line: str) -> str | None:
    """Infer default material from `--- memo_begin <iso> <Title...> ---` (plan: memo title hint)."""
    rest = line.removeprefix("--- memo_begin").strip()
    if rest.endswith("---"):
        rest = rest[:-3].strip()
    parts = rest.split(None, 1)
    title = parts[1] if len(parts) >= 2 else (parts[0] if parts else "")
    if not title:
        return None
    tokens = _norm_tokens(title)
    tipo, _ = _detect_tipo(tokens)
    return tipo


def best_catalog_match(
    catalog: list[CatalogRow],
    candidate: str,
    tipo_filter: str | None,
) -> tuple[CatalogRow | None, float]:
    best: CatalogRow | None = None
    best_score = 0.0
    for row in catalog:
        if tipo_filter and row.tipo != tipo_filter:
            continue
        for alias in row.aliases:
            sc = _match_score(candidate, alias)
            if sc > best_score:
                best_score = sc
                best = row
    return best, best_score


def parse_lines(catalog: list[CatalogRow], text: str) -> list[dict]:
    results: list[dict] = []
    memo_default_tipo: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("--- memo_begin"):
            memo_default_tipo = _tipo_from_memo_header(line)
            continue
        if line.startswith("--- memo_end"):
            memo_default_tipo = None
            continue

        tokens = _norm_tokens(line)
        if not tokens:
            continue

        tipo_hint, tipo_cons = _detect_tipo(tokens)
        if tipo_hint is None and memo_default_tipo is not None:
            tipo_hint = memo_default_tipo
        qty, qty_cons = _extract_quantity(tokens)
        consumed = set(tipo_cons) | set(qty_cons)
        candidate = _estampa_candidate(tokens, consumed)

        row_match, score = best_catalog_match(catalog, candidate, tipo_hint)
        inferred_tipo = tipo_hint

        if row_match is None and tipo_hint is None and candidate:
            row_match, score = best_catalog_match(catalog, candidate, None)
            if row_match is not None:
                inferred_tipo = row_match.tipo

        if row_match is None and tipo_hint is not None and candidate:
            row_match, score = best_catalog_match(catalog, candidate, None)
            if row_match is not None and row_match.tipo != tipo_hint:
                score *= 0.85

        estampa_out = row_match.estampa_canonica if row_match else ""
        sku_out = row_match.sku if row_match else ""
        tipo_out = inferred_tipo or (row_match.tipo if row_match else "")

        if row_match and inferred_tipo and row_match.tipo != inferred_tipo:
            score = min(score, 0.7)

        needs_review = (
            row_match is None
            or score < 0.85
            or qty is None
            or (tipo_hint is not None and row_match is not None and row_match.tipo != tipo_hint)
        )

        results.append(
            {
                "tipo_canga": tipo_out,
                "estampa": estampa_out,
                "quantidade": qty if qty is not None else "",
                "sku": sku_out,
                "confidence": round(score, 4) if row_match else 0.0,
                "needs_review": needs_review,
                "raw_line": raw,
            }
        )
    return results


PARSED_XLSX_COLUMNS = [
    "Tipo de Canga",
    "Estampa",
    "Quantidade",
    "sku",
    "confidence",
    "needs_review",
    "raw_line",
    "source_file",
]


def _bool_cell(val: object) -> bool:
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in ("true", "1", "yes", "sim")


def write_parsed_csv(all_rows: list[dict], path: Path) -> None:
    fields = [
        "tipo_canga",
        "estampa",
        "quantidade",
        "sku",
        "confidence",
        "needs_review",
        "source_file",
        "raw_line",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(all_rows)


def write_parsed_xlsx(all_rows: list[dict], path: Path) -> None:
    wb = openpyxl.Workbook()
    ws_p = wb.active
    assert ws_p is not None
    ws_p.title = "Parsed"
    ws_p.append(PARSED_XLSX_COLUMNS)
    for r in all_rows:
        ws_p.append(
            [
                r.get("tipo_canga"),
                r.get("estampa"),
                r.get("quantidade"),
                r.get("sku"),
                r.get("confidence"),
                _bool_cell(r.get("needs_review")),
                r.get("raw_line"),
                r.get("source_file"),
            ]
        )
    ws_s = wb.create_sheet("Summary")
    ws_s.append(["metric", "value"])
    n = len(all_rows)
    n_rev = sum(1 for r in all_rows if _bool_cell(r.get("needs_review")))
    ws_s.append(["parsed_row_count", n])
    ws_s.append(["needs_review_true_count", n_rev])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def main() -> None:
    ap = argparse.ArgumentParser(description="Parse voice memo transcripts into Canga rows.")
    ap.add_argument("transcripts", nargs="+", type=Path, help="One or more .txt transcript files")
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path (default: first input stem + _parsed.csv or _parsed.xlsx)",
    )
    ap.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG,
        help="Catalog CSV from export_canga_voice_memo_catalog.py",
    )
    ap.add_argument(
        "--refresh-catalog",
        action="store_true",
        help="Run export_canga_voice_memo_catalog.py before parsing",
    )
    ap.add_argument(
        "--format",
        choices=("csv", "xlsx"),
        default="csv",
        help="Output format (default csv). xlsx adds Parsed + Summary sheets.",
    )
    args = ap.parse_args()

    if args.refresh_catalog:
        subprocess.run([sys.executable, str(EXPORT_SCRIPT)], check=True)

    if not args.catalog.exists():
        print(f"Catalog missing: {args.catalog}\nRun: python etl/export_canga_voice_memo_catalog.py", file=sys.stderr)
        sys.exit(1)

    catalog = load_catalog(args.catalog)
    all_rows: list[dict] = []
    for path in args.transcripts:
        text = path.read_text(encoding="utf-8")
        for row in parse_lines(catalog, text):
            row["source_file"] = str(path.name)
            all_rows.append(row)

    out = args.output
    if out is None:
        first = args.transcripts[0]
        suffix = "_parsed.xlsx" if args.format == "xlsx" else "_parsed.csv"
        out = first.with_name(first.stem + suffix)
    else:
        p = Path(out)
        if args.format == "xlsx" and p.suffix.lower() not in (".xlsx", ".xlsm"):
            out = p.with_suffix(".xlsx")
        elif args.format == "csv" and p.suffix.lower() != ".csv":
            out = p.with_suffix(".csv")

    if args.format == "xlsx":
        write_parsed_xlsx(all_rows, Path(out))
    else:
        write_parsed_csv(all_rows, Path(out))

    print(f"Wrote {len(all_rows)} rows to {out}")


if __name__ == "__main__":
    main()
