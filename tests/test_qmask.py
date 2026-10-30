from app.common.qmask import mask_question

MAP = {"<HCP_FULL_NAME_1>": "Alice Morales", "<TERRITORY_MANAGER_NAME_1>": "Bruno Okafor",
       "<TERRITORY_MANAGER_EMAIL_1>": "bruno.okafor@firm.comp.com", "<OTHER_1>": "Not Masked"}


def test_names_and_emails_become_codes():
    q = mask_question("Which hcps are managed by bruno okafor (bruno.okafor@firm.comp.com)?", MAP)
    assert "<TERRITORY_MANAGER_NAME_1>" in q and "<TERRITORY_MANAGER_EMAIL_1>" in q and "okafor" not in q.lower()


def test_hcp_name_and_unrelated_text():
    assert mask_question("Top prescribers like Alice Morales in menji", MAP) == "Top prescribers like <HCP_FULL_NAME_1> in menji"
    assert mask_question("Not Masked stays", MAP) == "Not Masked stays"
