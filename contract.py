"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    LIST_SNAPSHOTS = "list_snapshots"
    VIEW_SNAPSHOT = "view_snapshot"
    FINGERPRINT = "fingerprint"
    DISTANCES = "distances"
    GROUP_SNAPSHOTS = "group_snapshots"


class Task(Enum):
    GROUP_PAGE_STATES = "group-page-states"


SEED = "The snapshots' seed, 0 to 1000000: the same seed always builds the same snapshots"
SNAPSHOT_ID = "A snapshot id, s followed by two digits, e.g. s04"
FINGERPRINT = "A 64-bit SimHash as 16 lowercase hex digits"


@dataclass
class SeedInput(Output):
    seed: Annotated[int, SEED]


@dataclass
class SnapshotsOutput(Output):
    seed: Annotated[int, SEED]
    snapshot_ids: Annotated[list[str], "Every snapshot's id, sorted"]
    threshold: Annotated[int, "Two snapshots show the same page state when their Hamming distance is at most this"]


@dataclass
class SnapshotInput(Output):
    seed: Annotated[int, SEED]
    snapshot_id: Annotated[str, SNAPSHOT_ID]


@dataclass
class ViewOutput(Output):
    snapshot_id: Annotated[str, SNAPSHOT_ID]
    lines: Annotated[list[str], "The snapshot's accessibility-tree lines, ads, clocks and sessions included"]


@dataclass
class FingerprintOutput(Output):
    snapshot_id: Annotated[str, SNAPSHOT_ID]
    fingerprint: Annotated[str, FINGERPRINT]


@dataclass
class Distance(Output):
    snapshot_id: Annotated[str, "The other snapshot"]
    distance: Annotated[int, "The Hamming distance between the two fingerprints, 0 to 64"]


@dataclass
class DistancesInput(Output):
    seed: Annotated[int, SEED]
    snapshot_ids: Annotated[list[str], "The snapshots to measure from, 1 to 25 distinct snapshot ids"]


@dataclass
class DistanceRow(Output):
    snapshot_id: Annotated[str, SNAPSHOT_ID]
    distances: Annotated[list[Distance], "The distance to every other snapshot, by snapshot id"]


@dataclass
class DistancesOutput(Output):
    rows: Annotated[list[DistanceRow], "One row per snapshot asked for, in the order given"]


@dataclass
class Snapshot(Output):
    snapshot_id: Annotated[str, SNAPSHOT_ID]
    lines: Annotated[list[str], "The snapshot's lines"]
    fingerprint: Annotated[str, FINGERPRINT]


@dataclass
class ReferenceOutput(Output):
    threshold: Annotated[int, "The same-state distance threshold"]
    snapshots: Annotated[list[Snapshot], "Every snapshot, sorted by id"]
    groups: Annotated[list[list[str]], "The page states: each a sorted group of snapshot ids, groups sorted"]


@dataclass
class GroupsOutput(Output):
    groups: Annotated[
        list[list[str]],
        "The page states: groups of snapshot ids, linked when their distance is at most the threshold;"
        " every snapshot in exactly one group",
    ]


TOOLS = {
    Tool.LIST_SNAPSHOTS: (SeedInput, SnapshotsOutput),
    Tool.VIEW_SNAPSHOT: (SnapshotInput, ViewOutput),
    Tool.FINGERPRINT: (SnapshotInput, FingerprintOutput),
    Tool.DISTANCES: (DistancesInput, DistancesOutput),
    Tool.GROUP_SNAPSHOTS: (SeedInput, ReferenceOutput),
}
TASKS = {
    Task.GROUP_PAGE_STATES: (SeedInput, GroupsOutput),
}
