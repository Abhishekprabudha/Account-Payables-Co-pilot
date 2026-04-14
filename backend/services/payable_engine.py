from __future__ import annotations
from collections import Counter
from typing import Dict, List
import pandas as pd
from .schemas import AnalysisResponse, ShipmentDecision


ALLOWED_STATUSES = {"Delivered", "RTO Delivered", "Partially Delivered"}


def analyze_payable(contract_meta: dict, erp: dict, invoice: dict, clauses) -> AnalysisResponse:
    erp_df = erp["shipment"].copy()
    invoice_df = invoice["lines"].copy()

    if "shipment_id" not in erp_df.columns:
        raise ValueError("ERP data missing shipment_id column.")

    erp_df["shipment_id"] = erp_df["shipment_id"].astype(str).str.strip()
    invoice_df["shipment_id"] = invoice_df["shipment_id"].astype(str).str.strip()

    duplicate_counts = invoice_df["shipment_id"].value_counts()
    duplicate_ids = set(duplicate_counts[duplicate_counts > 1].index)

    merge_cols = [
        c for c in [
            "shipment_id", "carrier_code", "carrier_name", "current_status", "pod_available_flag",
            "damage_flag", "shortage_flag", "rto_flag", "actual_pickup_datetime", "actual_delivery_datetime",
            "gps_tracking_flag", "otp_verified_flag", "e_pod_flag", "exception_code"
        ] if c in erp_df.columns
    ]

    merged = invoice_df.merge(erp_df[merge_cols], on="shipment_id", how="left", indicator=True)

    decisions: List[ShipmentDecision] = []
    held_reason_counter: Counter = Counter()
    recommended = 0.0
    held = 0
    eligible = 0
    missing = 0

    for _, row in merged.iterrows():
        reasons: List[str] = []
        decision = "Pay"
        erp_status = None if pd.isna(row.get("current_status")) else str(row.get("current_status"))
        shipment_id = str(row["shipment_id"])
        amount = float(row.get("invoice_amount", 0.0) or 0.0)

        if row["_merge"] == "left_only":
            decision = "Hold"
            reasons.append("Shipment missing in ERP raw extract")
            missing += 1

        if shipment_id in duplicate_ids:
            decision = "Hold"
            reasons.append("Duplicate invoice rows for same shipment")

        if erp_status and erp_status not in ALLOWED_STATUSES:
            decision = "Hold"
            reasons.append(f"ERP status not yet payable: {erp_status}")

        if str(row.get("pod_available_flag", "")).upper() == "N":
            decision = "Hold"
            reasons.append("POD not available in ERP")

        if str(row.get("damage_flag", "")).upper() == "Y":
            decision = "Hold"
            reasons.append("Damage flag present in ERP")

        if str(row.get("shortage_flag", "")).upper() == "Y":
            decision = "Hold"
            reasons.append("Shortage flag present in ERP")

        if pd.notna(row.get("carrier_name")) and invoice.get("meta", {}).get("carrier_name"):
            carrier_invoice = str(invoice["meta"]["carrier_name"]).lower().strip()
            carrier_erp = str(row.get("carrier_name")).lower().strip()
            if carrier_invoice and carrier_erp and carrier_invoice[:10] not in carrier_erp and carrier_erp[:10] not in carrier_invoice:
                decision = "Review"
                reasons.append("Carrier name differs between invoice face and ERP")

        if decision == "Pay":
            recommended += amount
            eligible += 1
            reasons = ["Line is payable based on invoice shipment match, ERP status, and operational evidence checks"]
        else:
            held += 1
            for r in reasons:
                held_reason_counter[r] += 1

        decisions.append(ShipmentDecision(
            shipment_id=shipment_id,
            invoice_amount=round(amount, 2),
            decision=decision,
            reasons=reasons,
            erp_status=erp_status,
            pod_flag=None if pd.isna(row.get("pod_available_flag")) else str(row.get("pod_available_flag")),
            damage_flag=None if pd.isna(row.get("damage_flag")) else str(row.get("damage_flag")),
            shortage_flag=None if pd.isna(row.get("shortage_flag")) else str(row.get("shortage_flag")),
        ))

    claimed = float(invoice_df["invoice_amount"].sum())
    withheld_amount = claimed - recommended
    confidence = "High" if missing == 0 and len(duplicate_ids) == 0 else "Medium"

    rationale_summary = [
        f"Recommended payable equals the sum of invoice shipment lines that matched ERP shipment IDs and cleared basic operational payability checks.",
        f"Held lines are excluded where the ERP extract showed missing shipment records, non-payable status, missing POD, damage, shortage, or duplicate billing rows.",
        f"Contract clauses were extracted as contextual guidance for AP review, especially for POD, withholding, loss/damage, audit, penalties, and discount mechanisms.",
    ]

    diagnostics = {
        "contract_meta": contract_meta,
        "invoice_rows": int(len(invoice_df)),
        "erp_rows": int(len(erp_df)),
        "allowed_statuses": sorted(ALLOWED_STATUSES),
    }

    return AnalysisResponse(
        recommended_payable=round(recommended, 2),
        claimed_invoice_amount=round(claimed, 2),
        withheld_amount=round(withheld_amount, 2),
        eligible_shipments=eligible,
        held_shipments=held,
        missing_in_erp=missing,
        duplicate_invoice_rows=sum(v - 1 for v in duplicate_counts[duplicate_counts > 1]),
        confidence=confidence,
        rationale_summary=rationale_summary,
        contract_clauses=clauses,
        held_reasons_breakdown=dict(held_reason_counter),
        decisions=decisions[:500],
        carrier_name=invoice.get("meta", {}).get("carrier_name") or (erp_df["carrier_name"].dropna().astype(str).iloc[0] if "carrier_name" in erp_df.columns and not erp_df["carrier_name"].dropna().empty else None),
        invoice_number=invoice.get("meta", {}).get("invoice_number"),
        period=invoice.get("meta", {}).get("period"),
        diagnostics=diagnostics,
    )
