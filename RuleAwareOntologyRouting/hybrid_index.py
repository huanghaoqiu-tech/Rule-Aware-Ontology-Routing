"""Hybrid inverted index: each term maps to TBox and rule-head posting lists.

I_tbox[t]  -> ontologies where t appears in the terminological signature
I_head[t]  -> ontologies where t appears as a SWRL rule-head atom
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Set


@dataclass
class HybridInvertedIndex:
    tbox: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    head: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    ontology_meta: Dict[str, dict] = field(default_factory=dict)

    def add_tbox(self, term: str, ontology: str) -> None:
        t = term.strip().lower()
        if t:
            self.tbox[t].add(ontology)

    def add_head(self, term: str, ontology: str) -> None:
        t = term.strip().lower()
        if t:
            self.head[t].add(ontology)

    def add_tbox_many(self, terms: Iterable[str], ontology: str) -> None:
        for t in terms:
            self.add_tbox(t, ontology)

    def add_head_many(self, terms: Iterable[str], ontology: str) -> None:
        for t in terms:
            self.add_head(t, ontology)

    def lookup(self, term: str) -> tuple[Set[str], Set[str]]:
        t = term.strip().lower()
        return set(self.tbox.get(t, ())), set(self.head.get(t, ()))

    def candidate_ontologies(self, terms: Iterable[str]) -> Set[str]:
        out: Set[str] = set()
        for t in terms:
            tb, hd = self.lookup(t)
            out |= tb
            out |= hd
        return out

    def vocabulary(self) -> Set[str]:
        return set(self.tbox.keys()) | set(self.head.keys())

    def to_serializable(self) -> dict:
        return {
            "tbox": {k: sorted(v) for k, v in self.tbox.items()},
            "head": {k: sorted(v) for k, v in self.head.items()},
            "ontology_meta": self.ontology_meta,
        }

    @classmethod
    def from_serializable(cls, data: dict) -> "HybridInvertedIndex":
        idx = cls()
        for k, v in data.get("tbox", {}).items():
            idx.tbox[k] = set(v)
        for k, v in data.get("head", {}).items():
            idx.head[k] = set(v)
        idx.ontology_meta = dict(data.get("ontology_meta", {}))
        return idx

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_serializable()), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "HybridInvertedIndex":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_serializable(data)
