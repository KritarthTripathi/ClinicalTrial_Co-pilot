from app.common.pii import PIIMasker, compliance_report


def test_masks_planted_pii():
    m = PIIMasker()
    out = m.mask("Patient John Smith, MRN-1234567, john.smith@site.example, call 212-555-0147, SUBJ-4821")
    for secret in ["John Smith", "1234567", "john.smith@site.example", "212-555-0147", "SUBJ-4821"]:
        assert secret not in out


def test_same_value_same_placeholder():
    m = PIIMasker()
    assert m.mask("MRN-1234567") == m.mask("MRN-1234567")


def test_compliance_passes_clean_masked_text():
    m = PIIMasker()
    masked = m.mask("Contact john.smith@site.example about MRN-1234567")
    assert compliance_report(masked, m.counts)["verdict"] == "pass"
