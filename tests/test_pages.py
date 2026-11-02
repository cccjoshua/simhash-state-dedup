from __future__ import annotations

import pytest

from contract import DistancesInput, SeedInput, SnapshotInput
from plugin import distances, fingerprint, group_snapshots, list_snapshots, view_snapshot
from plugin.pages import THRESHOLD, build_snapshots, groups, simhash


def groups_by_tools(seed: int) -> list[list[str]]:
    """What an agent submits after calling distances for every snapshot and joining the links."""
    listing = list_snapshots(SeedInput(seed=seed), None)
    group_of = {snapshot_id: {snapshot_id} for snapshot_id in listing.snapshot_ids}
    assert len(listing.snapshot_ids) <= 25  # one distances call
    for row in distances(DistancesInput(seed=seed, snapshot_ids=listing.snapshot_ids), None).rows:
        snapshot_id = row.snapshot_id
        for found in row.distances:
            if found.distance <= listing.threshold:
                joined = group_of[snapshot_id] | group_of[found.snapshot_id]
                for member in joined:
                    group_of[member] = joined
    return sorted({tuple(sorted(group)) for group in group_of.values()})


def test_a_seed_always_builds_the_same_snapshots() -> None:
    assert build_snapshots(42) == build_snapshots(42)
    assert build_snapshots(42) != build_snapshots(43)


@pytest.mark.parametrize("seed", range(200))
def test_groups_are_exactly_the_page_states(seed: int) -> None:
    snapshots = build_snapshots(seed)
    truth = sorted(sorted(item.snapshot_id for item in snapshots if item.state == state)
                   for state in {item.state for item in snapshots})
    assert groups(snapshots) == truth
    assert [list(group) for group in groups_by_tools(seed)] == truth
    assert group_snapshots(SeedInput(seed=seed), None).groups == truth


def test_noise_moves_the_fingerprint_but_not_past_the_threshold() -> None:
    snapshots = build_snapshots(7)
    state = next(item.state for item in snapshots if sum(other.state == item.state for other in snapshots) > 1)
    same = [item for item in snapshots if item.state == state]
    assert same[0].lines != same[1].lines
    assert (simhash(same[0].lines) ^ simhash(same[1].lines)).bit_count() <= THRESHOLD


def test_the_tools_agree_with_each_other() -> None:
    reference = group_snapshots(SeedInput(seed=7), None)
    for snapshot in reference.snapshots:
        given = SnapshotInput(seed=7, snapshot_id=snapshot.snapshot_id)
        assert view_snapshot(given, None).lines == snapshot.lines
        assert fingerprint(given, None).fingerprint == snapshot.fingerprint


def test_the_tools_refuse_unknown_snapshots() -> None:
    with pytest.raises(ValueError, match="no snapshot"):
        fingerprint(SnapshotInput(seed=7, snapshot_id="s99"), None)
    with pytest.raises(ValueError, match="no snapshot"):
        distances(DistancesInput(seed=7, snapshot_ids=["s99"]), None)
    with pytest.raises(ValueError, match="distinct"):
        distances(DistancesInput(seed=7, snapshot_ids=["s00", "s00"]), None)
    with pytest.raises(ValueError, match="seed"):
        list_snapshots(SeedInput(seed=-1), None)
