#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.utils.supplier_desk import rebuild_supplier_dashboard


def main() -> int:
    output = rebuild_supplier_dashboard()
    print(f"OK — rebuilt {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
