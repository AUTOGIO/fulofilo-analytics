#!/bin/bash
# ============================================================
# FulôFiló — Legacy refresh path (archived)
# ============================================================
# This script is intentionally disabled.
# It previously orchestrated Eleve/CSV ETL steps that are no
# longer part of the canonical Excel-first operating model.
# ============================================================

set -euo pipefail

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"

cat <<EOF
[refresh_data] Legacy path archived.

This repository now operates on the canonical Excel-first workflow only:

  source of truth: $PROJECT/data/excel/FuloFilo_Master.xlsx
  canonical sync:  bash $PROJECT/scripts/sync_excel.sh
  dashboard run:   bash $PROJECT/scripts/launch_app.sh

Do not use refresh_data.sh for normal operations.
Historical raw CSV/JSON files remain in the repository as archived evidence only.
EOF

exit 1
