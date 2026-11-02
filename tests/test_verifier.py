from __future__ import annotations

from functools import cache
from pathlib import Path

import pytest
from slimconfig import build_output, plain_output
from test_pages import groups_by_tools

import verifier
from contract import TASKS, TOOLS, DistancesInput, ReferenceOutput, SeedInput, SnapshotInput, Task, Tool
from plugin import distances, fingerprint, group_snapshots, list_snapshots, view_snapshot
from plugin.pages import simhash

TASK = "group-page-states"
SEEDS = range(60)


@cache
def reference(seed: int) -> ReferenceOutput:
    return group_snapshots(SeedInput(seed=seed), None)


@cache
def truth(seed: int) -> list[list[str]]:
    return [list(group) for group in groups_by_tools(seed)]


# The verifier gets contract instances, as NanoAgent's sandbox builds them from JSON.
def verify_task(seed: int, groups: list[list[str]], pinned: ReferenceOutput | None, workspace: Path) -> dict:
    given, made = TASKS[Task(TASK)]
    built = None if pinned is None else build_output(plain_output(pinned), ReferenceOutput)
    return verifier.verify_task(TASK, build_output({"seed": seed}, given), build_output({"groups": groups}, made),
                                built, str(workspace))


def verify_input(tool: str, value: dict) -> dict:
    return verifier.verify_input(tool, build_output(value, TOOLS[Tool(tool)][0]))


def verify_output(tool: str, given: dict, made: dict) -> dict:
    given_class, made_class = TOOLS[Tool(tool)]
    return verifier.verify_output(tool, build_output(given, given_class), build_output(made, made_class), "")


def seed_with(predicate) -> int:
    return next(seed for seed in range(60) if predicate(truth(seed)))


# Correct


@pytest.mark.parametrize("seed", SEEDS)
def test_approves_the_true_groups_in_any_order(seed: int, tmp_path: Path) -> None:
    groups = truth(seed)
    assert verify_task(seed, groups, reference(seed), tmp_path)["valid"] is True
    shuffled = [group[::-1] for group in groups[::-1]]
    verdict = verify_task(seed, shuffled, reference(seed), tmp_path)
    assert verdict["valid"] is True and verdict["score"] == 1.0


# Incorrect


def test_refuses_merged_states(tmp_path: Path) -> None:
    seed = seed_with(lambda groups: len(groups) >= 2)
    groups = truth(seed)
    merged = [groups[0] + groups[1]] + groups[2:]
    verdict = verify_task(seed, merged, reference(seed), tmp_path)
    assert verdict["valid"] is False and "1 group(s) join different states" in verdict["message"]
    assert 0 < verdict["score"] < 1


def test_refuses_a_split_state(tmp_path: Path) -> None:
    seed = seed_with(lambda groups: any(len(group) >= 2 for group in groups))
    groups = truth(seed)
    index = next(index for index, group in enumerate(groups) if len(group) >= 2)
    split = groups[:index] + [groups[index][:1], groups[index][1:]] + groups[index + 1:]
    verdict = verify_task(seed, split, reference(seed), tmp_path)
    assert verdict["valid"] is False and "1 state(s) are split" in verdict["message"]


def test_refuses_one_group_per_snapshot_or_one_group_for_all(tmp_path: Path) -> None:
    seed = seed_with(lambda groups: any(len(group) >= 2 for group in groups) and len(groups) >= 2)
    ids = sorted(snapshot_id for group in truth(seed) for snapshot_id in group)
    assert verify_task(seed, [[snapshot_id] for snapshot_id in ids], reference(seed), tmp_path)["valid"] is False
    assert verify_task(seed, [ids], reference(seed), tmp_path)["valid"] is False


def test_refuses_another_seeds_groups(tmp_path: Path) -> None:
    other = next(seed for seed in range(1, 40) if truth(seed) != truth(0))
    assert verify_task(0, truth(other), reference(0), tmp_path)["valid"] is False


# Missing


def test_refuses_a_missing_snapshot_or_reference(tmp_path: Path) -> None:
    groups = truth(7)
    dropped = [group[1:] if len(group) > 1 else group for group in groups]
    dropped = [group for group in dropped if group]
    verdict = verify_task(7, dropped, reference(7), tmp_path)
    assert verdict["valid"] is False and "in no group" in verdict["message"]
    assert verify_task(7, [], reference(7), tmp_path)["valid"] is False
    verdict = verify_task(7, groups, None, tmp_path)
    assert verdict["valid"] is False and "no reference" in verdict["message"]


# Malformed


def test_refuses_repeated_unknown_empty_or_misnamed_snapshots(tmp_path: Path) -> None:
    groups = truth(7)
    assert "more than one place" in verify_task(7, groups + [groups[0][:1]], reference(7), tmp_path)["message"]
    assert "no snapshot s99" in verify_task(7, groups + [["s99"]], reference(7), tmp_path)["message"]
    assert "empty" in verify_task(7, groups + [[]], reference(7), tmp_path)["message"]
    assert "not a snapshot id" in verify_task(7, groups + [["snap1"]], reference(7), tmp_path)["message"]


