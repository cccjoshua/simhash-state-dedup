"""Checks shared by the tool verifiers. Pure functions of their arguments.

The verifier recomputes every SimHash itself: each whitespace-separated token votes on 64 bits with the
first 8 bytes of its SHA-256, and a bit is set when its sum is positive.
"""

import hashlib
import re

SNAPSHOT_ID = re.compile(r"^s\d{2}$")
FINGERPRINT = re.compile(r"^[0-9a-f]{16}$")
MAX_SEED = 1_000_000
THRESHOLD = 6
MAX_SNAPSHOTS = 25


def result(valid, message, *, score=None, **details):
    return {
        "valid": valid,
        "score": float(valid) if score is None else score,
        "message": message,
        "details": details,
    }


def seed_problem(seed):
    if not 0 <= seed <= MAX_SEED:
        return f"seed must be between 0 and {MAX_SEED}"
    return None


def id_problem(snapshot_id):
    if not SNAPSHOT_ID.fullmatch(snapshot_id):
        return f"{snapshot_id!r} is not a snapshot id like s00"
    return None


def simhash(lines):
    sums = [0] * 64
    for line in lines:
        for token in line.split():
            value = int.from_bytes(hashlib.sha256(token.encode()).digest()[:8], "big")
            for bit in range(64):
                sums[bit] += 1 if value >> bit & 1 else -1
    return sum(1 << bit for bit in range(64) if sums[bit] > 0)


def grouping(snapshots, threshold=THRESHOLD):
    """Connected components of 'Hamming distance at most threshold', as a set of frozensets of ids."""
    prints = {snapshot.snapshot_id: simhash(snapshot.lines) for snapshot in snapshots}
    ids = sorted(prints)
    parent = {snapshot_id: snapshot_id for snapshot_id in ids}

    def root(snapshot_id):
        while parent[snapshot_id] != snapshot_id:
            snapshot_id = parent[snapshot_id]
        return snapshot_id

    for index, left in enumerate(ids):
        for right in ids[index + 1:]:
            if (prints[left] ^ prints[right]).bit_count() <= threshold:
                parent[root(right)] = root(left)
    found = {}
    for snapshot_id in ids:
        found.setdefault(root(snapshot_id), set()).add(snapshot_id)
    return {frozenset(group) for group in found.values()}


def pair_agreement(given, expected, ids):
    """The share of snapshot pairs on which two groupings agree (together or apart): the Rand index."""
    def together(groups):
        return {(left, right) for group in groups for left in group for right in group if left < right}

    pairs = len(ids) * (len(ids) - 1) // 2
    if not pairs:
        return 1.0
    return 1 - len(together(given) ^ together(expected)) / pairs
