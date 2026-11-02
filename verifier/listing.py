"""list_snapshots: the snapshot ids and the threshold."""

from .checks import THRESHOLD, id_problem, result, seed_problem


def verify_input(value):
    problem = seed_problem(value.seed)
    return result(problem is None, problem or "input is valid")


def verify_output(input_value, output_value, workspace):
    if output_value.seed != input_value.seed:
        return result(False, "the listing is for another seed")
    ids = output_value.snapshot_ids
    if not ids or ids != sorted(set(ids)) or any(id_problem(snapshot_id) for snapshot_id in ids):
        return result(False, "snapshot ids are distinct, sorted, well formed and not empty")
    if output_value.threshold != THRESHOLD:
        return result(False, f"the threshold is {THRESHOLD}")
    return result(True, f"{len(ids)} snapshots")
