# 🚀 CodeFixEnv — OpenEnv RL Environment for AI Code Debugging

## 🧠 Overview

**CodeFixEnv** is a production-grade **OpenEnv-compatible reinforcement learning environment** designed to evaluate and train AI agents (LLMs) on **real-world code debugging tasks**.

The environment simulates a realistic developer workflow where an agent must iteratively **analyze, modify, and fix buggy Python code** using structured actions.

Unlike toy environments, CodeFixEnv focuses on:

* Real debugging scenarios
* Gradual improvement-based rewards
* Deterministic evaluation via test cases

👉 This makes it a **benchmark-quality environment** for evaluating modern LLM agents.

---

# 🎯 Objective

The goal of the agent is to:

> Transform buggy Python code into a correct and functional version through sequential actions.

Each episode represents a debugging session where the agent:

1. Observes buggy code
2. Applies fixes step-by-step
3. Receives feedback (reward)
4. Stops when code is correct or steps are exhausted

---

# 🏗️ System Architecture

```
LLM Agent (inference.py)
        ↓
   HTTP Requests
        ↓
 FastAPI Server (app.py)
        ↓
 CodeFixEnv (environment.py)
        ↓
 ├── Logic Engine (logic.py)
 ├── Reward System (reward.py)
 ├── Task Loader (tasks/)
 ├── Grader (graders/)
        ↓
 Response (state, reward, done)
```

---

# 📁 Project Structure

```
codefix-env/
├── app.py                     # FastAPI server (API layer)
├── openenv.yaml              # OpenEnv specification

├── env/
│   ├── environment.py        # RL environment (step/reset)
│   ├── logic.py              # Code transformation logic
│   ├── state.py              # State representation
│   ├── actions.py            # Action parsing
│   ├── reward.py             # Reward computation

├── tasks/
│   ├── easy.py
│   ├── medium.py
│   ├── hard.py
│   └── task_loader.py        # Task selection

├── graders/
│   ├── grader.py             # Scoring logic
│   └── testcases.py          # Deterministic evaluation

├── models/
│   ├── request_models.py     # API input schemas
│   └── response_models.py    # API output schemas

├── utils/
│   ├── code_executor.py      # Safe execution
│   ├── diff_utils.py         # Code comparison
│   └── logger.py

├── inference.py              # Baseline agent runner
├── Dockerfile                # Container config
├── requirements.txt
├── README.md
```

---

# ⚙️ Environment Design

## 🔹 State Representation

Each state contains:

```json
{
  "code": "current python code",
  "error": "error description",
  "step_count": 0,
  "history": ["previous actions"]
}
```

---

## 🔹 Action Space

The agent interacts using **text-based actions**:

* `fix_syntax`
* `fix_logic`
* `replace_line:<line_no>:<new_code>`
* `noop`

👉 Designed to be:

* LLM-friendly
* interpretable
* deterministic

---

## 🔹 Episode Flow

1. Agent calls `/reset`
2. Receives buggy code
3. Iteratively calls `/step`
4. Environment:

   * applies action
   * computes reward
   * returns updated state
5. Episode ends when:

   * code is correct ✅
   * max steps reached ❌

---

# 🎯 Tasks Design

CodeFixEnv includes **3 progressively harder tasks**:

---

## 🟢 Easy

* Simple syntax errors
* Example: missing brackets

👉 Tests basic correction ability

---

## 🟡 Medium

* Logical errors
* Example: incorrect operations

👉 Requires reasoning

---

## 🔴 Hard

* Multiple bugs + edge cases
* Combination of syntax + logic

👉 Designed to challenge advanced agents

---

# 🧮 Grading System

The grader evaluates code deterministically using test cases.

## ✅ Scoring Range

```
0.0 → completely incorrect  
0.5 → partially correct  
1.0 → fully correct  
```

---

## 🧠 Scoring Logic

Reward is based on **progress**, not just final success:

* Syntax correctness → partial reward
* Passing test cases → higher reward
* Full correctness → max reward

👉 This avoids sparse rewards and improves learning signal.

---

# 🎁 Reward Design

The reward function is **dense and incremental**:

| Condition      | Reward |
| -------------- | ------ |
| Syntax fixed   | +0.3   |
| Logic improved | +0.5   |
| Fully correct  | +1.0   |
| Regression     | -0.2   |

---

## ⚠️ Why this matters

* Encourages step-by-step improvement
* Prevents random guessing
* Supports RL and LLM-based agents

---

# 🌐 API Specification

## 🔹 POST `/reset`

Returns initial environment state.

### Response:

```json
{
  "state": {...}
}
```

---

## 🔹 POST `/step`

### Input:

```json
{
  "action": "fix_syntax"
}
```

### Response:

```json
{
  "state": {...},
  "reward": 0.3,
  "done": false
}
```

---

# 🤖 Inference Pipeline

The `inference.py` script:

1. Loads environment via API
2. Uses an LLM (OpenAI-compatible client)
3. Generates actions
4. Interacts with environment
5. Logs rewards

---

## 🔑 Required Environment Variables

* `API_BASE_URL`
* `MODEL_NAME`
* `HF_TOKEN`

---

# 🐳 Deployment

## Docker

The environment runs inside a Docker container:

* FastAPI server auto-starts
* Exposes port `7860`

---

## Hugging Face Spaces

Deployment steps:

1. Create Docker Space
2. Upload repository
3. Set environment variables
4. Run

---

# ✅ Validation

Before submission:

* `/reset` returns HTTP 200
* Docker builds successfully
* `openenv validate` passes
* `inference.py` runs without error

---

# 🚫 What This Project Avoids

To ensure quality and fairness:

❌ No random rewards
❌ No trivial toy tasks
❌ No non-deterministic grading
❌ No ambiguous action space
❌ No hidden logic

---

# 🏆 Key Strengths

* Real-world debugging simulation
* Strong reward shaping
* Deterministic evaluation
* Clean API-based design
* Fully OpenEnv compliant

---

# 🔮 Future Improvements

* Multi-language support
* Advanced code analysis
* Integration with real-world datasets
* RL fine-tuning pipelines

---

# 👥 Team

Built for OpenEnv Hackathon Round 1.

---

# 📌 Final Note

CodeFixEnv is not just an environment —
it is a **benchmark system for evaluating AI reasoning and debugging ability**.

---
