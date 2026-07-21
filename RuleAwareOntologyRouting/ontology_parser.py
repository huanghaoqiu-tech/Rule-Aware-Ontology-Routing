"""Offline ontology indexing: TBox + SWRL rule-head harvesting (OWL RDF/XML & OBO)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Set, Tuple


_CAMEL_SPLIT = re.compile(r"(?<=[a-z])(?=[A-Z])|[_\-]+")
_STOP = {
    "a", "an", "the", "of", "and", "or", "to", "in", "on", "for", "is", "are",
    "be", "as", "by", "with", "from", "that", "this", "it", "at", "onto", "owl",
    "rdf", "rdfs", "xsd", "xml", "class", "property", "type", "thing", "nothing",
    "label", "comment", "version", "import", "ontology", "http", "https", "purl",
    "obolibrary", "obo", "www", "org", "com", "resource", "about", "description",
}


def normalize_token(tok: str) -> str:
    tok = tok.strip().lower()
    tok = re.sub(r"[^a-z0-9_\-]+", "", tok)
    return tok


def expand_term(raw: str) -> Set[str]:
    out: Set[str] = set()
    if not raw:
        return out
    raw = raw.strip().strip("\"'")
    if "#" in raw:
        raw = raw.rsplit("#", 1)[-1]
    if "/" in raw:
        raw = raw.rsplit("/", 1)[-1]
    # drop CURIE prefixes GO_0001 / GO:0001
    raw = re.sub(r"^[A-Za-z]{1,12}[_:]", "", raw)
    if re.fullmatch(r"\d+", raw or ""):
        return out
    parts = _CAMEL_SPLIT.split(raw)
    parts = [p for p in parts if p]
    candidates = parts + ["".join(parts), raw]
    # also split whitespace labels
    candidates += re.split(r"\s+", raw)
    for p in candidates:
        t = normalize_token(p)
        if len(t) >= 3 and len(t) <= 40 and t not in _STOP and not t.isdigit():
            # skip mostly-numeric tokens (ontology IDs)
            digits = sum(ch.isdigit() for ch in t)
            if digits > 0 and digits >= len(t) // 2:
                continue
            out.add(t)
    return out


def _is_obo(data_head: bytes) -> bool:
    h = data_head[:2048].lower()
    return h.startswith(b"format-version:") or b"\nformat-version:" in h or b"format-version:" in h[:200]


def extract_from_obo_stream(path: Path, max_terms: int = 80000) -> Tuple[Set[str], Set[str]]:
    terms: Set[str] = set()
    with open(path, "rb") as f:
        for raw in f:
            line = raw.decode("utf-8", "ignore").rstrip()
            if line.startswith("name:"):
                terms |= expand_term(line[5:].strip())
            elif line.startswith("id:"):
                terms |= expand_term(line[3:].strip())
            elif line.startswith("synonym:"):
                # synonym: "foo" EXACT []
                m = re.search(r'"([^"]+)"', line)
                if m:
                    terms |= expand_term(m.group(1))
            elif line.startswith("def:"):
                m = re.search(r'"([^"]+)"', line)
                if m:
                    for w in re.split(r"\W+", m.group(1)):
                        terms |= expand_term(w)
            if len(terms) >= max_terms:
                break
    return terms, set()


_URI_ATTR = re.compile(
    rb'(?:rdf:(?:about|ID|resource)|IRI)\s*=\s*"([^"]+)"', re.I
)
_LABEL = re.compile(
    rb"<rdfs:label[^>]*>([^<]{2,160})</rdfs:label>", re.I
)
_HEAD_BLOCK = re.compile(
    rb"<swrl:head\b[^>]*>(.*?)</swrl:head>", re.I | re.S
)
_PRED = re.compile(
    rb"swrl:(?:class|property)Predicate[^>]*rdf:resource=\"([^\"]+)\"", re.I
)


def extract_from_owl_stream(
    path: Path,
    max_bytes: int = 150_000_000,
    max_terms: int = 100000,
) -> Tuple[Set[str], Set[str]]:
    terms: Set[str] = set()
    heads: Set[str] = set()
    buf = b""
    read = 0
    with open(path, "rb") as f:
        while read < max_bytes:
            chunk = f.read(4 * 1024 * 1024)
            if not chunk:
                break
            read += len(chunk)
            data = buf + chunk
            # keep tail for cross-chunk regex
            for m in _URI_ATTR.finditer(data):
                uri = m.group(1).decode("utf-8", "ignore")
                if "swrl" in uri.lower() or "variable" in uri.lower():
                    continue
                terms |= expand_term(uri)
            for m in _LABEL.finditer(data):
                label = m.group(1).decode("utf-8", "ignore")
                for w in re.split(r"\W+", label):
                    terms |= expand_term(w)
            for m in _HEAD_BLOCK.finditer(data):
                block = m.group(1)
                for pm in _PRED.finditer(block):
                    heads |= expand_term(pm.group(1).decode("utf-8", "ignore"))
                for pm in _URI_ATTR.finditer(block):
                    uri = pm.group(1).decode("utf-8", "ignore")
                    if "swrl" in uri.lower() or "Variable" in uri:
                        continue
                    heads |= expand_term(uri)
            buf = data[-200_000:]
            if len(terms) >= max_terms:
                break
    terms |= heads
    return terms, heads


def index_ontology_file(
    path: Path,
    large_threshold_mb: float = 80,
    window_mb: float = 40,
    max_bytes_per_ontology: int = 150_000_000,
) -> Tuple[Set[str], Set[str]]:
    with open(path, "rb") as f:
        head = f.read(4096)
    if _is_obo(head) or path.suffix.lower() == ".obo":
        return extract_from_obo_stream(path)
    # full-ish stream for OWL
    return extract_from_owl_stream(path, max_bytes=max_bytes_per_ontology)


def tokenize_query(query: str) -> list[str]:
    toks = []
    for w in re.split(r"\W+", query.lower()):
        t = normalize_token(w)
        if len(t) >= 3 and t not in _STOP and not t.isdigit():
            toks.append(t)
    seen = set()
    out = []
    for t in toks:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out
