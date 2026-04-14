from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ClauseSnippet(BaseModel):
    title: str
    snippet: str


class ShipmentDecision(BaseModel):
    shipment_id: str
    invoice_amount: float
    decision: str
    reasons: List[str]
    erp_status: Optional[str] = None
    pod_flag: Optional[str] = None
    damage_flag: Optional[str] = None
    shortage_flag: Optional[str] = None


class AnalysisResponse(BaseModel):
    recommended_payable: float
    claimed_invoice_amount: float
    withheld_amount: float
    eligible_shipments: int
    held_shipments: int
    missing_in_erp: int
    duplicate_invoice_rows: int
    confidence: str
    rationale_summary: List[str]
    contract_clauses: List[ClauseSnippet]
    held_reasons_breakdown: Dict[str, int]
    decisions: List[ShipmentDecision]
    carrier_name: Optional[str] = None
    invoice_number: Optional[str] = None
    period: Optional[str] = None
    diagnostics: Dict[str, Any]
