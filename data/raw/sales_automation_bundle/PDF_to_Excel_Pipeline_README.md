# PDF to Excel sales pipeline

## Purpose
Convert a folder of daily sales PDFs into:
- `sales_entries.csv`
- `sales_entries.xlsx`
- `parse_log.txt`

The parser is built around annotation text like:

`venda 05 unidades de ' CAMISETA BASICA ' da estampa ' Cabedelo_Peito ', tamanho ' M '`

## Dependencies
```bash
python3 -m pip install pymupdf openpyxl
```

## macOS example
```bash
python3 "/Users/YOUR_USER/Downloads/pdf_to_sales_pipeline.py"   --input-dir "/Users/YOUR_USER/Documents/TShirtSales/PDFs"   --output-dir "/Users/YOUR_USER/Documents/TShirtSales/Output"   --recursive
```

## Optional fixed date
Use this only if your PDF filenames do not contain a date and you do not want to rely on file modified time:
```bash
python3 "/Users/YOUR_USER/Downloads/pdf_to_sales_pipeline.py"   --input-dir "/Users/YOUR_USER/Documents/TShirtSales/PDFs"   --output-dir "/Users/YOUR_USER/Documents/TShirtSales/Output"   --default-date 2025-01-01
```

## Date resolution order
1. Date found in filename, such as `2025-01-01_regionais.pdf`
2. File modified date
3. `--default-date` if explicitly provided

## Output fields
- `sale_date`
- `source_file`
- `source_path`
- `page`
- `category`
- `product_label`
- `print_name`
- `size`
- `units`
- `notes`

## Notes
- Categories are normalized to: `BÁSICAS`, `REGATAS`, `INFANTIS`, `BABY`
- The script currently targets PDFs that contain sale annotations in text form
- If future PDFs are scanned images only, add OCR before parsing
