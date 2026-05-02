#!/usr/bin/env python3
import os, csv, json, re, unicodedata
from difflib import SequenceMatcher

INPUT_DIR = "/Volumes/MICRO/VoiceMemo_output"
OUTPUT_CSV = "/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/VoiceMemo_csv/daily_sales.csv"
CATALOG_JSON = "/Users/giovannini_nuovo/Documents/GitHub/FuloFilo/data/catalog/canga_catalog.json"

NUMBER_WORDS = {
    "um":1,"uma":1,"dois":2,"duas":2,"tres":3,"três":3,"quatro":4,
    "cinco":5,"seis":6,"sete":7,"oito":8,"nove":9,"dez":10
}

STOPWORDS = {
    "canga","elastano","lycra","algodao","algodão","de","da","do","com",
    "quantidade","qtd","unidade","unidades","peca","peça","pecas","peças"
} | set(NUMBER_WORDS.keys())

def normalize(text):
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")
    return re.sub(r"[^a-z0-9\s]", " ", text)

def clean_estampa_candidate(text):
    t = normalize(text)
    t = re.sub(r"\d+", " ", t)
    words = [w for w in t.split() if w not in STOPWORDS]
    return " ".join(words).strip()

def load_catalog():
    with open(CATALOG_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_tipo(text):
    t = normalize(text)
    if "elastano" in t or "lycra" in t:
        return "ELASTANO"
    if "algodao" in t:
        return "ALGODAO"
    return "UNKNOWN"

def extract_quantity(text):
    t = normalize(text)
    m = re.search(r"\d+", t)
    if m:
        return int(m.group())
    for word, value in NUMBER_WORDS.items():
        if normalize(word) in t.split():
            return value
    return 1

def score(a, b):
    return SequenceMatcher(None, a, b).ratio()

def extract_estampa(text, catalog):
    candidate = clean_estampa_candidate(text)
    best_name = "UNKNOWN"
    best_score = 0

    for item in catalog:
        names = [item.get("estampa_canonical", "")]
        names += item.get("aliases", [])

        for name in names:
            s = score(candidate, normalize(name))
            if s > best_score:
                best_score = s
                best_name = item.get("estampa_canonical", "UNKNOWN")

    if best_score >= 0.45:
        return best_name

    return "UNKNOWN"

def process_file(filepath, catalog):
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            rows.append([
                extract_tipo(raw),
                extract_estampa(raw, catalog),
                extract_quantity(raw)
            ])
    return rows

def write_csv(rows):
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["tipo_canga", "estampa", "quantidade"])
        writer.writerows(rows)

def main():
    catalog = load_catalog()
    all_rows = []

    for filename in os.listdir(INPUT_DIR):
        if filename.endswith(".txt"):
            filepath = os.path.join(INPUT_DIR, filename)
            print(f"Processing: {filename}")
            all_rows.extend(process_file(filepath, catalog))

    write_csv(all_rows)
    print(f"CSV written: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
