# PrintFactoryKit — User Guide

---

## Overview

PrintFactoryKit takes your artwork image and produces a complete factory production package in one click. Every file the factory needs — print-ready artwork at 300 DPI, tech pack, color palette with CMYK, approval checklist — is generated locally on your Mac and zipped for delivery.

---

## Step-by-step workflow

### Step 1 — Import Artwork

Drag and drop your artwork image onto the drop zone, or click **Browse** to select a file.

Supported formats: JPEG, PNG, TIFF, HEIC

The image is analysed immediately: dominant colors are extracted and a palette preview appears on the right.

---

### Step 2 — Auto-fill from Image (optional)

Click **✦ Auto-fill from Image** to use Apple Intelligence to suggest:

- Project name
- Collection name
- Motifs and color mood
- Notes

Only empty fields are filled — existing values are never overwritten.

> Requires Apple Intelligence enabled in System Settings. If unavailable, fill the fields manually.

---

### Step 3 — Project Details

Fill in or confirm:

| Field | Required | Notes |
|-------|----------|-------|
| Project Name | Yes | e.g. Floral Escape |
| Collection Name | No | e.g. Verão 2026 |
| Factory Name | No | Leave blank if unknown |
| Product Type | Yes | Necessaire, Tote Bag, Canga, etc. |
| Material | Yes | Cetim + Lona, Poliéster com Elastano, etc. |
| Print Method | Yes | Digital Textile, Sublimação, etc. |
| Notes | No | Motifs, references, special instructions |

---

### Step 4 — Production Specs

Specs are filled automatically when you select a product type and material (industry-standard defaults).

Review and adjust if needed:

| Section | Fields |
|---------|--------|
| Product Dimensions | Width × Height × Depth (cm) |
| Print Area | Width × Height (cm) + DPI |
| Seam Allowance | e.g. 1 cm overlock |
| Lining | Color + Material |
| Zipper | Color, Type, Length |
| Strap / Handle | Material, Width, Length |
| Target Quantity | Units for this order |

Click **✦ Apply Defaults** to reset to industry standards for the selected product and material.

---

### Step 5 — Generate Package

Click **Generate Factory Package**.

The app will:

1. Create a project folder under `~/Documents/FULO_FILO_FACTORY_PROJECTS/`
2. Generate all print-ready files at 300 DPI
3. Apply material-specific processing:
   - **Cetim + Lona** → 4 mm bleed on all edges
   - **Poliéster com Elastano** → 8% vertical stretch compensation
4. Generate all PDFs (brief, palette, tech pack, checklist, readiness report)
5. Create a ZIP with everything ready to send

---

### Step 6 — Send to Factory

In the result panel:

- Click **Reveal ZIP in Finder** to locate the file
- Send the ZIP directly to your factory contact
- Use `08_SUPPLIER_MESSAGE.txt` inside the ZIP as your email body (available in PT and EN)

---

## What the factory receives inside the ZIP

```
FF_PRINT_YYYY_NNN_PROJECTNAME_FACTORY_PACKAGE.zip
├── 01_READ_ME_FIRST.pdf
├── 02_DESIGN_BRIEF.pdf
├── 03_COLOR_PALETTE.pdf          ← HEX + RGB + CMYK per color
├── 04_PRODUCT_TECH_PACK.pdf      ← dimensions, hardware, lining, seam
├── 05_PRODUCTION_NOTES.pdf       ← material-specific requirements
├── 06_FACTORY_APPROVAL_CHECKLIST.pdf  ← factory fills and signs this
├── 07_AI_FACTORY_READINESS_REPORT.pdf
├── 08_SUPPLIER_MESSAGE.txt       ← copy-paste email PT + EN
├── 09_ORIGINAL_ARTWORK_IMAGE/    ← source file
└── 10_VECTOR_AND_REPEAT/
    ├── artwork_PRINT_READY_300dpi.png
    ├── artwork_PRINT_READY_300dpi.pdf  ← open in CorelDRAW
    ├── artwork_PRINT_READY.svg
    ├── seamless_repeat_2x2_300dpi.png
    ├── seamless_repeat_3x3_300dpi.png
    └── README_PRINT_FILES.txt
```

---

## Before mass production — mandatory steps

These are NOT handled by the app. They require human confirmation:

1. **Physical pre-production sample** — factory produces one piece, you approve it
2. **Pantone / CMYK color confirmation** — confirm exact color codes with a color specialist
3. **Factory signs the approval checklist** — `06_FACTORY_APPROVAL_CHECKLIST.pdf`

The package is approved for **factory review only**, not for mass production.

---

## Refresh / Start over

Click the **↺ Refresh** button in the top bar to clear all fields and start a new project.

---

## Project folder structure

Every project is saved permanently at:

```
~/Documents/FULO_FILO_FACTORY_PROJECTS/
└── FF_PRINT_YYYY_NNN_PROJECTNAME/
    ├── 00_BRIEF/                  — Markdown source documents
    ├── 03_MASTER_ARTWORK/         — Original artwork copy
    ├── 04_PATTERN_SYSTEM/
    │   ├── seamless_repeat/
    │   └── sparse_repeat/
    ├── 08_FACTORY_PACKAGE/        — All deliverables
    └── 09_EXPORT/                 — Factory ZIP
```

Projects are never overwritten. Each generation creates a new numbered folder.

---

## Warnings explained

| Warning | Meaning | Action |
|---------|---------|--------|
| No vector file | Only raster files generated | Have artwork vectorized for screen print |
| No Pantone/CMYK references | Notes contain no color codes | Add Pantone/CMYK refs to notes before sending |
| Image resolution low | Source image under 1500 px | Use a higher resolution source image |

---

## Sharing the app

To share PrintFactoryKit with a third party:

```bash
xattr -cr /path/to/PrintFactoryKit.app
ditto -c -k --keepParent /path/to/PrintFactoryKit.app ~/Desktop/PrintFactoryKit.zip
```

Recipient must: **right-click → Open** on first launch to bypass Gatekeeper.

Requirements on recipient Mac: macOS 26+, Apple Silicon.

---

## Support

Part of [FulôFiló Analytics](https://github.com/AUTOGIO/fulofilo-analytics) — `macos/PrintFactoryKit`
