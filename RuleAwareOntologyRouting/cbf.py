"""Counting Bloom Filter (CBF) for sub-millisecond vocabulary screening.

Supports insert / membership / delete via counters (dynamic ontology updates).
Configured with size_bits=1_000_000 and num_hashes=7 per experimental setup.
"""
from __future__ import annotations

import hashlib
import struct
from typing import Iterable


class CountingBloomFilter:
    """Array-of-counters Bloom filter (8-bit counters by default)."""

    def __init__(self, size_bits: int = 1_000_000, num_hashes: int = 7):
        if size_bits <= 0 or num_hashes <= 0:
            raise ValueError("size_bits and num_hashes must be positive")
        self.size_bits = int(size_bits)
        self.num_hashes = int(num_hashes)
        self.counters = bytearray(self.size_bits)  # saturating at 255
        self.n_inserted = 0

    def _hashes(self, item: str) -> list[int]:
        """Double-hashing: h_i = h1 + i*h2 (mod m)."""
        raw = item.encode("utf-8", errors="ignore")
        h1 = int.from_bytes(hashlib.md5(raw).digest()[:8], "little")
        h2 = int.from_bytes(hashlib.sha1(raw).digest()[:8], "little") | 1
        m = self.size_bits
        return [((h1 + i * h2) % m) for i in range(self.num_hashes)]

    def add(self, item: str) -> None:
        for idx in self._hashes(item.lower()):
            if self.counters[idx] < 255:
                self.counters[idx] += 1
        self.n_inserted += 1

    def add_many(self, items: Iterable[str]) -> None:
        for it in items:
            self.add(it)

    def contains(self, item: str) -> bool:
        return all(self.counters[idx] > 0 for idx in self._hashes(item.lower()))

    def remove(self, item: str) -> bool:
        """Decrement counters if item was present (best-effort delete)."""
        idxs = self._hashes(item.lower())
        if not all(self.counters[i] > 0 for i in idxs):
            return False
        for i in idxs:
            if self.counters[i] > 0:
                self.counters[i] -= 1
        self.n_inserted = max(0, self.n_inserted - 1)
        return True

    def false_positive_rate_estimate(self) -> float:
        """Classic Bloom FPR estimate: (1 - e^{-kn/m})^k."""
        import math

        m, k, n = self.size_bits, self.num_hashes, max(1, self.n_inserted)
        return (1.0 - math.exp(-k * n / m)) ** k

    def empirically_fpr(self, negative_terms: Iterable[str]) -> float:
        negs = list(negative_terms)
        if not negs:
            return 0.0
        fps = sum(1 for t in negs if self.contains(t))
        return fps / len(negs)

    def to_bytes(self) -> bytes:
        header = struct.pack("<IIQ", self.size_bits, self.num_hashes, self.n_inserted)
        return header + bytes(self.counters)

    @classmethod
    def from_bytes(cls, blob: bytes) -> "CountingBloomFilter":
        size_bits, num_hashes, n_inserted = struct.unpack("<IIQ", blob[:16])
        obj = cls(size_bits=size_bits, num_hashes=num_hashes)
        obj.counters = bytearray(blob[16 : 16 + size_bits])
        obj.n_inserted = n_inserted
        return obj
