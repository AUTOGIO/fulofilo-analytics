"""Tests for procurement / lead-time math."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.procurement.purchase_order import _po_id


def test_po_id_format():
    pid = _po_id("sup1", "Fornecedor Teste")
    assert pid.startswith("PO-")
    assert "Fornecedor_Teste" in pid or "sup1" in pid


def test_moq_rounding_logic():
    qty = 7
    pack = 6
    rounded = int(math.ceil(qty / pack) * pack)
    assert rounded == 12
