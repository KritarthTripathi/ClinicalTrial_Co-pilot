"""Generates fully synthetic protocol + sales data with PLANTED PII and a ground-truth
file, so masking recall can be measured. Nothing here is real."""
import csv
import json
import random
from pathlib import Path

random.seed(7)
out = Path("data/synthetic")
out.mkdir(parents=True, exist_ok=True)

FIRST = ["Alice", "Bruno", "Chen", "Divya", "Elena", "Farid", "Grace", "Hiro"]
LAST = ["Morales", "Okafor", "Lindqvist", "Sharma", "Petrov", "Nakamura", "Duarte", "Haddad"]
CITIES = ["Springfield", "Riverton", "Lakeside", "Fairview"]
planted: list[str] = []
names: list[str] = []


def person():
    n = f"{random.choice(FIRST)} {random.choice(LAST)}"
    planted.append(n)
    names.append(n)
    return n


inv, coord = person(), person()
mrn, subj = f"MRN-{random.randint(1000000, 9999999)}", f"SUBJ-{random.randint(1000, 9999)}"
email, phone = f"{coord.split()[0].lower()}.{coord.split()[1].lower()}@trial-site.example", "212-555-0147"
planted += [mrn, subj, email, phone]

protocol = f"""PROTOCOL XT-204: A Phase II Study of Compound ABC-123 in Moderate Plaque Psoriasis

Principal Investigator: Dr. {inv}, Riverton Medical Center
Site Coordinator: {coord}, {email}, {phone}

1. Study Objectives
Primary: evaluate efficacy of ABC-123 versus placebo at Week 16.
Secondary: assess safety and tolerability through Week 52.

2. Study Design
Randomized, double-blind, placebo-controlled, parallel-group study in 120 adults.
Sample record for training: patient {subj}, {mrn}, DOB: 04/12/1981.

3. Inclusion Criteria
Age 18 to 65 years at screening.
Diagnosis of plaque psoriasis for at least 6 months.
PASI score of 12 or greater and BSA involvement of 10 percent or greater.

4. Exclusion Criteria
Prior exposure to any biologic IL-17 inhibitor.
Active tuberculosis or untreated latent tuberculosis.
Pregnancy or breastfeeding.

5. Endpoints
Primary endpoint: proportion of subjects achieving PASI 75 at Week 16.
Secondary endpoint: proportion achieving sPGA score of 0 or 1 at Week 16.

6. Schedule of Assessments
Screening visit, Baseline (Day 1), Week 4, Week 8, Week 16, Week 52.

7. Dosing
ABC-123 150 mg subcutaneous injection at Day 1, Week 1, Week 2, then every 4 weeks.
"""
planted.append("04/12/1981")
(out / "protocol_001.txt").write_text(protocol)

regions, products = ["North", "South", "East", "West"], ["Alpha", "Beta", "Gamma", "Delta"]
with open(out / "sales_001.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["order_id", "customer_name", "customer_email", "phone", "city", "region", "product", "units", "revenue"])
    for i in range(1, 61):
        n = person() if i <= 20 else random.choice(names[2:22])
        em = f"{n.split()[0].lower()}{i}@client.example"
        ph = f"646-555-{random.randint(1000, 9999)}"
        planted += [em, ph]
        u = random.randint(1, 40)
        w.writerow([i, n, em, ph, random.choice(CITIES), random.choice(regions),
                    random.choice(products), u, round(u * random.uniform(20, 90), 2)])

(out / "planted_pii.json").write_text(json.dumps(sorted(set(planted)), indent=2))
print(f"wrote synthetic data + {len(set(planted))} planted PII strings")
