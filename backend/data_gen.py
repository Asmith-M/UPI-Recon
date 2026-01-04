#!/usr/bin/env python3
"""
Generate mock bank reconciliation files for an Indian bank (example: SBI).
Produces seven Excel files:
  1_CBS_Inward.xlsx
  2_CBS_Outward.xlsx
  3_Switch.xlsx
  4_NPCI_Inward.xlsx
  5_NPCI_Outward.xlsx
  6_NSTL.xlsx
  7_Adjustment_Files.xlsx

Requirements:
  pip install pandas openpyxl numpy
"""
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ----------------------------
# Configuration
# ----------------------------
OUTPUT_DIR = "bank_recon_files"   # output folder (created if missing)
NUM_MASTER_RECORDS = 300         # master transactions to generate
EXTRA_SWITCH_RECORDS = 12        # extra messages in switch
SEED = 42                        # reproducible randomness (set to None for true randomness)

# Set seeds for reproducibility
if SEED is not None:
    random.seed(SEED)
    np.random.seed(SEED)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----------------------------
# Helpers
# ----------------------------
def generate_unique_rrns(count, forbidden_set=None):
    """
    Generate `count` unique 12-digit RRNs as strings, ensuring none in `forbidden_set`.
    Leading digit will not be zero.
    """
    forbidden = set(forbidden_set) if forbidden_set else set()
    rrns = set()
    while len(rrns) < count:
        r = str(random.randint(100_000_000_000, 999_999_999_999))  # 12-digit numeric
        if r not in forbidden and r not in rrns:
            rrns.add(r)
    return list(rrns)

def random_date_within_last(days=2):
    minutes_back = random.randint(1, days * 24 * 60)
    d = datetime.now() - timedelta(minutes=minutes_back)
    return d.strftime("%Y-%m-%d %H:%M:%S")

def generate_master(num_records):
    """
    Generate a master dataframe of transactions (unique RRNs).
    """
    rrns = generate_unique_rrns(num_records)
    channels = ["UPI", "IMPS", "NEFT", "RTGS", "ATM", "POS"]
    statuses = ["SUCCESS", "FAILED", "PENDING"]
    directions = ["CR", "DR"]  # CR = credit (inward to bank), DR = debit (outward from bank)
    beneficiaries = ["Alice", "Bob", "CorpX", "VendorY", "MerchantZ", "CustomerA"]
    tran_types = ["U2", "U3"]  # UPI transaction types

    rows = []
    for i in range(num_records):
        txn_id = f"TXN{100000 + i}"
        rrn = rrns[i]
        # realistic amounts: mostly retail, some larger
        if random.random() < 0.75:
            amount = round(random.uniform(10.0, 2000.0), 2)
        else:
            amount = round(random.uniform(2000.0, 50000.0), 2)

        date = random_date_within_last(days=2)
        status = random.choices(statuses, weights=[0.85, 0.08, 0.07])[0]
        channel = random.choice(channels)
        direction = random.choices(directions, weights=[0.6, 0.4])[0]
        account_no = str(random.randint(1000000000, 9999999999))
        beneficiary = random.choice(beneficiaries)
        tran_type = random.choice(tran_types)  # U2 or U3
        rc = str(random.randint(100, 999))  # Response code

        rows.append({
            "Transaction_ID": txn_id,
            "RRN": rrn,
            "Amount": amount,
            "Tran_Date": date,
            "Dr_Cr": direction,
            "RC": rc,
            "Tran_Type": tran_type,
            "Status": status,
            "Channel": channel,
            "Account_No": account_no,
            "Beneficiary": beneficiary
        })
    return pd.DataFrame(rows)

# ----------------------------
# Generate datasets
# ----------------------------
print("Generating master dataset...")
df_master = generate_master(NUM_MASTER_RECORDS)

# Create SWITCH file: master + some extra messages (late/duplicate)
print("Creating Switch file...")
extra = generate_master(EXTRA_SWITCH_RECORDS)
# Ensure extra RRNs don't collide with master
extra_rrns = generate_unique_rrns(EXTRA_SWITCH_RECORDS, forbidden_set=set(df_master["RRN"].tolist()))
extra["RRN"] = extra_rrns
df_switch = pd.concat([df_master, extra], ignore_index=True)

# Introduce a few random status mismatches in switch (for test)
for idx in random.sample(range(len(df_switch)), k=min(6, len(df_switch))):
    df_switch.at[idx, "Status"] = random.choice(["SUCCESS", "FAILED", "PENDING"])

df_switch["Source"] = "SWITCH"
df_switch.to_excel(os.path.join(OUTPUT_DIR, "3_Switch.xlsx"), index=False)

# CBS Inward / Outward: what posted to the core banking system (subsets of master)
print("Creating CBS Inward and CBS Outward...")
master_credits = df_master[df_master["Dr_Cr"] == "CR"].copy().reset_index(drop=True)
master_debits = df_master[df_master["Dr_Cr"] == "DR"].copy().reset_index(drop=True)

# Simulate realistic posting percentages
df_cbs_inward = master_credits.sample(frac=0.92, random_state=SEED).copy()
df_cbs_inward["Source"] = "CBS"

df_cbs_outward = master_debits.sample(frac=0.90, random_state=SEED).copy()
df_cbs_outward["Source"] = "CBS"

