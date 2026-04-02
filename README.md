---
title: CodeFixEnv
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
app_file: app.py
pinned: false
---

# CodeFixEnv - Round 1 Execution Guide (Start to Submission)

## Purpose of This Document
This is the working guide to build, deploy, validate, and submit the Round 1 OpenEnv environment without missing mandatory requirements.

If followed, it is designed to maximize safety and scoring potential through:
- clean implementation
- deterministic behavior
- reproducible deployment
- explicit validation evidence

---

## 1. What We Are Building
We are building an API-based RL environment, not an agent product.

The environment allows external agents to interact through HTTP endpoints and iteratively fix buggy Python code.

Mandatory interaction surface:
- POST /reset
- POST /step

---

## 2. System Flow
1. Agent policy (inference.py) sends request.
2. API receives action.
3. Environment applies the action to current code state.
4. Grader computes score and reward.
5. API returns new state, reward, done flag.

Current implementation files:
- app.py
- env/environment.py
- graders/grader.py
- inference.py

---

## 3. Hackathon Requirements (Must Satisfy)
### Mandatory components
- API endpoints: /reset, /step
- Minimum 3 tasks
- Grader returning 0.0 to 1.0
- inference.py
- openenv.yaml
- Dockerfile
- Hugging Face deployment

### Disqualification triggers
- API not working
- Docker image does not build or run
- Space does not respond
- missing inference.py
- non-informative grader (constant score)

---

## 4. Project Structure (Final)

```text
codefix-env/
|-- app.py
|-- openenv.yaml
|-- settings.py
|-- inference.py
|-- Dockerfile
|-- requirements.txt
|-- README.md
|-- .env.example
|-- env/
|   |-- actions.py
|   |-- environment.py
|   |-- logic.py
|   |-- reward.py
|   |-- session_manager.py
|   |-- state.py
|-- tasks/
|   |-- easy.py
|   |-- medium.py
|   |-- hard.py
|   |-- task_loader.py
|-- graders/
|   |-- grader.py
|   |-- testcases.py
|-- models/
|   |-- request_models.py
|   |-- response_models.py
|-- utils/
|   |-- code_executor.py
|   |-- diff_utils.py
|   |-- logger.py
|-- tests/
|   |-- test_env.py
|   |-- test_actions_and_reward.py
```

---

## 5. Development Plan (Who Does What)
Member 1 (Core Logic)
- environment step/reset logic
- deterministic reward shaping

Member 2 (API and Infra)
- FastAPI surface
- session handling
- Docker and runtime hardening
- deployment readiness

Member 3 (Tasks and Grader)
- task authoring by difficulty
- deterministic grading testcases
- scoring signal quality

---

## 6. Environment Design Rules
State must include:
- code
- error
- step_count
- history

Actions must be:
- simple text
- deterministic
- LLM-friendly

Supported actions:
- fix_syntax
- fix_logic
- noop
- replace_line:<line_no>:<new_code>
- insert_line:<line_no>:<new_code>
- replace_range:<start_line>:<end_line>:<new_code>
- append_line:<new_code>
- delete_line:<line_no>
- replace_text:<old_text>:<new_text>
- rewrite_code:<new_code>

For multiline payloads in action strings, use escaped newlines like \n.

Reward must:
- support partial progress
- avoid binary-only signal
- remain deterministic

Episode ends when:
- code is correct
- or max steps reached

Current behavior:
- environment state is represented via env/state.py
- session-safe runtime provided by env/session_manager.py

---

## 7. Task Design Strategy
Required task tiers:
- easy: simple syntax bug
- medium: logic bug
- hard: multi-bug sequence
- expert: logic with edge-case clamps
- nightmare: syntax + branch logic traps

Rules:
- tasks are genuinely different
- difficulty progression is real
- deterministic grader path

Current tasks:
- tasks/easy.py
- tasks/medium.py
- tasks/hard.py
- tasks/expert.py
- tasks/nightmare.py

---

## 8. Grader Design Rules
Grader must:
- return score in [0.0, 1.0]
- be deterministic
- use explicit testcases

Current scoring approach:
- syntax fail: 0.0
- syntax pass baseline: 0.3
- testcase pass ratio contributes remaining 0.7
- reward shaping favors improvement and lightly penalizes invalid/no-change steps

Avoided anti-patterns:
- random scoring
- same score for all outcomes

Implemented in:
- graders/grader.py
- graders/testcases.py

---

## 9. API Design
### Required endpoints
- POST /reset
- POST /step
- GET /state/{session_id}

### Additional operational endpoints
- GET /health
- GET /ready
- DELETE /session/{session_id}

### Contract used in this repository
POST /reset input:
```json
{
  "task": "easy",
  "session_id": "optional"
}
```

POST /reset response:
```json
{
  "session_id": "uuid",
  "state": {
    "task": "easy",
    "code": "...",
    "error": "...",
    "step_count": 0,
    "history": [],
    "score": 0.0
  }
}
```

