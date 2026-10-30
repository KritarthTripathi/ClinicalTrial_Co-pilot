"""Column-level privacy policy for schema v2. HCP names and territory manager names/emails are replaced by stable codes
(same value -> same code in every table); the real values live only in the encrypted vault."""
POLICY = {
    "hcp_summary_with_territory_and_tm_info": {"hcp_full_name": "pseudonymize", "territory_manager_name": "pseudonymize",
                                               "territory_manager_email": "pseudonymize"},
    "hcp_rx_summary_report": {"hcp_full_name": "pseudonymize"},
    "hcp_activity_calls_vae_suggestions": {"hcp_full_name": "pseudonymize"},
    "territory_alignment_hierarchy": {"territory_manager_name": "pseudonymize", "territory_manager_email": "pseudonymize"},
}   # address_line is a (synthetic) business address and stays readable so address questions work; rx_report_summary_geo has no personal data


def apply_policy(frames: dict, masker) -> dict:
    out = {}
    for table, df in frames.items():
        df = df.copy()
        for col, action in POLICY.get(table, {}).items():
            if action == "pseudonymize":
                ent = col.upper()
                df[col] = df[col].map(lambda v, e=ent: masker._placeholder(e, str(v)))
        out[table] = df
    return out
