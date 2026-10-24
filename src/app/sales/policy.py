"""Column-level privacy policy. HCP identifiers are pseudonymized (model sees codes, real values
live in the encrypted vault); numbers and codes pass through; free text is scanned with Presidio."""
POLICY = {
    "dim_hcp": {"npi": "pseudonymize", "full_name": "pseudonymize"},
    "fact_activity": {"notes_text": "scan_presidio"},
}


def apply_policy(frames: dict, masker) -> dict:
    out = {}
    for table, df in frames.items():
        df = df.copy()
        for col, action in POLICY.get(table, {}).items():
            if action == "pseudonymize":
                ent = col.upper()
                df[col] = df[col].map(lambda v, e=ent: masker._placeholder(e, str(v)))
            elif action == "scan_presidio":
                cache = {}

                def mask_once(v, cache=cache):
                    if v not in cache:
                        cache[v] = masker.mask(v)
                    return cache[v]
                df[col] = df[col].fillna("").map(mask_once)
        out[table] = df
    return out
