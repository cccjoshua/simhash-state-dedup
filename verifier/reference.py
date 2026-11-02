"""group_snapshots, the reference: every snapshot's lines, fingerprint and the grouping."""

from .checks import THRESHOLD, grouping, id_problem, result, seed_problem, simhash


def verify_input(value):
    problem = seed_problem(value.seed)
    return result(problem is None, problem or "input is valid")


def verify_output(input_value, output_value, workspace):
    if output_value.threshold != THRESHOLD:
        return result(False, f"the threshold is {THRESHOLD}")
    ids = [snapshot.snapshot_id for snapshot in output_value.snapshots]
    if not ids or ids != sorted(set(ids)) or any(id_problem(snapshot_id) for snapshot_id in ids):
        return result(False, "snapshots are distinct, sorted by id and well formed")
    for snapshot in output_value.snapshots:
        if snapshot.fingerprint != f"{simhash(snapshot.lines):016x}":
            return result(False, f"{snapshot.snapshot_id}'s fingerprint is not the SimHash of its lines")
    if {frozenset(group) for group in output_value.groups} != grouping(output_value.snapshots):
        return result(False, "the groups are not the snapshots' components at the threshold")
    return result(True, "reference is consistent", snapshots=len(ids), groups=len(output_value.groups))
