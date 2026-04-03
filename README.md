---
title: CodeFixEnv
emoji: "🤖"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# CodeFixEnv

An OpenEnv-compliant reinforcement learning environment for evaluating AI agents on **iterative Python code debugging**.

Agents receive buggy Python code and must choose repair actions to make the code pass a deterministic grader. The environment provides partial-progress reward signals so agents can learn incrementally rather than relying on sparse binary feedback.

---

## Motivation

Code debugging is a genuine task that developers perform daily. Unlike toy environments, CodeFixEnv models a realistic workflow: read code, identify the bug category, apply a targeted fix, and verify correctness. This makes it directly useful for evaluating and training LLM-based coding agents.

---

## Action Space

Actions are text strings. The environment supports:

| Action | Description |
|---|---|
| `fix_syntax` | Auto-fix common syntax errors (missing colons, unclosed parens) |
| `fix_logic` | Auto-fix common logic errors (subtraction → addition) |
| `noop` | Do nothing |
| `replace_line:<n>:<code>` | Replace line `n` with `<code>` |
| `append_line:<code>` | Append a new line of code |
| `delete_line:<n>` | Delete line `n` |
| `replace_text:<old>:<new>` | Find-and-replace text in the code |

**Typed model:** `CodeFixAction(action="fix_syntax")`

---

## Observation Space

Each observation contains:

| Field | Type | Description |
|---|---|---|
| `task` | `str` | Current task name |
| `code` | `str` | Current state of the code |
| `error` | `str` | Current error message (empty if none) |
| `step_count` | `int` | Steps taken so far |
| `history` | `List[str]` | List of actions taken |
| `score` | `float` | Current grader score (0.0–1.0) |
| `done` | `bool` | Whether the episode has ended |
| `reward` | `float` | Reward from the last action |

---

## Tasks

Five tasks with genuine difficulty progression:

| Task | Bug Type | Description | Max Steps |
|---|---|---|---|
| **easy** | Syntax | Missing closing quote and parenthesis in `print` | 4 |
| **medium** | Logic | `add()` function uses subtraction instead of addition | 5 |
| **hard** | Syntax + Logic | Missing colon on `if` + wrong operator in both branches | 6 |
| **expert** | Logic + Edge cases | Subtraction instead of addition with boundary clamping | 7 |
| **nightmare** | Syntax + Multi-branch logic | Missing colon + subtraction in multiple branches | 8 |

---

## Reward Function

The reward provides **partial-progress signal** (not binary):

- **Syntax pass baseline:** 0.3 (code compiles but may fail tests)
- **Test case ratio:** remaining 0.7 × (passed / total test cases)
- **Efficiency bonus:** +0.05 for fixes that change ≤ 2 lines
- **Penalties:** –0.02 for no change, –0.08 for invalid action, –0.12 for regression
- **Floor:** rewards clamped at –0.5

---

## Grader

Each task has deterministic test cases. The grader:
1. Checks syntax (fail → score 0.0)
2. Executes code in a sandboxed environment with line-count limits
3. Runs function-level test cases (`call`, `call_approx`, `contains`, `not_contains`)
4. Includes **anti-cheat detection** for hardcoded test-case mappings

---

## Setup

### Prerequisites

- Python 3.12+
- Docker (for containerized deployment)

### Local Development

```bash
# Clone and install
git clone <repo-url>
cd codefix-env
python -m venv .venv
.venv/Scripts/activate   # Windows
pip install -r requirements.txt

# Run server
uvicorn app:app --host 127.0.0.1 --port 7860

# Run tests
python -m pytest -q

# Run benchmark
python benchmark.py

# Run inference (deterministic policy, no LLM needed)
set API_BASE_URL=http://127.0.0.1:7860
python inference.py
```

### Docker

```bash
docker build -t codefix-env .
docker run --rm -p 7860:7860 codefix-env
```

---

## API Endpoints

OpenEnv auto-registers:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/reset` | Start a new episode |
| `POST` | `/step` | Execute an action |
| `GET` | `/state` | Get current environment state |
| `GET` | `/health` | Health check |
| `GET` | `/schema` | JSON schemas for action and observation |
| `WS` | `/ws` | WebSocket for persistent sessions |

### Example: Reset

```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "easy"}'
```

Response:
```json
{
  "observation": {
    "task": "easy",
    "code": "print(\"Hello",
    "error": "SyntaxError: ...",
    "step_count": 0,
    "history": [],
    "score": 0.0
  },
  "reward": 0.0,
  "done": false
}
```

### Example: Step

```bash
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"action": "fix_syntax"}}'
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `API_BASE_URL` | `http://localhost:7860` | Environment server URL |
| `MODEL_NAME` | `demo-rule-agent` | LLM model identifier |
| `OPENAI_API_KEY` | — | API key for LLM calls |
| `HF_TOKEN` | — | Hugging Face token |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | LLM endpoint |
| `TASKS` | `easy,medium,hard` | Comma-separated task list |
| `MAX_STEPS` | `8` | Max steps per episode |

---

## Baseline Scores

Deterministic rule-based policy (no LLM):

| Task | Score | Steps | Solved |
|---|---|---|---|
| easy | 1.000 | 1/4 | ✅ |
| medium | 1.000 | 1/5 | ✅ |
| hard | 1.000 | 2/6 | ✅ |
| expert | 1.000 | 1/7 | ✅ |
| nightmare | 1.000 | 2/8 | ✅ |

---

## Project Structure

```
codefix-env/
├── app.py                  # OpenEnv FastAPI server
├── models.py               # Typed Action/Observation/State models
├── openenv.yaml            # OpenEnv manifest
├── inference.py            # Baseline inference script
├── benchmark.py            # Local benchmark runner
├── Dockerfile              # Container definition
├── requirements.txt        # Dependencies
├── settings.py             # Configuration
├── env/
│   ├── environment.py      # CodeFixEnvironment (extends Environment)
│   ├── actions.py          # Action parsing
│   ├── logic.py            # Code transformation logic
│   ├── reward.py           # Reward computation
│   └── state.py            # Internal state dataclass
├── tasks/
│   ├── easy.py             # Easy task
│   ├── medium.py           # Medium task
│   ├── hard.py             # Hard task
│   ├── expert.py           # Expert task
│   ├── nightmare.py        # Nightmare task
│   └── task_loader.py      # Task registry
├── graders/
│   ├── grader.py           # Grading logic + anti-cheat
│   └── testcases.py        # Deterministic test cases
├── utils/
│   ├── code_executor.py    # Sandboxed code execution
│   ├── diff_utils.py       # Diff utilities
│   └── logger.py           # Logging
└── tests/
    ├── test_env.py
    ├── test_actions_and_reward.py
    ├── test_grader_anticheat.py
    └── test_benchmark.py
```
