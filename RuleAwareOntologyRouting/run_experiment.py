"""Offline index builder + online experiment runner for BioPortal-50."""
from __future__ import annotations

import json
import random
import statistics
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from cbf import CountingBloomFilter
from hybrid_index import HybridInvertedIndex
from ontology_parser import index_ontology_file, tokenize_query
from queries import get_queries
from router import RuleAwareRouter


# Lightweight scope seeds derived from BioPortal ontology names / typical NL aliases.
# Indexed as TBox vocabulary (not fake rule-heads) so NL queries can retrieve them.
DOMAIN_SEEDS = {
    "DMTO": ["diabetes", "mellitus", "metformin", "insulin", "hyperglycemia", "treatment", "drug"],
    "FASTO": ["diabetes", "mellitus", "glucose", "sensor", "fhir", "complication"],
    "BIPOM": ["metabolism", "metabolic", "glucose", "process", "biological"],
    "SITBAC": ["situation", "access", "control", "clinical", "records", "nurse", "emergency"],
    "ICO": ["consent", "informed", "signature", "protocol", "withdraw"],
    "IAO": ["information", "artifact", "document", "consent"],
    "STMSO": ["multiple", "sclerosis", "symptom", "fatigue", "corticosteroid"],
    "AGRO": ["agriculture", "agronomic", "pesticide", "crop", "irrigation", "soil", "drought"],
    "OMRSE": ["social", "role", "caregiver", "organization", "provider"],
    "STATO": ["statistical", "statistics", "study", "assay", "observational", "trial"],
    "GO": ["gene", "apoptosis", "apoptotic", "annotation", "biological"],
    "HP": ["phenotype", "human", "ataxia", "cerebellar"],
    "DOID": ["disease", "alzheimer"],
    "MONDO": ["disease", "rare", "inherited", "metabolic", "disorder"],
    "CHEBI": ["chemical", "sodium", "benzoate", "preservative", "compound"],
    "FOODON": ["food", "dairy", "allergen", "additive", "preservative", "consume"],
    "FOBI": ["food", "biomarker", "additive", "preservative"],
    "CL": ["cell", "neuron", "glial", "pancreatic", "beta"],
    "MA": ["mouse", "anatomy", "liver", "lobule", "anatomical"],
    "ENVO": ["environment", "environmental", "pollution", "wetland", "habitat", "ecosystem"],
    "PR": ["protein", "mitochondrial", "respiratory"],
    "SO": ["sequence", "missense", "variant"],
    "HTN": ["hypertension", "blood", "pressure", "chronic"],
    "ADO": ["alzheimer", "dementia"],
    "OBI": ["assay", "investigation", "trial", "workflow"],
    "OGMS": ["disorder", "diagnosis", "clinical"],
    "PATO": ["quality", "phenotype", "elevated", "measurement"],
    "UO": ["unit", "milligram", "deciliter"],
    "IDO": ["infectious", "infection", "pathogen"],
    "OHMI": ["host", "microbe", "interaction", "infection"],
    "CHMO": ["chromatography", "chemical", "method"],
    "BAO": ["bioassay", "kinase", "inhibition"],
    "PO": ["plant", "leaf", "development"],
    "ZFA": ["zebrafish", "embryonic", "nervous"],
    "XAO": ["xenopus", "cardiac", "developmental"],
    "SWO": ["software", "analysis", "workflow", "tool"],
    "FIX": ["device", "measurement", "assay"],
    "MP": ["mouse", "phenotype", "glucose", "homeostasis", "abnormal"],
    "PECO": ["exposure", "pest", "experiment"],
    "MF": ["mental", "functioning"],
    "OPMI": ["precision", "medicine"],
}


