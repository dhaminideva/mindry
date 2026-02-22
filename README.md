# ⚡ Mindry — Real-Time Thought Structuring Agent

> Turn messy spoken thoughts → structured goals → executable roadmaps.
> **100% free. Runs fully local. No API keys. No database.**

---

## 🪟 Windows Setup (Step by Step)

### Step 1 — Install Python
Download from https://python.org/downloads (3.11 or 3.12)
> ✅ During install, check **"Add Python to PATH"**

### Step 2 — Install Ollama (the free local AI)
Download from https://ollama.com/download/windows
Run the installer. After install, open a new terminal and run:
```
ollama pull llama3.2
```
This downloads the free AI model (~2GB). Only needed once.

### Step 3 — Unzip and set up Mindry
Open **Command Prompt** or **PowerShell** in the mindry folder:
```
cd mindry
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Step 4 — Configure
```
copy .env.example .env
```
That's it — no API keys needed! The `.env` file works as-is.

### Step 5 — Start Ollama (keep this running)
Open a **separate** terminal window and run:
```
ollama serve
```
Leave this window open. Ollama must stay running in the background.

### Step 6 — Start Mindry
Back in your first terminal (with venv active):
```
uvicorn main:app --reload --port 8000
```

### Step 7 — Open the app
Go to: **http://localhost:8000**

---

## ✅ Every time you want to use Mindry

1. Open terminal A → run `ollama serve`
2. Open terminal B → `cd mindry` → `venv\Scripts\activate` → `uvicorn main:app --reload --port 8000`
3. Open http://localhost:8000

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/`           | Web UI |
| `POST` | `/think`      | Submit a thought (REST) |
| `POST` | `/interrupt`  | Trigger interrupt |
| `GET`  | `/state`      | Current agent state |
| `GET`  | `/metrics`    | Latency + performance data |
| `GET`  | `/memory`     | All saved thoughts (this session) |
| `DELETE` | `/memory/{id}` | Delete a thought |
| `WS`   | `/ws`         | WebSocket real-time interface |

### REST Example (PowerShell)
```powershell
Invoke-RestMethod -Uri http://localhost:8000/think `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"transcript": "I want to change careers but I have a mortgage and no idea what to do"}'
```

---

## 🔧 Customization

### Change AI model
In `.env`, change `LLM_MODEL` to any model you've pulled:
```
LLM_MODEL=mistral       # Very fast, good quality
LLM_MODEL=phi3          # Tiny, runs on weak hardware
LLM_MODEL=llama3.2      # Default — best balance
LLM_MODEL=gemma2        # Google's model, great reasoning
```
Pull any model with: `ollama pull mistral`

### Change confidence threshold
In `.env`:
```
CONFIDENCE_THRESHOLD=0.5   # Lower = save more thoughts
CONFIDENCE_THRESHOLD=0.8   # Higher = only save very clear thoughts
```

### Add guardrail patterns
In `guardrails/policy.py`, add to `BLOCKED_PATTERNS`:
```python
("your trigger phrase", "Message shown to user"),
```

### Memory note
Thoughts are stored **in memory only** — they reset when you restart the server.
If you want persistence later, the README has SQLite upgrade instructions.

---

## 🏗 Architecture

```
Text Input (UI or API)
       ↓
FastAPI Server  (api/server.py)
       ↓
MindryOrchestrator  (core/orchestrator.py)
   ├── StateMachine      — 8 deterministic states
   ├── GuardrailsPolicy  — safety checks BEFORE LLM
   ├── ThoughtStructurer — text → structured JSON  ┐
   ├── ConflictDetector  — detect contradictions   ├── all via Ollama (free, local)
   ├── RoadmapGenerator  — JSON → action plan      ┘
   └── MemoryStore       — in-memory dict (no DB)
```

### Agent States
```
IDLE → EXTRACTING → STRUCTURING → VERIFYING → COMPLETED
                                      ↓
                                  REFINING → EXTRACTING
            Any state → INTERRUPTED → EXTRACTING
```

---

## 📁 Project Structure
```
mindry/
├── main.py                  # Entry point
├── requirements.txt         # No openai or sqlite deps!
├── .env.example             # Config — no keys needed
├── api/server.py            # FastAPI + WebSocket
├── core/
│   ├── state_machine.py     # Deterministic states
│   ├── orchestrator.py      # Plan→Act→Verify loop
│   └── schemas.py           # Pydantic models
├── tools/
│   ├── ollama_client.py     # Free local LLM client
│   ├── structurer.py        # ThoughtStructurer
│   ├── contradiction.py     # ConflictDetector
│   └── roadmap.py           # RoadmapGenerator
├── memory/store.py          # In-memory storage
├── guardrails/policy.py     # Safety rules
├── static/index.html        # Web UI
└── tests/test_core.py       # Unit tests
```

---

## 🧪 Run Tests
```
venv\Scripts\activate
pytest tests/ -v
```

---

## 💡 Tips
- **Ctrl+Enter** in the text area submits your thought
- **⚡ button** triggers an interrupt mid-processing
- **Memory tab** shows thoughts saved this session
- **Metrics tab** shows latency and request stats
- Ollama first response may be slow (~5–10s) — subsequent ones are faster
