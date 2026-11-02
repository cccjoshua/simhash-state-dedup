"""view_snapshot, fingerprint and distances: one snapshot's lines, SimHash and distances."""

from .checks import FINGERPRINT, MAX_SNAPSHOTS, id_problem, result, seed_problem


def verify_input(value):
    problem = seed_problem(value.seed) or id_problem(value.snapshot_id)
    return result(problem is None, problem or "input is valid")


def verify_view(input_value, output_value, workspace):
    if output_value.snapshot_id != input_value.snapshot_id:
        return result(False, "the lines are for another snapshot")
    if not output_value.lines or any(not line.strip() for line in output_value.lines):
        return result(False, "a snapshot has lines, none blank")
    return result(True, f"{len(output_value.lines)} lines")


def verify_fingerprint(input_value, output_value, workspace):
    if output_value.snapshot_id != input_value.snapshot_id:
        return result(False, "the fingerprint is for another snapshot")
    if not FINGERPRINT.fullmatch(output_value.fingerprint):
        return result(False, "a fingerprint is 16 lowercase hex digits")
    return result(True, output_value.fingerprint)


def verify_distances_input(value):
    problem = seed_problem(value.seed)
    if problem is None and not 1 <= len(value.snapshot_ids) <= MAX_SNAPSHOTS:
        problem = f"give 1 to {MAX_SNAPSHOTS} snapshot ids"
    if problem is None and len(set(value.snapshot_ids)) != len(value.snapshot_ids):
        problem = "a snapshot id is given twice"
    for snapshot_id in value.snapshot_ids:
        problem = problem or id_problem(snapshot_id)
    return result(problem is None, problem or "input is valid")


def verify_distances(input_value, output_value, workspace):
    if [row.snapshot_id for row in output_value.rows] != input_value.snapshot_ids:
        return result(False, "the rows are not for the snapshots given, in order")
    others = None
    for row in output_value.rows:
        ids = [found.snapshot_id for found in row.distances]
        if ids != sorted(set(ids)) or row.snapshot_id in ids or any(id_problem(other) for other in ids):
            return result(False, f"{row.snapshot_id}: one distance per other snapshot, by id")
        if any(not 0 <= found.distance <= 64 for found in row.distances):
            return result(False, f"{row.snapshot_id}: a distance is between 0 and 64")
        every = sorted(ids + [row.snapshot_id])
        if others is not None and every != others:
            return result(False, "every row measures against the same snapshots")
        others = every
    return result(True, f"{len(output_value.rows)} rows")