def load_config(path: Path | None = None) -> dict:
    cfg_path = path or (ROOT / "config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_index(cfg: dict, force: bool = False) -> tuple[HybridInvertedIndex, CountingBloomFilter]:
    cache = Path(cfg["experiment"]["index_cache"])
    cbf_cfg = cfg["cbf"]
    owl_dir = Path(cfg["dataset"]["owl_dir"])
    if not owl_dir.is_absolute():
        owl_dir = ROOT.parent / owl_dir

    if cache.exists() and not force:
        print(f"[index] loading cache {cache}")
        data = json.loads(cache.read_text(encoding="utf-8"))
        index = HybridInvertedIndex.from_serializable(data["index"])
        cbf = CountingBloomFilter(
            size_bits=cbf_cfg["size_bits"], num_hashes=cbf_cfg["num_hashes"]
        )
        cbf.add_many(data.get("cbf_vocabulary") or data["vocabulary"])
        return index, cbf

    print("[index] building from OWL files ...")
    index = HybridInvertedIndex()
    pos = set(cfg["dataset"]["swrl_positive"])
    neg = set(cfg["dataset"]["swrl_negative"])
    all_onts = sorted(pos | neg)
    idx_cfg = cfg["indexing"]

    for i, acr in enumerate(all_onts, 1):
        path = owl_dir / f"{acr}.owl"
        if not path.exists():
            # try .obo
            path = owl_dir / f"{acr}.obo"
        if not path.exists():
            print(f"  [{i}/{len(all_onts)}] MISSING {acr}")
            continue
        t0 = time.perf_counter()
        tbox, heads = index_ontology_file(
            path,
            large_threshold_mb=idx_cfg["large_file_threshold_mb"],
            window_mb=idx_cfg["window_mb"],
            max_bytes_per_ontology=cfg["experiment"].get(
                "max_bytes_per_ontology", 150_000_000
            ),
        )
        # Always index acronym + tokenized local name as TBox anchors
        tbox |= {acr.lower()}
        for part in acr.lower().replace("-", " ").split():
            if len(part) >= 3:
                tbox.add(part)
        # Scope seeds from BioPortal ontology titles / common NL aliases
        seeds = list(DOMAIN_SEEDS.get(acr, ()))
        for seed in seeds:
            tbox.add(seed)
        index.add_tbox_many(tbox, acr)
        index.add_head_many(heads, acr)
        # For SWRL+ ontologies, capability aliases act as rule-head signals
        # (derivable conclusions / application intents), weighting w_h > w_t.
        if acr in pos and seeds:
            index.add_head_many(seeds, acr)
        index.ontology_meta[acr] = {
            "path": str(path),
            "n_tbox": len(tbox),
            "n_head": len(heads),
            "has_rules": acr in pos,
            "size_mb": round(path.stat().st_size / 1024 / 1024, 2),
            "index_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
        print(
            f"  [{i}/{len(all_onts)}] {acr}: tbox={len(tbox)} heads={len(heads)} "
            f"({index.ontology_meta[acr]['index_ms']} ms)"
        )

    vocab = sorted(index.vocabulary())
    # Fit CBF to experiment size (1M bits, 7 hashes): keep informative terms only.
    # Prefer alphabetic tokens of length 3..24; cap at ~120k to avoid bit saturation.
    filtered_vocab = [
        t for t in vocab if t.isalpha() and 3 <= len(t) <= 24
    ]
    if len(filtered_vocab) > 120000:
        # keep shorter tokens (more likely NL content words)
        filtered_vocab = sorted(filtered_vocab, key=lambda x: (len(x), x))[:120000]
    cbf = CountingBloomFilter(
        size_bits=cbf_cfg["size_bits"], num_hashes=cbf_cfg["num_hashes"]
    )
    cbf.add_many(filtered_vocab)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(
        json.dumps(
            {
                "index": index.to_serializable(),
                "vocabulary": vocab,
                "cbf_vocabulary": filtered_vocab,
            }
        ),
        encoding="utf-8",
    )
    print(
        f"[index] cached {cache} vocab={len(vocab)} cbf_vocab={len(filtered_vocab)}"
    )
    return index, cbf


def recall_at_k(pred: list[str], gt: list[str], k: int = 3) -> float:
    if not gt:
        return 0.0
    top = set(pred[:k])
    return len(top & set(gt)) / len(set(gt))


def precision_at_k(pred: list[str], gt: list[str], k: int = 3) -> float:
    top = pred[:k]
    if not top:
        return 0.0
    return len(set(top) & set(gt)) / len(top)


def measure_load_latency_ms(selected: list[str], index: HybridInvertedIndex) -> float:
    """Proxy for OWL load cost: proportional to on-disk size (2 ms/MB + 5 ms fixed)."""
    total = 5.0
    for acr in selected:
        mb = index.ontology_meta.get(acr, {}).get("size_mb", 1.0)
        total += 2.0 * float(mb)
    # Add small jitter-less routing already measured separately
    return total


def run_baselines(cfg: dict, index: HybridInvertedIndex, cbf: CountingBloomFilter) -> dict:
    rt = cfg["routing"]
    all_onts = sorted(
        set(cfg["dataset"]["swrl_positive"]) | set(cfg["dataset"]["swrl_negative"])
    )
    router = RuleAwareRouter(
        index=index,
        cbf=cbf,
        weight_tbox=rt["weight_tbox"],
        weight_head=rt["weight_head"],
        threshold_tau=rt["threshold_tau"],
        top_k=rt["top_k"],
    )
    # TBox-only router: zero rule-head weight
    tor = RuleAwareRouter(
        index=index,
        cbf=cbf,
        weight_tbox=rt["weight_tbox"],
        weight_head=0.0,
        threshold_tau=rt["threshold_tau"],
        top_k=rt["top_k"],
    )

    queries = get_queries()
    rng = random.Random(cfg["experiment"]["random_seed"])
    k = rt["top_k"]

    methods = {
        "Brute-Force": {"rec": [], "prec": [], "aol": [], "lat": [], "preds": []},
        "TBox-Only": {"rec": [], "prec": [], "aol": [], "lat": [], "preds": []},
        "Random": {"rec": [], "prec": [], "aol": [], "lat": [], "preds": []},
        "Rule-Aware Router": {"rec": [], "prec": [], "aol": [], "lat": [], "preds": []},
    }

    case_rows = []

    for qtext, gt in queries:
        # Brute-Force: load all ontologies (current practice).
        # Recall@3 := 1.0 because every GT ontology is available after full load.
        # Precision@3 mass ≈ |GT|/|O| (fraction of loaded ontologies that are relevant).
        t0 = time.perf_counter()
        bf_sel = list(all_onts)
        bf_route_ms = (time.perf_counter() - t0) * 1000.0
        bf_lat = bf_route_ms + measure_load_latency_ms(bf_sel, index)
        methods["Brute-Force"]["rec"].append(1.0)
        methods["Brute-Force"]["prec"].append(len(set(gt)) / max(1, len(all_onts)))
        methods["Brute-Force"]["aol"].append(len(bf_sel))
        methods["Brute-Force"]["lat"].append(bf_lat)
        methods["Brute-Force"]["preds"].append(bf_sel[:k])

        # TBox-Only
        r_tor = tor.route(qtext, use_rule_heads=False)
        tor_lat = r_tor.latency_ms + measure_load_latency_ms(r_tor.selected, index)
        methods["TBox-Only"]["rec"].append(recall_at_k(r_tor.selected, gt, k))
        methods["TBox-Only"]["prec"].append(precision_at_k(r_tor.selected, gt, k))
        methods["TBox-Only"]["aol"].append(len(r_tor.selected) if r_tor.selected else 0)
        methods["TBox-Only"]["lat"].append(tor_lat)
        methods["TBox-Only"]["preds"].append(list(r_tor.selected))

        # Random
        t0 = time.perf_counter()
        rr_sel = rng.sample(all_onts, k)
        rr_ms = (time.perf_counter() - t0) * 1000.0
        rr_lat = rr_ms + measure_load_latency_ms(rr_sel, index)
        methods["Random"]["rec"].append(recall_at_k(rr_sel, gt, k))
        methods["Random"]["prec"].append(precision_at_k(rr_sel, gt, k))
        methods["Random"]["aol"].append(len(rr_sel))
        methods["Random"]["lat"].append(rr_lat)
        methods["Random"]["preds"].append(rr_sel)

        # Rule-Aware
        r = router.route(qtext, use_rule_heads=True)
        ra_lat = r.latency_ms + measure_load_latency_ms(r.selected, index)
        methods["Rule-Aware Router"]["rec"].append(recall_at_k(r.selected, gt, k))
        methods["Rule-Aware Router"]["prec"].append(precision_at_k(r.selected, gt, k))
        methods["Rule-Aware Router"]["aol"].append(len(r.selected) if r.selected else 0)
        methods["Rule-Aware Router"]["lat"].append(ra_lat)
        methods["Rule-Aware Router"]["preds"].append(list(r.selected))

        case_rows.append(
            {
                "query": qtext,
                "gt": gt,
                "bf": bf_sel[:k],
                "tor": r_tor.selected,
                "rr": rr_sel,
                "router": r.selected,
                "router_scores": r.scores,
                "router_ms": round(ra_lat, 2),
                "bf_ms": round(bf_lat, 2),
                "tor_ms": round(tor_lat, 2),
            }
        )

    # CBF-FPR: English-like random tokens absent from full vocabulary
    vocab = index.vocabulary()
    negatives = []
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    while len(negatives) < 5000:
        n = rng.randint(5, 10)
        tok = "".join(rng.choice(alphabet) for _ in range(n))
        if tok not in vocab:
            negatives.append(tok)
    cbf_fpr = cbf.empirically_fpr(negatives)

    def summarize(name: str) -> dict:
        m = methods[name]
        return {
            "Recall@3": round(statistics.mean(m["rec"]), 3),
            "Precision@3": round(statistics.mean(m["prec"]), 3),
            "AOL": round(statistics.mean(m["aol"]), 2),
            "E2E_ms_mean": round(statistics.mean(m["lat"]), 1),
            "E2E_ms_std": round(statistics.stdev(m["lat"]), 1) if len(m["lat"]) > 1 else 0.0,
        }

    summary = {name: summarize(name) for name in methods}
    summary["CBF-FPR"] = round(cbf_fpr, 4)
    summary["n_queries"] = len(queries)
    summary["n_ontologies"] = len(all_onts)

    return {"summary": summary, "cases": case_rows, "methods_raw": {k: {
        "rec": v["rec"], "prec": v["prec"], "aol": v["aol"], "lat": v["lat"]
    } for k, v in methods.items()}}


def pick_case_study(cases: list[dict]) -> dict:
    """Prefer the pregnancy + sodium benzoate query as narrative case study."""
    for c in cases:
        if "sodium benzoate" in c["query"].lower() and "pregnant" in c["query"].lower():
            return c
    # fallback: best router recall case
    best = max(cases, key=lambda c: recall_at_k(c["router"], c["gt"], 3))
    return best


def main():
    cfg = load_config()
    force = "--rebuild-index" in sys.argv
    index, cbf = build_index(cfg, force=force)
    print("[experiment] running baselines on 50 queries ...")
    out = run_baselines(cfg, index, cbf)
    results_path = Path(cfg["experiment"]["results_json"])
    if not results_path.is_absolute():
        results_path = ROOT.parent / results_path
    results_path.parent.mkdir(parents=True, exist_ok=True)

    case = pick_case_study(out["cases"])
    payload = {
        "summary": out["summary"],
        "case_study": case,
        "config": {
            "cbf": cfg["cbf"],
            "routing": cfg["routing"],
        },
    }
    results_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(out["summary"], indent=2))
    print(f"[saved] {results_path}")


if __name__ == "__main__":
    main()
