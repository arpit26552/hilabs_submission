# backend/dedupe_providers.py
# Local-only provider deduplication: blocking, similarity, scoring, clustering
import os, re
from collections import defaultdict, Counter
import pandas as pd
from difflib import SequenceMatcher
from itertools import combinations

OUT_PATH = './dedup_results.csv'
PAIRS_OUT = './dedup_candidate_pairs.csv'

# -------------------------
# Helpers: normalization
# -------------------------
def normalize_name(s: str) -> str:
    s = (s or '')
    s = s.lower().strip()
    s = re.sub(r'[\.,]',' ', s)
    s = re.sub(r'\b(dr|md|do|prof|mr|mrs|ms|jr|sr|ii|iii)\b', '', s)
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def normalize_phone(s: str) -> str:
    return re.sub(r'[^0-9]', '', (s or ''))

def name_tokens(s: str):
    return [t for t in re.split(r'\s+', s) if t]

def last_name_prefix(s: str, n=4):
    toks = name_tokens(s)
    if toks:
        return toks[-1][:n]
    return ''

def seq_ratio(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()

def token_overlap(a: str, b: str) -> float:
    sa = set(name_tokens(a)); sb = set(name_tokens(b))
    if not sa and not sb:
        return 1.0
    inter = sa & sb; uni = sa | sb
    return len(inter)/len(uni) if uni else 0.0

def phone_last4(s: str): return s[-4:] if len(s)>=4 else ''

# -------------------------
# Union-Find for clustering
# -------------------------
class UF:
    def __init__(self, n): self.p = list(range(n))
    def find(self,x):
        if self.p[x]!=x: self.p[x]=self.find(self.p[x])
        return self.p[x]
    def union(self,a,b):
        ra, rb = self.find(a), self.find(b)
        if ra!=rb: self.p[rb]=ra

# -------------------------
# Core dedupe function
# -------------------------
def dedupe(roster_df, threshold_definite=5.0, threshold_possible=3.0, verbose=True):
    roster = roster_df.copy().fillna('')
    roster['name_norm'] = roster['full_name'].astype(str).map(normalize_name)
    roster['npi_norm'] = roster['npi'].astype(str).str.strip()
    roster['license_norm'] = roster['license_number'].astype(str).str.strip().str.upper()
    roster['license_state_norm'] = roster['license_state'].astype(str).str.strip().str.upper()
    roster['phone_norm'] = roster['practice_phone'].astype(str).map(normalize_phone)
    roster['phone_last4'] = roster['phone_norm'].map(phone_last4)
    roster['last_pref'] = roster['name_norm'].map(lambda x: last_name_prefix(x,4))
    roster['tax_norm'] = roster['taxonomy_code'].astype(str).str.strip().str.upper().fillna('')
    roster['addr_norm'] = (roster['practice_address_line1'].astype(str).fillna('')+' '+roster['practice_city'].astype(str).fillna('')+' '+roster['practice_state'].astype(str).fillna('')+' '+roster['practice_zip'].astype(str).fillna('')).map(lambda x: re.sub(r'[^a-z0-9\s]',' ', x.lower())).map(lambda x: re.sub(r'\s+',' ',x).strip())

    idx = list(roster.index)
    # Build blocks
    blocks = defaultdict(list)
    for i in idx:
        r = roster.loc[i]
        if r['npi_norm'] and r['npi_norm']!='nan': blocks['NPI::'+r['npi_norm']].append(i)
        if r['license_norm'] and r['license_state_norm'] and r['license_norm']!='nan': blocks['LIC::'+r['license_state_norm']+'::'+r['license_norm']].append(i)
        if r['last_pref']: blocks['LNP::'+r['last_pref']].append(i)
        if r['phone_last4']: blocks['PH4::'+r['phone_last4']].append(i)
        if r['tax_norm']: blocks['TAX::'+r['tax_norm']].append(i)

    # Generate candidate pairs from blocks
    candidates = set()
    for k,v in blocks.items():
        if len(v)>1:
            for a,b in combinations(sorted(set(v)),2):
                candidates.add((a,b))
    if verbose: print(f"Generated {len(candidates)} candidate pairs from {len(blocks)} blocks")

    # Score pairs
    pair_data=[]
    for a,b in candidates:
        ra = roster.loc[a]; rb = roster.loc[b]
        score = 0.0; reasons=[]
        if ra['npi_norm'] and rb['npi_norm'] and ra['npi_norm']==rb['npi_norm']:
            score += 6.0; reasons.append('npi_eq')
        if ra['license_norm'] and rb['license_norm'] and ra['license_state_norm'] and rb['license_state_norm'] and ra['license_state_norm']==rb['license_state_norm'] and ra['license_norm']==rb['license_norm']:
            score += 5.0; reasons.append('lic_eq')
        name_sim = seq_ratio(ra['name_norm'], rb['name_norm']); score += name_sim * 3.0
        tok_ov = token_overlap(ra['name_norm'], rb['name_norm']); score += tok_ov * 1.0
        if ra['phone_last4'] and rb['phone_last4'] and ra['phone_last4']==rb['phone_last4']:
            score += 1.5; reasons.append('ph4_eq')
        addr_ov = token_overlap(ra['addr_norm'], rb['addr_norm']); score += addr_ov * 0.8
        if ra['tax_norm'] and rb['tax_norm'] and ra['tax_norm']==rb['tax_norm']:
            score += 0.6
        if ra['npi_norm'] and rb['npi_norm'] and ra['npi_norm']!=rb['npi_norm'] and ra['npi_norm']!='nan' and rb['npi_norm']!='nan':
            score -= 4.0; reasons.append('npi_conflict')
        pair_data.append({'idx_a':a,'idx_b':b,'score':score,'name_sim':round(name_sim,3),'tok_ov':round(tok_ov,3),'addr_ov':round(addr_ov,3),'reasons':';'.join(reasons)})
    pairs_df = pd.DataFrame(pair_data).sort_values('score', ascending=False).reset_index(drop=True)
    pairs_df['match_class'] = pairs_df['score'].apply(lambda s: 'definite' if s>=threshold_definite else ('possible' if s>=threshold_possible else 'nonmatch'))

    # Cluster definite matches
    index_to_pos = {idx[i]:i for i in range(len(idx))}
    uf = UF(len(idx))
    for _,row in pairs_df[pairs_df['match_class']=='definite'].iterrows():
        a = index_to_pos[row['idx_a']]; b = index_to_pos[row['idx_b']]
        uf.union(a,b)
    clusters = defaultdict(list)
    for i in range(len(idx)):
        clusters[uf.find(i)].append(idx[i])

    # Build dedup mapping
    record_to_cluster = {}
    for root, members in clusters.items():
        if len(members)==1:
            record_to_cluster[members[0]] = roster.loc[members[0]]['provider_id']
        else:
            cand_ids = [roster.loc[m]['provider_id'] for m in members]
            canonical = sorted(cand_ids)[0]
            for m in members: record_to_cluster[m] = canonical
    for i in idx:
        if i not in record_to_cluster:
            record_to_cluster[i] = roster.loc[i]['provider_id']

    roster['dedup_cluster_id'] = roster.index.map(lambda x: record_to_cluster.get(x, roster.loc[x]['provider_id']))
    roster.to_csv(OUT_PATH, index=False)
    pairs_df.to_csv(PAIRS_OUT, index=False)

    if verbose:
        n = len(roster_df)
        n_clusters = len(set(record_to_cluster.values()))
        counts = Counter(roster['dedup_cluster_id'])
        dup_counts = sum(1 for c in counts.values() if c>1)
        print(f"Wrote dedup results to {OUT_PATH}")
        print(f"Original records: {n}, Unique clusters after dedup: {n_clusters}, canonical IDs with >1 input records: {dup_counts}")

    return pairs_df, roster, [c for c in clusters.values() if len(c)>1]

# -------------------------
# Run when script executed
# -------------------------
if __name__ == '__main__':
    roster_file = "provider_roster_with_errors.csv"
    roster = pd.read_csv(roster_file, dtype=str).fillna('')
    pairs_df, roster_out, multi = dedupe(roster)
    print("Done. Candidate pairs saved to:", PAIRS_OUT)
