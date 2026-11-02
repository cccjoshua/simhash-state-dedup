# SimHash Page-State Deduplicator

A `nanoagent.plugin/v0001` plugin. An agent groups page snapshots that differ only in ads, clocks and
session ids into page states, using SimHash fingerprints and Hamming distances. A deterministic
verifier recomputes every fingerprint and the grouping itself and checks the answer.

Each set of snapshots is built from an integer seed alone (SHA-256 of the seed and a counter): 4 to 6
page states of 30 to 37 accessibility-tree lines, each captured 1 to 4 times with one or two noise
lines. The SimHash is over a snapshot's whitespace-separated tokens, each weighted 1, with the first 8
bytes of its SHA-256 as its 64-bit hash. Captures of one state are within the threshold (6) of each
other and captures of different states farther apart; a draw that breaks this is drawn again. No
network is used.

## Tools

| Tool | Does | Code |
|---|---|---|
| `list_snapshots` | Lists the snapshot ids and the threshold | `src/plugin/tools.py` |
| `view_snapshot` | Shows one snapshot's lines | `src/plugin/tools.py` |
| `fingerprint` | Gives one snapshot's 64-bit SimHash | `src/plugin/tools.py` |
| `distances` | Gives the Hamming distance from each of up to 25 snapshots to every other | `src/plugin/tools.py` |
| `group_snapshots` | Every snapshot and the true grouping: the task's reference, never shown to the agent | `src/plugin/tools.py` |

The snapshots themselves are built in `src/plugin/pages.py`.

### Tasks

| Task | Does | Runner |
|---|---|---|
| `group-page-states` | Group the snapshots into page states | `agent`, with `list_snapshots`, `view_snapshot`, `fingerprint` and `distances`; reference `group_snapshots` |

The verifier (`verifier/groups.py`) recomputes each snapshot's SimHash from its lines, links snapshots
within the threshold and takes the connected components. The answer is valid only when its groups
are exactly those components, every snapshot in one group. Its score is the Rand index.

## Layout

```text
.
├── nanoagent.yaml   # manifest: id, runtime, permissions, tools, tasks
├── contract.py      # each tool's and task's typed input and output
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable NAMEs this plugin needs (none)
├── src/plugin/      # the MCP server, the snapshot generator and the tools
├── tests/           # tests of the snapshots, the tools and the verifier
├── ui/              # outputs are drawn from their JSON Schema
├── product/         # the product page: product.yaml and icon.svg
└── verifier/        # deterministic verifier package
```

## Develop and run

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```

Publishing checks every plugin rule: push the plugin to a public GitHub repository and submit its
URL on RUSH Lab.
