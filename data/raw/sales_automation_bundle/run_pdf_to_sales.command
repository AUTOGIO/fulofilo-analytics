#!/bin/bash
set -euo pipefail

PY_SCRIPT="$HOME/Downloads/pdf_to_sales_pipeline.py"
INPUT_DIR="$HOME/Documents/TShirtSales/PDFs"
OUTPUT_DIR="$HOME/Documents/TShirtSales/Output"

python3 "$PY_SCRIPT" --input-dir "$INPUT_DIR" --output-dir "$OUTPUT_DIR" --recursive
