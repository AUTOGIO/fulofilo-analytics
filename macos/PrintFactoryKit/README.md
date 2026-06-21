# PrintFactoryKit

Local-first native macOS app for textile and accessories print production.

Takes an artwork image and generates a complete factory-ready package: print files at 300 DPI, tech pack, color palette with CMYK values, production notes, approval checklist, and a ZIP ready to send to the factory.

**No cloud. No login. No database. Apple Silicon only.**

---

## What it generates

| Output | Description |
|--------|-------------|
| `artwork_PRINT_READY_300dpi.png` | Artwork scaled to exact print dimensions at 300 DPI |
| `artwork_PRINT_READY_300dpi.pdf` | PDF at exact print dimensions — open directly in CorelDRAW |
| `artwork_PRINT_READY.svg` | SVG with embedded raster — CorelDRAW 2019+, Inkscape |
| `seamless_repeat_2x2_300dpi.png` | 2×2 seamless repeat tile at 300 DPI |
| `seamless_repeat_3x3_300dpi.png` | 3×3 seamless repeat tile at 300 DPI |
| `03_COLOR_PALETTE.pdf` | Color swatches with HEX + RGB + CMYK values |
| `04_PRODUCT_TECH_PACK.pdf` | Full technical spec sheet |
| `06_FACTORY_APPROVAL_CHECKLIST.pdf` | Factory fills and signs before production |
| `08_SUPPLIER_MESSAGE.txt` | Ready-to-send email in PT + EN |
| `FACTORY_PACKAGE.zip` | Everything above in one file — send this to factory |

---

## Supported products

- Necessaire
- Cosmetic Pouch
- Tote Bag
- Beach Bag
- Canga

## Supported materials

- Canvas 12oz
- Cetim + Lona (bleed applied automatically)
- Poliéster com Elastano (8% stretch compensation applied automatically)
- Polyester
- Cotton

---

## Requirements

- macOS 26 or later
- Apple Silicon (M1, M2, M3, M4)
- Xcode 26 (to build from source)
- `xcodegen` (`brew install xcodegen`)
- Apple Intelligence enabled — required for Auto-fill from Image only

---

## Build from source

```bash
git clone https://github.com/AUTOGIO/fulofilo-analytics.git
cd fulofilo-analytics/macos/PrintFactoryKit

xcodegen generate

xcodebuild \
  -scheme PrintFactoryKit \
  -configuration Release \
  -derivedDataPath build \
  CODE_SIGN_IDENTITY="-" \
  CODE_SIGNING_REQUIRED=NO \
  CODE_SIGNING_ALLOWED=NO \
  build

cp -R build/Build/Products/Release/PrintFactoryKit.app dist/
open dist/PrintFactoryKit.app
```

---

## Project structure

```
PrintFactoryKit/
├── PrintFactoryKit/
│   ├── App/                  — Entry point, ContentView
│   ├── Models/               — FactoryProject, ProductionSpecs, ArtworkAnalysis
│   ├── Services/             — PDF, palette, print export, ZIP, approval
│   ├── Features/
│   │   ├── ImportArtwork/    — Drag-drop UI, project details, production specs
│   │   ├── ImageAnalysis/    — Palette preview, Apple Intelligence auto-fill
│   │   ├── ProjectGenerator/ — Package generator, production defaults, view model
│   │   └── Exporter/         — Result view, warnings, next steps
│   ├── AppIntents/           — Shortcuts integration (placeholder)
│   └── Resources/            — Info.plist, entitlements
├── Tests/
├── project.yml               — xcodegen spec
├── dist/                     — Built Release app (gitignored)
└── USER_GUIDE.md
```

---

## Part of

[FulôFiló Analytics](https://github.com/AUTOGIO/fulofilo-analytics) — `macos/PrintFactoryKit`
