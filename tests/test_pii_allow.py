from app.common.pii import PIIMasker


def test_brand_not_masked():
    assert "Aurelis" in PIIMasker().mask("Discussed efficacy data and dosing for Aurelis. HCP receptive.")


def test_patient_still_masked():
    assert "Maria Garcia" not in PIIMasker().mask("HCP mentioned patient Maria Garcia switched therapy last month.")