POST /step input:
```json
{
  "session_id": "uuid",
  "action": "fix_syntax"
}
```

POST /step response:
```json
{
  "session_id": "uuid",
  "state": {"...": "..."},
  "reward": 0.7,
  "done": false,
  "score": 0.65
}
```

Reliability rules:
- always return JSON
- deterministic behavior for same input trajectory
- session-aware flow for concurrent users

---

## 10. inference.py Requirements
Round 1 expectation:
- OpenAI-compatible client usage
- environment variables for endpoint/model/token
- deterministic and fast run behavior

Current implementation:
- uses OpenAI SDK when enabled and token is provided
- falls back to deterministic local policy if token is missing
- interacts with API via /reset and /step

Environment variables used:
- API_BASE_URL
- MODEL_NAME
- HF_TOKEN
- LLM_BASE_URL
- USE_LLM_POLICY
- TASK_NAME
- MAX_STEPS
- REQUEST_TIMEOUT
- MAX_LLM_RETRIES

---

## 11. Docker Requirements
Must:
- build successfully
- start API server
- expose port 7860

Current Docker runtime:
- base image: python:3.12-slim-bookworm
- non-root execution
- gunicorn + uvicorn worker
- healthcheck against /health
- apt upgrade during build

Build and run:
```bash
docker build -t codefix-env:local .
docker run --rm -p 7860:7860 --env-file .env.example codefix-env:local
```

---

## 12. Hugging Face Deployment
Steps:
1. Create new Space using Docker SDK.
2. Push repository.
3. Configure secrets/variables.
4. Deploy and verify health.

Recommended variables/secrets:
- HF_TOKEN (secret)
- MODEL_NAME
- API_BASE_URL (if needed by external runner)
- LLM_BASE_URL (if using compatible endpoint)

Post-deploy checks:
- GET /health responds
- POST /reset responds
- POST /step responds

---

## 13. Validation Process
Run these checks before submission:
1. Unit and API tests
2. Local end-to-end inference loop
3. Docker build and container run
4. OpenEnv validation command
5. Hosted Space endpoint checks

Official-style validator script is included at scripts/validate-submission.sh.

Recommended validator run:
```bash
chmod +x scripts/validate-submission.sh
./scripts/validate-submission.sh https://your-space.hf.space .
```

If openenv is missing locally:
```bash
pip install openenv-core
```

Example local commands:
```bash
python -m pytest -q
python -m uvicorn app:app --host 127.0.0.1 --port 7860
python inference.py
python benchmark.py
python predeploy_check.py
openenv validate
```

---

## 14. Performance Constraints
Design goals:
- complete validation under 20 minutes
- support low-resource environments
- avoid expensive runtime operations

Current implementation notes:
- small deterministic task payloads
- bounded execution checks in utils/code_executor.py
- lightweight API state transitions

---

## 15. Common Mistakes to Avoid
Technical:
- endpoint contract drift
- missing dependency in image
- server not listening on expected port

Design:
- weak or trivial tasks
- binary-only reward
- non-deterministic grader behavior

Strategy:
- over-optimizing the agent instead of environment quality
- skipping reproducibility checks

---

## 16. Winning Strategy Priorities
1. Grader quality
2. Task quality and progression
3. Reward shaping
4. API correctness and stability
5. Deployment reliability

---

## 17. Final Checklist
Before submission confirm:
- /reset works
- /step works
- three tasks exist
- grader returns 0.0 to 1.0
- inference.py executes
- Docker builds and serves
- HF Space responds

---

## 18. Current Completion Audit (April 1, 2026)
Status key:
- PASS: verified locally in this workspace
- BLOCKED-LOCAL: could not verify due missing local runtime tool, requires your machine/service setup

Checklist status:
- API endpoints /reset and /step: PASS
- minimum 3 tasks: PASS
- deterministic 0.0 to 1.0 grader: PASS
- inference.py present and running: PASS
- openenv.yaml present: PASS
- Dockerfile present and production oriented: PASS
- Docker build execution in this session: PASS
- openenv validate execution in this session: BLOCKED-LOCAL (openenv CLI unavailable)
- Hugging Face deployment responsiveness: BLOCKED-LOCAL (requires your Space)

Validation evidence collected in this workspace session:
- python -m pytest -q => 18 passed
- local uvicorn startup => success
- docker build => success
- docker run + /health + /ready => success
- inference.py smoke run => success (completed an episode)

---

## 19. Execution Timeline (Suggested)
Day 1:
- architecture and scope lock

Day 2-3:
- environment logic and tasks

Day 4:
- grader and API contract

Day 5:
- inference and Docker hardening

Day 6:
- deployment and validation

---

## 20. Final Note
CodeFixEnv is a benchmark-oriented environment for evaluating AI debugging reasoning, with deterministic scoring and deployment-ready API behavior.

To finish Round 1 with high confidence, complete the remaining blocked-local checks in your environment:
- openenv validator run
- Hugging Face Space live endpoint validation
