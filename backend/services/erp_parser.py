from __future__ import annotations
from pathlib import Path
from typing import Dict
import pandas as pd


REQUIRED_COLS = [
    "shipment_id", "carrier_code", "carrier_name", "current_status", "pod_available_flag",
    "damage_flag", "shortage_flag", "rto_flag", "actual_pickup_datetime", "actual_delivery_datetime",
]


def load_erp(path: str) -> Dict[str, pd.DataFrame]:
    suffix = Path(path).suffix.lower()
    if suffix != ".xlsx":
        raise ValueError("ERP report must be an .xlsx file for this MVP.")
    xls = pd.ExcelFile(path)
    if "Shipment_Raw" not in xls.sheet_names:
        raise ValueError("Expected a 'Shipment_Raw' sheet in ERP file.")
    shipment = pd.read_excel(path, sheet_name="Shipment_Raw")
    for col in REQUIRED_COLS:
        if col not in shipment.columns:
            shipment[col] = None
    shipment.columns = [str(c).strip() for c in shipment.columns]
    shipment["shipment_id"] = shipment["shipment_id"].astype(str).str.strip()
    return {
        "shipment": shipment,
        "event_log": pd.read_excel(path, sheet_name="Milestone_Event_Log") if "Milestone_Event_Log" in xls.sheet_names else pd.DataFrame(),
        "reference": pd.read_excel(path, sheet_name="Reference_Master") if "Reference_Master" in xls.sheet_names else pd.DataFrame(),
    }