df_cbs_inward.to_excel(os.path.join(OUTPUT_DIR, "1_CBS_Inward.xlsx"), index=False)
df_cbs_outward.to_excel(os.path.join(OUTPUT_DIR, "2_CBS_Outward.xlsx"), index=False)

# NPCI Inward / Outward: derived from Switch plus small differences
print("Creating NPCI Inward and NPCI Outward...")
switch_copy = df_switch.copy().reset_index(drop=True)

npc_in = switch_copy[switch_copy["Dr_Cr"] == "CR"].sample(frac=0.93, random_state=SEED).copy().reset_index(drop=True)
npc_out = switch_copy[switch_copy["Dr_Cr"] == "DR"].sample(frac=0.90, random_state=SEED).copy().reset_index(drop=True)

# Introduce small amount differences (fees/rounding) in some records
def apply_small_amount_variations(df, pct=0.06, delta=-0.50):
    count = max(1, int(len(df) * pct))
    idxs = np.random.choice(df.index, size=count, replace=False)
    for i in idxs:
        df.at[i, "Amount"] = round(df.at[i, "Amount"] + delta, 2)

apply_small_amount_variations(npc_in, pct=0.06, delta=-0.50)    # small fees on inbound
apply_small_amount_variations(npc_out, pct=0.05, delta=+1.00)   # small rounding on outbound

npc_in["Source"] = "NPCI"
npc_out["Source"] = "NPCI"

npc_in.to_excel(os.path.join(OUTPUT_DIR, "4_NPCI_Inward.xlsx"), index=False)
npc_out.to_excel(os.path.join(OUTPUT_DIR, "5_NPCI_Outward.xlsx"), index=False)

# NSTL settlement file: successful settled transactions with settlement charges for some
print("Creating NSTL settlement file...")
npc_combined = pd.concat([npc_in, npc_out], ignore_index=True)
settled = npc_combined[npc_combined["Status"] == "SUCCESS"].copy().reset_index(drop=True)

# Apply settlement charges to a small percent
settled["Settlement_Charge"] = 0.0
settled["Amount_Settled"] = settled["Amount"]
if len(settled) > 0:
    n_charges = max(1, int(len(settled) * 0.03))
    charge_idxs = np.random.choice(settled.index, size=n_charges, replace=False)
    for i in charge_idxs:
        # charge is small, e.g., 0.1% up to a small cap
        charge_amt = round(min(10.0, settled.at[i, "Amount"] * 0.001), 2)
        settled.at[i, "Settlement_Charge"] = charge_amt
        settled.at[i, "Amount_Settled"] = round(settled.at[i, "Amount"] - charge_amt, 2)

settled["Source"] = "NSTL"
settled.to_excel(os.path.join(OUTPUT_DIR, "6_NSTL.xlsx"), index=False)

# Adjustment file: manual corrections and force matches for exceptions
print("Creating Adjustment file...")
rrn_switch = set(df_switch["RRN"].tolist())
rrn_cbs = set(pd.concat([df_cbs_inward, df_cbs_outward], ignore_index=True)["RRN"].tolist())
missing_in_cbs = list(rrn_switch - rrn_cbs)

adjustments = []

# Create adjustments for some of the missing-in-CBS switch records
n_missing_to_fix = min(8, len(missing_in_cbs))
if n_missing_to_fix > 0:
    sample_missing = random.sample(missing_in_cbs, n_missing_to_fix)
    for rrn in sample_missing:
        rec = df_switch[df_switch["RRN"] == rrn].iloc[0].to_dict()
        adjustments.append({
            "RRN": rrn,
            "Amount": rec["Amount"],
            "Tran_Date": rec["Tran_Date"],
            "Dr_Cr": rec["Dr_Cr"],
            "RC": rec["RC"],
            "Tran_Type": rec["Tran_Type"],
            "Adjustment_Action": random.choice(["FORCE_MATCH", "MANUAL_POST", "REVERSE"]),
            "Comments": "Auto-generated adjustment to reconcile missing in CBS",
            "Performed_By": random.choice(["Ops_User1", "Ops_User2", "ManagerA"])
        })

# Add some pure manual entries (new RRNs)
manual_rrns = generate_unique_rrns(5, forbidden_set=rrn_switch.union(rrn_cbs))
for i, rrn in enumerate(manual_rrns):
    adjustments.append({
        "RRN": rrn,
        "Amount": round(random.uniform(50.0, 10000.0), 2),
        "Tran_Date": random_date_within_last(days=2),
        "Dr_Cr": random.choice(["CR", "DR"]),
        "RC": str(random.randint(100, 999)),
        "Tran_Type": random.choice(["U2", "U3"]),
        "Adjustment_Action": "MANUAL_ENTRY",
        "Comments": "Manual adjustment posted to correct prior day imbalance",
        "Performed_By": random.choice(["Ops_User1", "ManagerB"])
    })

df_adjust = pd.DataFrame(adjustments)
df_adjust.to_excel(os.path.join(OUTPUT_DIR, "7_Adjustment_Files.xlsx"), index=False)

print("\n✅ Generation complete. Files saved to:", os.path.abspath(OUTPUT_DIR))
for p in sorted(Path(OUTPUT_DIR).glob("*.xlsx")):
    print(" -", p.name)
