"""Online Rule-Aware Router: CBF screening → hybrid lookup → weighted top-k."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional

from cbf import CountingBloomFilter
from hybrid_index import HybridInvertedIndex
from ontology_parser import tokenize_query
from weighted_scoring import rank_ontologies, score_all_above_threshold


@dataclass
class RouteResult:
    selected: List[str]
    scores: List[tuple[str, float]]
    filtered_terms: List[str]
    dropped_terms: List[str]
    n_above_tau: int
    latency_ms: float


class RuleAwareRouter:
    def __init__(
        self,
        index: HybridInvertedIndex,
        cbf: CountingBloomFilter,
        weight_tbox: float = 1.0,
        weight_head: float = 1.5,
        threshold_tau: float = 0.5,
        top_k: int = 3,
    ):
        self.index = index
        self.cbf = cbf
        self.weight_tbox = weight_tbox
        self.weight_head = weight_head
        self.threshold_tau = threshold_tau
        self.top_k = top_k

    def route(self, query: str, use_rule_heads: bool = True) -> RouteResult:
        t0 = time.perf_counter()
        tokens = tokenize_query(query)
        filtered, dropped = [], []
        for t in tokens:
            if self.cbf.contains(t):
                filtered.append(t)
            else:
                dropped.append(t)

        wh = self.weight_head if use_rule_heads else 0.0
        scored_all = score_all_above_threshold(
            filtered,
            self.index,
            weight_tbox=self.weight_tbox,
            weight_head=wh,
            threshold_tau=self.threshold_tau,
        )
        ranked = scored_all[: self.top_k]
        selected = [o for o, _ in ranked]
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return RouteResult(
            selected=selected,
            scores=ranked,
            filtered_terms=filtered,
            dropped_terms=dropped,
            n_above_tau=len(scored_all),
            latency_ms=latency_ms,
        )
