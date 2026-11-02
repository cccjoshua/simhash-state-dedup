"""The deterministic verifier: each tool's checks live in its own module, on contract instances."""

from contract import Task, Tool

from . import groups, listing, reference, snapshot

# tool -> (its input check, its output check)
TOOLS = {
    Tool.LIST_SNAPSHOTS: (listing.verify_input, listing.verify_output),
    Tool.VIEW_SNAPSHOT: (snapshot.verify_input, snapshot.verify_view),
    Tool.FINGERPRINT: (snapshot.verify_input, snapshot.verify_fingerprint),
    Tool.DISTANCES: (snapshot.verify_distances_input, snapshot.verify_distances),
    Tool.GROUP_SNAPSHOTS: (reference.verify_input, reference.verify_output),
}
# task -> its output's check, verify_task(arguments, output, reference, workspace)
TASKS = {Task.GROUP_PAGE_STATES: groups.verify_task}


def verify_input(tool, value):
    return TOOLS[Tool(tool)][0](value)


def verify_output(tool, input_value, output_value, workspace):
    return TOOLS[Tool(tool)][1](input_value, output_value, workspace)


def verify_task(task, arguments, output, reference, workspace):
    return TASKS[Task(task)](arguments, output, reference, workspace)
