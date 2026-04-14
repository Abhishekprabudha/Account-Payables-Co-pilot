from pathlib import Path
from services.contract_parser import extract_contract_text, extract_key_clauses


def test_contract_parser_reads_docx():
    path = Path(__file__).resolve().parents[2] / "sample_data" / "3PL_Aggregator_Carrier_Master_Transportation_Agreement.docx"
    text = extract_contract_text(str(path))
    assert "Agreement" in text
    assert extract_key_clauses(text)
