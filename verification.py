import pandas as pd, numpy as np, re
from datetime import datetime

# File paths
ROSTER = "provider_roster_with_errors.csv"
NY = "ny_medical_license_database.csv"
CA = "ca_medical_license_database.csv"
NPI = "mock_npi_registry.csv"
OUT_VALID = "roster_with_validations.csv"
# OUT_MIS = "roster_mismatches.csv"

# Load datasets
df_roster = pd.read_csv(ROSTER, dtype=str, low_memory=False).fillna("")
df_ny = pd.read_csv(NY, dtype=str, low_memory=False).fillna("")
df_ca = pd.read_csv(CA, dtype=str, low_memory=False).fillna("")
df_npi = pd.read_csv(NPI, dtype=str, low_memory=False).fillna("")

# Helpers
def normalize_text(v):
    if v is None: return ""
    s = str(v).strip()
    s = re.sub(r"\s+", " ", s).lower()
    return s

def parse_date(v):
    try:
        dt = pd.to_datetime(v, errors='coerce')
        if pd.isna(dt):
            return None
        return dt.normalize()
    except:
        return None

def date_to_str(dt):
    if dt is None or (isinstance(dt, float) and np.isnan(dt)): return ""
    return pd.to_datetime(dt).strftime("%Y-%m-%d")

def make_lookup(df, key_col, prefer_date_col=None):
    if key_col not in df.columns:
        return {}
    sub = df[df[key_col]!=""].copy()
    if prefer_date_col and prefer_date_col in sub.columns:
        sub["_dt"] = pd.to_datetime(sub[prefer_date_col], errors='coerce')
        sub = sub.sort_values("_dt").drop_duplicates(subset=[key_col], keep="last").drop(columns=["_dt"])
    else:
        sub = sub.drop_duplicates(subset=[key_col], keep="last")
    return {str(r[key_col]): r.to_dict() for _, r in sub.iterrows()}

ny_lookup = make_lookup(df_ny, "license_number", prefer_date_col="expiration_date" if "expiration_date" in df_ny.columns else None)
ca_lookup = make_lookup(df_ca, "license_number", prefer_date_col="expiration_date" if "expiration_date" in df_ca.columns else None)
npi_lookup = make_lookup(df_npi, "npi", prefer_date_col="npi_certification_date" if "npi_certification_date" in df_npi.columns else None)

def get_external_records(roster_row):
    npi_rec = npi_lookup.get(roster_row.get("npi",""), {})
    state_rec = {}
    lic = roster_row.get("license_number","")
    st = (roster_row.get("license_state","") or "").upper().strip()
    if st == "NY":
        state_rec = ny_lookup.get(lic, {})
    elif st == "CA":
        state_rec = ca_lookup.get(lic, {})
    else:
        state_rec = ny_lookup.get(lic, {}) or ca_lookup.get(lic, {})
    external = {}
    external.update(npi_rec or {})
    if state_rec:
        external.update(state_rec)
    return external, npi_rec, state_rec

def find_external_value_for_col(roster_col, external):
    lower_map = {k.lower(): v for k,v in external.items()}
    rc = roster_col.lower()
    if rc in lower_map:
        return lower_map[rc]
    synonyms = {
        "last_updated": ["last_updated","lastupdated","last_date_update","last_date_updated","last_update_date","last_upd","verification_date"],
        "npi_certification_date": ["npi_certification_date","npi_cert_date","npi_certified_date","certification_date"],
        "license_expiration": ["expiration_date","license_expiration","expiry_date","expiration"],
        "license_number": ["license_number","provider_license_number","provider_license_number_1","provider_license_number_2"],
        "first_name": ["first_name","basic_first_name","provider_first_name","authorized_official_first_name"],
        "last_name": ["last_name","basic_last_name","provider_last_name","authorized_official_last_name"],
        "provider_name": ["provider_name","provider_organization_name_legal_name","provider_legal_name","provider_name_full"],
        "practice_phone": ["practice_phone","telephone_number","phone","practice_phone_number"],
        "practice_address_line1": ["practice_address_line1","address_1","practice_address","address_line_1","addressline1"],
        "practice_city": ["practice_city","city"],
        "practice_state": ["practice_state","state","license_state"],
        "practice_zip": ["practice_zip","zip","postal_code","zipcode"],
        "taxonomy_code": ["taxonomy_code","healthcare_provider_taxonomy_code_1","taxonomy"],
        "primary_specialty": ["specialty","primary_specialty"]
    }
    for key, candidates in synonyms.items():
        if roster_col.lower() == key or roster_col.lower().replace(" ","_") == key:
            for c in candidates:
                if c.lower() in lower_map:
                    return lower_map[c.lower()]
    tokens = re.split(r"[\W_]+", roster_col.lower())
    tokens = [t for t in tokens if t and len(t)>2]
    for extk, val in external.items():
        lk = extk.lower()
        if all(any(tok in lk for tok in tokens) for tok in tokens[:2]):
            return val
    return None

