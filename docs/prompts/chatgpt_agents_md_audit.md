# ChatGPT prompt — AGENTS.md audit or bootstrap

Copy everything inside the fenced block below into your ChatGPT personal assistant. Replace the placeholders before sending.

---

```
You are my repository analyst and technical writer. Your job is to ensure the repo has a correct, agent-ready AGENTS.md at the repository root.

## Target repository

- **Repo URL or local path:** [PASTE_GITHUB_URL_OR_PATH_HERE]
- **Primary branch:** [main | master | other]
- **Optional context:** [e.g. "Python Streamlit app on Apple M4 Mac, 16 GB RAM" or leave blank]

## Task (strict order)

### Step 1 — Locate AGENTS.md

1. Search the repository root for a file named exactly **`AGENTS.md`** (plural).
2. Also check for legacy names: `AGENT.md`, `.github/copilot-instructions.md`, `.cursorrules` — note them but do **not** treat them as substitutes.
3. In monorepos, note any nested `AGENTS.md` files under subdirectories.

Report what you found (path, size, last modified if available).

### Step 2 — Branch on result

**IF `AGENTS.md` does NOT exist at the repo root:**

- Analyze the repo structure (README, pyproject/package manifests, Makefile, CI workflows, main entrypoints, docs/).
- **Create** a new `AGENTS.md` at the repository root.
- Keep it **under ~150 lines** — concise, imperative, copy-pasteable commands.
- Do **not** duplicate the full README; focus on what AI coding agents need to work safely.

**IF `AGENTS.md` EXISTS:**

- **Audit** it against the checklist below.
- Produce a scored review (Pass / Partial / Fail per section).
- List concrete gaps, stale commands, wrong paths, or missing guardrails.
- Provide a **revised full file** only if changes are needed; otherwise say "no rewrite required" and list minor optional improvements.

### Step 3 — Deliverables

Always output in this order:

1. **Executive summary** (3–5 bullets)
2. **Findings table** (section → status → notes)
3. **Action taken:** `CREATED` | `AUDITED — OK` | `AUDITED — REWRITE RECOMMENDED`
4. **Full AGENTS.md content** (only when creating or rewriting)
5. **Optional follow-ups** (e.g. add `.cursor/rules/`, symlink `AGENT.md` → `AGENTS.md`)

---

## AGENTS.md quality checklist (audit against this)

### Required sections

| Section | What good looks like |
|---------|----------------------|
| **Project purpose** | One paragraph + data/architecture flow (if applicable) |
| **Setup & toolchain** | Exact package manager, runtime version, venv path |
| **Common commands** | Copy-paste blocks: install, run app, test, lint/build |
| **Repository map** | Table or list: key dirs → purpose |
| **Conventions & guardrails** | Imports, style, what NOT to do |
| **Validation / CI** | What runs on push; required artifacts or schema |
| **Workflow for agents** | Numbered steps: read → change → verify → commit policy |

### Content quality

- [ ] Commands are **verified against the repo** (Makefile, package.json, scripts/, CI) — not guessed
- [ ] Paths and filenames match the **actual tree**
- [ ] **Guardrails** are explicit (source of truth, read-only layers, secrets, scope boundaries)
- [ ] **Hardware/runtime constraints** stated if relevant (OS, RAM, GPU/MPS/CoreML, thread limits)
- [ ] Pinned or sensitive dependency versions called out when they matter
- [ ] Commit policy stated if the team expects "commit only when asked"
- [ ] Legacy/out-of-scope areas marked so agents don't touch them

### Anti-patterns (flag these)

- Duplicates entire README or long prose docs
- Vague commands ("run tests" without the exact command)
- Wrong tool (`pip` when repo uses `uv`, `npm` when repo uses `pnpm`, etc.)
- Missing "don'ts" (agents need explicit bans)
- Over 200 lines without strong reason
- References files or scripts that no longer exist
- CUDA/GPU assumptions on Apple Silicon-only projects

### Standard & compatibility

- File must be named **`AGENTS.md`** at repo root (Linux Foundation / agents.md convention)
- Plain Markdown, no required YAML frontmatter
- Suitable for Cursor, Copilot, Codex, and other agents that read AGENTS.md

---

## Analysis instructions

When inspecting the repo:

1. Read `README.md`, dependency manifests (`pyproject.toml`, `package.json`, `Cargo.toml`, etc.), `Makefile`, and `.github/workflows/*`.
2. Identify the **canonical data/ops flow** (e.g. source → ETL → read models → UI).
3. Find the **main entrypoint** and how to run it locally.
4. Find the **test command** and any CI validation gates.
5. Infer **agent-critical don'ts** from architecture (e.g. "dashboard is read-only", "don't edit generated artifacts directly").

If you cannot access the repo directly, ask me to paste: tree output (`find . -maxdepth 3 -type f | head -80`), README, and pyproject/package.json — then proceed.

## Output format for the AGENTS.md file

Use this skeleton when creating or rewriting:

```markdown
# AGENTS.md

[One-line purpose statement]

## What this project is
[Architecture / source of truth]

## Host environment (if relevant)
[OS, hardware, memory, GPU constraints]

## Setup & toolchain
[Package manager, versions, venv]

## Common commands
[bash blocks]

## Repository map
[table]

## Conventions & guardrails
[bullets, including don'ts]

## Validation gate (CI)
[what CI checks]

## Doing work here
[numbered workflow]
```

Be precise. Prefer `uv run pytest` over "run tests". Prefer `bash scripts/sync_excel.sh` over "sync data".

Begin now with Step 1 for: [PASTE_GITHUB_URL_OR_PATH_HERE]
```

---

## Example (fulofilo-analytics)

For this repo, paste:

```
Repo URL: https://github.com/AUTOGIO/fulofilo-analytics
Primary branch: main
Optional context: Python 3.12 + uv + Streamlit on iMac M4, 16 GB RAM. Excel master → sync → Parquet/DuckDB → dashboard.
```

Then run the prompt. The assistant should find existing `AGENTS.md` and audit it against the checklist.
