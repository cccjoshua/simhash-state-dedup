"""The plugin's tools: each takes its contract input and the workspace, and reads the seed's snapshots."""

from __future__ import annotations

from pathlib import Path

from contract import (
    Distance,
    DistanceRow,
    DistancesInput,
    DistancesOutput,
    FingerprintOutput,
    ReferenceOutput,
    SeedInput,
    Snapshot,
    SnapshotInput,
    SnapshotsOutput,
    ViewOutput,
)
from plugin.pages import MAX_SNAPSHOTS, THRESHOLD, build_snapshots, find, groups, hamming, simhash


def _hex(value: int) -> str:
    return f"{value:016x}"


def list_snapshots(given: SeedInput, workspace: Path) -> SnapshotsOutput:
    snapshots = build_snapshots(given.seed)
    ids = sorted(snapshot.snapshot_id for snapshot in snapshots)
    return SnapshotsOutput(seed=given.seed, snapshot_ids=ids, threshold=THRESHOLD)


def view_snapshot(given: SnapshotInput, workspace: Path) -> ViewOutput:
    snapshot = find(build_snapshots(given.seed), given.snapshot_id)
    return ViewOutput(snapshot_id=snapshot.snapshot_id, lines=list(snapshot.lines))


def fingerprint(given: SnapshotInput, workspace: Path) -> FingerprintOutput:
    snapshot = find(build_snapshots(given.seed), given.snapshot_id)
    return FingerprintOutput(snapshot_id=snapshot.snapshot_id, fingerprint=_hex(simhash(snapshot.lines)))


def distances(given: DistancesInput, workspace: Path) -> DistancesOutput:
    ids = given.snapshot_ids
    if not 1 <= len(ids) <= MAX_SNAPSHOTS or len(set(ids)) != len(ids):
        raise ValueError(f"give 1 to {MAX_SNAPSHOTS} distinct snapshot ids")
    snapshots = build_snapshots(given.seed)
    rows = []
    for snapshot_id in ids:
        own = simhash(find(snapshots, snapshot_id).lines)
        others = sorted((item for item in snapshots if item.snapshot_id != snapshot_id), key=lambda item: item.snapshot_id)
        rows.append(DistanceRow(
            snapshot_id=snapshot_id,
            distances=[Distance(snapshot_id=other.snapshot_id, distance=hamming(own, simhash(other.lines)))
                       for other in others],
        ))
    return DistancesOutput(rows=rows)


def group_snapshots(given: SeedInput, workspace: Path) -> ReferenceOutput:
    """The reference: every snapshot and the grouping, run out of the agent's sight."""
    snapshots = sorted(build_snapshots(given.seed), key=lambda snapshot: snapshot.snapshot_id)
    return ReferenceOutput(
        threshold=THRESHOLD,
        snapshots=[Snapshot(snapshot_id=item.snapshot_id, lines=list(item.lines), fingerprint=_hex(simhash(item.lines)))
                   for item in snapshots],
        groups=groups(snapshots),
    )
