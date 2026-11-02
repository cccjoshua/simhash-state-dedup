"""group-page-states: the agent's groups, compared with the components recomputed from the snapshots.

Valid only when the groups are exactly the components of 'Hamming distance at most the threshold' on
SimHashes the verifier computes itself: every snapshot in exactly one group, no unknown id. The order
of groups and of ids within them does not matter. The score is the Rand index, the share of snapshot
pairs both groupings put together or apart alike.
"""

from .checks import grouping, id_problem, pair_agreement, result


def verify_task(arguments, output, reference, workspace):
    """``output``: a contract GroupsOutput; ``reference``: the group_snapshots ReferenceOutput of the same seed."""
    if reference is None:
        return result(False, "no reference snapshots: the groups cannot be checked")
    ids = sorted(snapshot.snapshot_id for snapshot in reference.snapshots)
    listed = [snapshot_id for group in output.groups for snapshot_id in group]
    for snapshot_id in listed:
        problem = id_problem(snapshot_id)
        if problem:
            return result(False, problem)
    if any(not group for group in output.groups):
        return result(False, "a group is empty")
    unknown = sorted(set(listed) - set(ids))
    if unknown:
        return result(False, f"there is no snapshot {', '.join(unknown)}", unknown=unknown)
    repeated = sorted({snapshot_id for snapshot_id in listed if listed.count(snapshot_id) > 1})
    if repeated:
        return result(False, f"snapshots in more than one place: {', '.join(repeated)}", repeated=repeated)
    missing = sorted(set(ids) - set(listed))
    if missing:
        return result(False, f"snapshots in no group: {', '.join(missing)}", missing=missing)
    given = {frozenset(group) for group in output.groups}
    expected = grouping(reference.snapshots, reference.threshold)
    if given != expected:
        score = pair_agreement(given, expected, ids)
        merged = [sorted(group) for group in given if not any(group <= truth for truth in expected)]
        split = [sorted(truth) for truth in expected if not any(truth <= group for group in given)]
        return result(False, f"{len(merged)} group(s) join different states, {len(split)} state(s) are split",
                      score=score, merged=sorted(merged), split=sorted(split))
    return result(True, f"{len(expected)} page states from {len(ids)} snapshots", states=len(expected))
