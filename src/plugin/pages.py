"""Page snapshots built from a seed: several page states, each captured a few times with noise.

A snapshot is an accessibility tree as text lines. Snapshots of one state share every structural line
and differ only in noise lines: ad banners, clocks and session ids. The SimHash of a snapshot is over
its whitespace-separated tokens, each weighted 1: for each of 64 bits, add 1 when the bit of the
token's hash (the first 8 bytes of its SHA-256) is set and subtract 1 when not; the fingerprint bit is
set when the sum is positive. Snapshots of one state are within THRESHOLD of each other, snapshots
of different states are farther apart than THRESHOLD, and the states themselves more than twice
THRESHOLD apart: a capture or a state that breaks this is drawn again.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import cache

MAX_SEED = 1_000_000
THRESHOLD = 6
MAX_SNAPSHOTS = 25  # the most snapshots one distances call measures from; a seed has at most 24
ROLES = ("button", "link", "heading", "textbox", "checkbox", "tab", "listitem", "image", "menuitem")
WORDS = (
    "account", "add", "address", "apply", "back", "billing", "browse", "cancel", "cart", "change", "checkout",
    "close", "compare", "confirm", "contact", "continue", "coupon", "delete", "delivery", "details", "download",
    "edit", "email", "export", "filter", "gift", "help", "history", "home", "invoice", "item", "language",
    "login", "logout", "manage", "menu", "message", "more", "next", "notifications", "order", "orders",
    "password", "payment", "phone", "plan", "previous", "price", "privacy", "product", "profile", "quantity",
    "rating", "remove", "reorder", "reports", "return", "review", "reviews", "save", "search", "security",
    "settings", "share", "shipping", "show", "size", "sort", "status", "submit", "subscribe", "summary",
    "support", "team", "terms", "total", "track", "update", "upgrade", "upload", "view", "wishlist",
)


@dataclass(frozen=True)
class Snapshot:
    snapshot_id: str
    state: int
    lines: tuple[str, ...]


class Draws:
    """A deterministic stream of choices from the seed: SHA-256 of the seed and a counter."""

    def __init__(self, seed: int) -> None:
        self.seed, self.count = seed, 0

    def below(self, bound: int) -> int:
        digest = hashlib.sha256(f"simhash-dedup:{self.seed}:{self.count}".encode()).digest()
        self.count += 1
        return int.from_bytes(digest[:8], "big") % bound

    def pick(self, items):
        return items[self.below(len(items))]

    def shuffled(self, items):
        items = list(items)
        for index in range(len(items) - 1, 0, -1):
            other = self.below(index + 1)
            items[index], items[other] = items[other], items[index]
        return items


def simhash(lines) -> int:
    return _simhash(tuple(lines))


@cache
def _simhash(lines: tuple[str, ...]) -> int:
    sums = [0] * 64
    for line in lines:
        for token in line.split():
            value = int.from_bytes(hashlib.sha256(token.encode()).digest()[:8], "big")
            for bit in range(64):
                sums[bit] += 1 if value >> bit & 1 else -1
    return sum(1 << bit for bit in range(64) if sums[bit] > 0)


def hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def _state(draws: Draws, number: int) -> tuple[str, ...]:
    lines = [f"heading {draws.pick(WORDS)} {draws.pick(WORDS)} page-{number}"]
    for index in range(30 + draws.below(8)):
        words = " ".join(draws.pick(WORDS) for _ in range(4 + draws.below(4)))
        lines.append(f"{draws.pick(ROLES)} {words} node-{number}-{index}")
    return tuple(lines)


def _noise(draws: Draws) -> list[str]:
    kinds = (
        lambda: f"ad banner campaign-{draws.below(100_000)}",
        lambda: f"clock {draws.below(24):02d}:{draws.below(60):02d}:{draws.below(60):02d}",
        lambda: f"session token-{draws.below(16 ** 8):08x}",
        lambda: f"badge {draws.below(20)} unread",
    )
    return [draws.pick(kinds)() for _ in range(1 + draws.below(2))]


@cache
def build_snapshots(seed: int) -> tuple[Snapshot, ...]:
    if not 0 <= seed <= MAX_SEED:
        raise ValueError(f"seed must be between 0 and {MAX_SEED}")
    draws = Draws(seed)
    states: list[tuple[str, ...]] = []
    captures: list[list[tuple[str, ...]]] = []
    earlier: list[tuple[str, ...]] = []  # every capture of the states drawn so far
    for number in range(4 + draws.below(3)):  # 4 to 6 states
        while True:
            base = _state(draws, number)
            if all(hamming(simhash(base), simhash(other)) > 2 * THRESHOLD for other in states):
                break
        taken: list[tuple[str, ...]] = []
        for _ in range(1 + draws.below(4)):  # 1 to 4 captures
            while True:
                lines = list(base)
                for line in _noise(draws):
                    lines.insert(draws.below(len(lines) + 1), line)
                same = all(hamming(simhash(lines), simhash(other)) <= THRESHOLD for other in taken + [base])
                apart = all(hamming(simhash(lines), simhash(other)) > THRESHOLD for other in earlier)
                if same and apart:
                    break
            taken.append(tuple(lines))
        states.append(base)
        captures.append(taken)
        earlier.extend(taken)
    order = draws.shuffled((state, lines) for state, taken in enumerate(captures) for lines in taken)
    return tuple(Snapshot(f"s{index:02d}", state, lines) for index, (state, lines) in enumerate(order))


def groups(snapshots) -> list[list[str]]:
    """Connected components of 'distance at most THRESHOLD', each sorted, sorted by first id."""
    prints = {snapshot.snapshot_id: simhash(snapshot.lines) for snapshot in snapshots}
    ids, parent = sorted(prints), {}
    for snapshot_id in ids:
        parent[snapshot_id] = snapshot_id

    def root(snapshot_id: str) -> str:
        while parent[snapshot_id] != snapshot_id:
            snapshot_id = parent[snapshot_id]
        return snapshot_id

    for index, left in enumerate(ids):
        for right in ids[index + 1:]:
            if hamming(prints[left], prints[right]) <= THRESHOLD:
                parent[root(right)] = root(left)
    found: dict[str, list[str]] = {}
    for snapshot_id in ids:
        found.setdefault(root(snapshot_id), []).append(snapshot_id)
    return sorted(found.values())


def find(snapshots, snapshot_id: str) -> Snapshot:
    for snapshot in snapshots:
        if snapshot.snapshot_id == snapshot_id:
            return snapshot
    raise ValueError(f"no snapshot {snapshot_id} for this seed")
