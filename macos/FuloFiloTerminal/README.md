# FulôFiló Retail Operations Terminal (macOS SwiftUI)

This folder contains a complete native macOS SwiftUI implementation of a Bloomberg-terminal-style retail operations dashboard (mock data only).

## How to Run

This is a SwiftPM package. Open it directly in Xcode:

1. Open `macos/FuloFiloTerminal/Package.swift` in Xcode.
2. Select the `FuloFiloTerminal` scheme.
3. Build & Run (⌘R).

Recommended window size for the intended density: ~**1600 × 900**.

## Notes

- No external dependencies.
- No web views.
- No backend required.
- All data is mock/local sample data.
  - Optional read-model bridge uses the repo’s existing `.venv` Python + DuckDB to load snapshots from `data/parquet/*`.
  - If the bridge fails, the UI falls back to mock data.