@pytest.mark.parametrize("output", [{}, {"groups": ["s00", "s01"]}, {"groups": "s00 s01"}, {"groups": [[0, 1]]}])
def test_the_contract_refuses_a_malformed_answer(output: dict) -> None:
    with pytest.raises(Exception):  # noqa: B017 - slimconfig's error type is its own
        build_output(output, TASKS[Task(TASK)][1])


def test_refuses_malformed_tool_input() -> None:
    assert verify_input("distances", {"seed": 7, "snapshot_ids": ["s03", "s04"]})["valid"] is True
    assert verify_input("distances", {"seed": 7, "snapshot_ids": ["3"]})["valid"] is False
    assert verify_input("distances", {"seed": 7, "snapshot_ids": []})["valid"] is False
    assert verify_input("distances", {"seed": 7, "snapshot_ids": ["s03", "s03"]})["valid"] is False
    assert verify_input("distances", {"seed": 7, "snapshot_ids": [f"s{n:02d}" for n in range(26)]})["valid"] is False
    assert verify_input("fingerprint", {"seed": 7, "snapshot_id": "3"})["valid"] is False
    assert verify_input("list_snapshots", {"seed": -5})["valid"] is False
    assert verify_input("group_snapshots", {"seed": 1_000_001})["valid"] is False


# Boundary


def test_a_state_captured_once_is_a_group_of_its_own(tmp_path: Path) -> None:
    seed = seed_with(lambda groups: any(len(group) == 1 for group in groups))
    groups = truth(seed)
    assert any(len(group) == 1 for group in groups)
    assert verify_task(seed, groups, reference(seed), tmp_path)["valid"] is True


def test_the_threshold_is_inclusive(tmp_path: Path) -> None:
    found = plain_output(reference(7))
    base = found["snapshots"][0]["lines"]
    # noise lines that move the fingerprint exactly to the threshold
    twins = (base + [f"session token-{extra:08x}-{line}" for line in range(count)]
             for extra in range(2000) for count in (2, 3, 4, 5))
    at = next(lines for lines in twins if (simhash(lines) ^ simhash(base)).bit_count() == found["threshold"])
    found["snapshots"] = [
        {"snapshot_id": "s00", "lines": base, "fingerprint": f"{simhash(base):016x}"},
        {"snapshot_id": "s01", "lines": at, "fingerprint": f"{simhash(at):016x}"},
    ]
    found["groups"] = [["s00", "s01"]]
    assert verify_output("group_snapshots", {"seed": 7}, found)["valid"] is True
    pinned = build_output(found, ReferenceOutput)
    assert verify_task(7, [["s00", "s01"]], pinned, tmp_path)["valid"] is True
    assert verify_task(7, [["s00"], ["s01"]], pinned, tmp_path)["valid"] is False


# Each tool's own checks


def test_tool_outputs_pass_their_checks_and_tampered_ones_do_not() -> None:
    listing = plain_output(list_snapshots(SeedInput(seed=7), None))
    assert verify_output("list_snapshots", {"seed": 7}, listing)["valid"] is True
    assert verify_output("list_snapshots", {"seed": 7}, listing | {"threshold": 3})["valid"] is False

    given = {"seed": 7, "snapshot_id": "s01"}
    viewed = plain_output(view_snapshot(SnapshotInput(**given), None))
    assert verify_output("view_snapshot", given, viewed)["valid"] is True
    assert verify_output("view_snapshot", given, viewed | {"lines": []})["valid"] is False

    printed = plain_output(fingerprint(SnapshotInput(**given), None))
    assert verify_output("fingerprint", given, printed)["valid"] is True
    assert verify_output("fingerprint", given, printed | {"fingerprint": "XYZ"})["valid"] is False

    asked = {"seed": 7, "snapshot_ids": ["s01", "s02"]}
    found = plain_output(distances(DistancesInput(**asked), None))
    assert verify_output("distances", asked, found)["valid"] is True
    first = found["rows"][0]
    selfish = {"rows": [first | {"distances": first["distances"] + [{"snapshot_id": "s01", "distance": 0}]},
                        found["rows"][1]]}
    assert verify_output("distances", asked, selfish)["valid"] is False
    assert verify_output("distances", asked, {"rows": found["rows"][::-1]})["valid"] is False

    full = plain_output(reference(7))
    assert verify_output("group_snapshots", {"seed": 7}, full)["valid"] is True
    tampered = full | {"groups": [[snapshot["snapshot_id"]] for snapshot in full["snapshots"]]}
    assert verify_output("group_snapshots", {"seed": 7}, tampered)["valid"] is False
    full["snapshots"][0]["fingerprint"] = "0" * 16
    assert verify_output("group_snapshots", {"seed": 7}, full)["valid"] is False


def test_the_verdict_is_the_same_every_time(tmp_path: Path) -> None:
    groups = truth(11)
    wrong = [groups[0] + groups[1]] + groups[2:]
    verdicts = [verify_task(11, wrong, reference(11), tmp_path) for _ in range(3)]
    assert verdicts[0] == verdicts[1] == verdicts[2]
