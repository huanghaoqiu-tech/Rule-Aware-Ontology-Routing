"""Weighted scoring for Rule-Aware Ontology Routing.

S(O_i) = sum_{t in T_Q} ( w_t * I(t in I_tbox[O_i]) + w_h * I(t in I_head[O_i]) )

Normalized to [0,1] by dividing by |T_Q| * w_h so that threshold τ=0.5 is meaningful.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

from hybrid_index import HybridInvertedIndex


def score_ontology(
    ontology: str,
    query_terms: Iterable[str],
    index: HybridInvertedIndex,
    weight_tbox: float = 1.0,
    weight_head: float = 1.5,
) -> float:
    terms = [t.strip().lower() for t in query_terms if t and t.strip()]
    if not terms:
        return 0.0
    raw = 0.0
    for t in terms:
        tb, hd = index.lookup(t)
        if ontology in tb:
            raw += weight_tbox
        if ontology in hd:
            raw += weight_head
    # Max raw if every filtered term hits a rule-head
    denom = len(terms) * max(weight_head, weight_tbox)
    return raw / denom if denom > 0 else 0.0


def rank_ontologies(
    query_terms: Iterable[str],
    index: HybridInvertedIndex,
    weight_tbox: float = 1.0,
    weight_head: float = 1.5,
    threshold_tau: float = 0.5,
    top_k: int = 3,
) -> List[Tuple[str, float]]:
    """Return ranked (ontology, score) pairs above τ, truncated to top_k."""
    terms = [t.strip().lower() for t in query_terms if t and t.strip()]
    cands = index.candidate_ontologies(terms)
    scored: List[Tuple[str, float]] = []
    for ont in cands:
        s = score_ontology(ont, terms, index, weight_tbox, weight_head)
        if s >= threshold_tau:
            scored.append((ont, s))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored[:top_k]


def score_all_above_threshold(
    query_terms: Iterable[str],
    index: HybridInvertedIndex,
    weight_tbox: float = 1.0,
    weight_head: float = 1.5,
    threshold_tau: float = 0.5,
) -> List[Tuple[str, float]]:
    """All candidates with S >= τ (used for AOL diagnostics before top-k cut)."""
    terms = [t.strip().lower() for t in query_terms if t and t.strip()]
    cands = index.candidate_ontologies(terms)
    scored = []
    for ont in cands:
        s = score_ontology(ont, terms, index, weight_tbox, weight_head)
        if s >= threshold_tau:
            scored.append((ont, s))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored
