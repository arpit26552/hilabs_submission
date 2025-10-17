import pandas as pd
import logging
from collections import defaultdict
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ProviderDataVerifier:
    def __init__(self, roster_file, ca_ground_truth_file, ny_ground_truth_file):
        self.roster_file = roster_file
        self.ca_ground_truth_file = ca_ground_truth_file
        self.ny_ground_truth_file = ny_ground_truth_file

        # Containers
        self.roster_data = None
        self.ca_ground_truth = None
        self.ny_ground_truth = None
        self.ca_index = {}
        self.ny_index = {}

        # Results
        self.mismatches = defaultdict(list)
        self.matches = defaultdict(list)
        self.expired_licenses = []
        self.not_expired_licenses = []
        self.board_certification_results = []

        # Mappings
        self.field_mappings = {
            "first_name": "first_name",
            "last_name": "last_name",
            "primary_specialty": "specialty",
            "practice_address_line1": "address_line1",
            "practice_city": "address_city",
            "practice_state": "address_state",
            "practice_zip": "address_zip",
            "practice_phone": "phone",
            "license_expiration": "expiration_date",
            "medical_school": "medical_school",
            "residency_program": "residency_program",
            "credential": "credential",
            "mailing_address_line1": "mailing_address_line1",
            "mailing_city": "mailing_city",
            "mailing_state": "mailing_state",
            "mailing_zip": "mailing_zip",
            "accepting_new_patients": "accepting_new_patients",
            "years_in_practice": "years_in_practice",
            "taxonomy_code": "taxonomy_code",
        }

    # -------------------------------------------------------------------
    # Load Data
    # -------------------------------------------------------------------
    def load_data(self):
        logger.info("Loading data...")
        self.roster_data = pd.read_csv(self.roster_file)
        self.ca_ground_truth = pd.read_csv(self.ca_ground_truth_file)
        self.ny_ground_truth = pd.read_csv(self.ny_ground_truth_file)
        self._create_indexes()
        logger.info("Loaded roster: %d, CA: %d, NY: %d", len(self.roster_data), len(self.ca_ground_truth), len(self.ny_ground_truth))

    def _create_indexes(self):
        for _, row in self.ca_ground_truth.iterrows():
            lic = str(row["license_number"]).strip()
            if lic and lic != "nan":
                self.ca_index[lic] = row.to_dict()

        for _, row in self.ny_ground_truth.iterrows():
            lic = str(row["license_number"]).strip()
            if lic and lic != "nan":
                self.ny_index[lic] = row.to_dict()

    def _normalize_value(self, v):
        if pd.isna(v) or v is None:
            return ""
        return " ".join(str(v).strip().split()).lower()

    # -------------------------------------------------------------------
    # Checks
    # -------------------------------------------------------------------
    def _check_license_expiration(self, expiration_date, pid, full_name, lic, state):
        current_date = datetime.now().date()
        if not expiration_date:
            return
        exp_date = None
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]:
            try:
                exp_date = datetime.strptime(str(expiration_date), fmt).date()
                break
            except ValueError:
                continue
        if not exp_date:
            return
        info = {
            "provider_id": pid,
            "full_name": full_name,
            "license_number": lic,
            "state": state,
            "expiration_date": expiration_date,
            "current_date": current_date.strftime("%Y-%m-%d"),
            "days_difference": (exp_date - current_date).days,
        }
        if exp_date < current_date:
            self.expired_licenses.append(info)
        else:
            self.not_expired_licenses.append(info)

    def _check_board_certification(self, roster_record, gt_record, pid, full_name, state):
        roster_board = str(roster_record.get("board_certified", "")).lower()
        roster_spec = self._normalize_value(roster_record.get("primary_specialty", ""))
        result = {
            "provider_id": pid,
            "full_name": full_name,
            "license_number": roster_record.get("license_number", ""),
            "state": state,
            "roster_board_certified": roster_board,
            "roster_specialty": roster_spec,
            "match_status": "UNKNOWN",
            "ground_truth_value": "",
            "certification_correct": False,
        }
        if state == "CA":
            gt_cert = self._normalize_value(gt_record.get("board_certification", ""))
            result["ground_truth_value"] = gt_cert
            if roster_board in ["true", "1", "yes"]:
                if roster_spec and gt_cert:
                    if roster_spec == gt_cert:
                        result["match_status"] = "CERTIFIED_MATCH"
                        result["certification_correct"] = True
                    else:
                        result["match_status"] = "CERTIFIED_SPECIALTY_MISMATCH"
                else:
                    result["match_status"] = "CERTIFIED_NO_GT_DATA"
            else:
                result["match_status"] = "NOT_CERTIFIED_MATCH" if not gt_cert else "NOT_CERTIFIED_BUT_GT_HAS_CERT"
        elif state == "NY":
            gt_cert = str(gt_record.get("board_certified", "")).lower()
            result["ground_truth_value"] = gt_cert
            if roster_board == gt_cert:
                result["match_status"] = "DIRECT_MATCH"
                result["certification_correct"] = True
            else:
                result["match_status"] = "DIRECT_MISMATCH"
        self.board_certification_results.append(result)

    def _compare_fields(self, roster_record, gt_record, pid, full_name):
        for rf, gf in self.field_mappings.items():
            if rf in roster_record and gf in gt_record:
                rv = self._normalize_value(roster_record[rf])
                gv = self._normalize_value(gt_record[gf])
                info = {
                    "provider_id": pid,
                    "full_name": full_name,
                    "license_number": roster_record.get("license_number", ""),
                    "state": roster_record.get("practice_state", ""),
                    "roster_value": roster_record.get(rf, ""),
                    "ground_truth_value": gt_record.get(gf, ""),
                    "field_name": rf,
                }
                if rv == gv and (rv or gv):
                    self.matches[f"{rf}_match"].append(info)
                elif rv != gv and (rv or gv):
                    self.mismatches[f"{rf}_mismatch"].append(info)

    # -------------------------------------------------------------------
    # Verification
    # -------------------------------------------------------------------
    def verify_data(self):
        for idx, r in self.roster_data.iterrows():
            pid = r.get("provider_id", f"UNKNOWN_{idx}")
            full_name = r.get("full_name", "Unknown")
            lic = str(r.get("license_number", "")).strip()
            state = str(r.get("practice_state", "")).strip().upper()
            if not lic or lic == "nan":
                continue
            gt = self.ca_index.get(lic) if state == "CA" else self.ny_index.get(lic) if state == "NY" else None
            if gt:
                self._compare_fields(r.to_dict(), gt, pid, full_name)
                self._check_license_expiration(gt.get("expiration_date"), pid, full_name, lic, state)
                self._check_board_certification(r.to_dict(), gt, pid, full_name, state)
            else:
                self.mismatches["license_not_found"].append(
                    {"provider_id": pid, "full_name": full_name, "license_number": lic, "state": state}
                )

    # -------------------------------------------------------------------
    # Reports (returns DataFrames instead of only saving)
    # -------------------------------------------------------------------
    def generate_reports(self):
        mismatches_df = pd.DataFrame([m for cat in self.mismatches.values() for m in cat]) if self.mismatches else pd.DataFrame()
        matches_df = pd.DataFrame([m for cat in self.matches.values() for m in cat]) if self.matches else pd.DataFrame()
        expired_df = pd.DataFrame(self.expired_licenses) if self.expired_licenses else pd.DataFrame()
        active_df = pd.DataFrame(self.not_expired_licenses) if self.not_expired_licenses else pd.DataFrame()
        board_df = pd.DataFrame(self.board_certification_results) if self.board_certification_results else pd.DataFrame()

        return {
            "mismatches": mismatches_df,
            "matches": matches_df,
            "expired": expired_df,
            "active": active_df,
            "board": board_df,
        }


# Debug usage
if __name__ == "__main__":
    roster_file = "provider_roster_with_errors.csv"
    ca_file = "ca_medical_license_database.csv"
    ny_file = "ny_medical_license_database.csv"

    v = ProviderDataVerifier(roster_file, ca_file, ny_file)
    v.load_data()
    v.verify_data()
    dfs = v.generate_reports()

    for k, df in dfs.items():
        print(f"{k}: {len(df)} rows")