def compare_values(roster_val, external_val):
    if external_val is None or (isinstance(external_val, str) and external_val.strip()==""):
        return "not_found", ""
    r_dt = parse_date(roster_val)
    e_dt = parse_date(external_val)
    if r_dt is not None or e_dt is not None:
        r_str = date_to_str(r_dt) if r_dt is not None else ""
        e_str = date_to_str(e_dt) if e_dt is not None else ""
        if r_str and e_str and r_str == e_str:
            return "correct", e_str
        else:
            return "mismatch", e_str or external_val
    if normalize_text(roster_val) == normalize_text(external_val):
        return "correct", external_val
    else:
        return "mismatch", external_val

def check_board_certification(roster_row, state_rec, license_state):
    """
    Handle board certification check for NY and CA
    """
    roster_primary_specialty = normalize_text(roster_row.get("primary_specialty", ""))
    license_state = license_state.upper().strip()
    
    if license_state == "NY":
        # NY has board_certified column with true/false
        board_certified = state_rec.get("board_certified", "").strip().lower()
        if board_certified == "true":
            return "correct"
        elif board_certified == "false":
            # Write value from specialty column
            ny_specialty = state_rec.get("specialty", "").strip()
            if ny_specialty:
                return ny_specialty
            else:
                return "not_found"
        else:
            return "not_found"
    
    elif license_state == "CA":
        # CA has specialty values in board_certification column
        ca_board_certification = normalize_text(state_rec.get("board_certification", ""))
        ca_specialty = normalize_text(state_rec.get("specialty", ""))
        
        if ca_board_certification:
            # Compare roster primary_specialty with CA board_certification
            if roster_primary_specialty == ca_board_certification:
                return "correct"
            else:
                return state_rec.get("board_certification", "")
        else:
            # No value in board_certification, compare with specialty
            if ca_specialty:
                if roster_primary_specialty == ca_specialty:
                    return "correct"
                else:
                    return state_rec.get("specialty", "")
            else:
                return "not_found"
    
    else:
        return "not_found"

augmented_rows = []
mismatch_rows = []
TODAY = pd.to_datetime("2025-09-06")

for idx, r in df_roster.iterrows():
    external, npi_rec, state_rec = get_external_records(r)
    augmented = {}
    row_mismatch = r.to_dict()
    any_mismatch = False
    mismatch_reasons = []
    
    # Get license state for board certification check
    license_state = (r.get("license_state","") or "").upper().strip()
    
    for col in df_roster.columns:
        roster_val = r.get(col,"")
        augmented[col] = roster_val
        if(col=='years_in_practice'):
            augmented["years_in_practice_check"] = roster_val
            continue
        if(col=='board_certified'):
            continue
        ext_val = find_external_value_for_col(col, external)
        status, ext_display = compare_values(roster_val, ext_val)
        check_col = f"{col}_check"
        if status == "correct":
            augmented[check_col] = "correct"
        elif status == "not_found":
            augmented[check_col] = "not_found"
            if col.lower() in ["npi","license_number","first_name","last_name","license_expiration"]:
                any_mismatch = True
                mismatch_reasons.append(f"{col}_not_found")
        else:
            any_mismatch = True
            mismatch_reasons.append(f"{col}_mismatch")
            augmented[check_col] = ext_display if ext_display is not None else str(ext_val)
    
    # Add board certification check
    board_cert_result = check_board_certification(r, state_rec, license_state)
    augmented["board_certification_check"] = board_cert_result
    
    if board_cert_result not in ["correct", "not_found"]:
        any_mismatch = True
        mismatch_reasons.append("board_certification_mismatch")
    elif board_cert_result == "not_found":
        any_mismatch = True
        mismatch_reasons.append("board_certification_not_found")
    
    # Check for expired license
    state_exp_raw = None
    for k in state_rec.keys():
        if 'expir' in k.lower() or 'expiration' in k.lower() or 'expiry' in k.lower():
            state_exp_raw = state_rec.get(k); break
    if state_exp_raw is None and "expiration_date" in state_rec:
        state_exp_raw = state_rec.get("expiration_date")
    state_exp = parse_date(state_exp_raw)
    if state_exp is not None and state_exp < TODAY:
        check_col = "license_expiration_check"
        augmented[check_col] = f"EXPIRED"
        any_mismatch = True
        mismatch_reasons.append("state_license_expired")
    
    if any_mismatch:
        row_mismatch["mismatch_types"] = "|".join(sorted(set(mismatch_reasons)))
        row_mismatch["state_license_expiration_raw"] = state_exp_raw or ""
        row_mismatch["state_license_expiration_parsed"] = date_to_str(state_exp) if state_exp else ""
        mismatch_rows.append(row_mismatch)
    
    augmented_rows.append(augmented)

df_aug = pd.DataFrame(augmented_rows)
df_mis = pd.DataFrame(mismatch_rows)
df_aug.to_csv(OUT_VALID, index=False)
# df_mis.to_csv(OUT_MIS, index=False)

print("Saved augmented:", OUT_VALID)
# print("Saved mismatches:", OUT_MIS)
print("Totals: roster rows =", len(df_roster), "; mismatches =", len(df_mis))