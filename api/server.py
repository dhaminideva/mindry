"""
api/server.py
FastAPI app — REST + WebSocket endpoints.
"""
import os
import json
import asyncio
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from core.orchestrator import MindryOrchestrator
from memory.store import MemoryStore

log = structlog.get_logger()

# One orchestrator per server (shared session state)
orchestrator = MindryOrchestrator()
memory = orchestrator.memory


@asynccontextmanager
async def lifespan(app: FastAPI):
    await orchestrator.init()
    log.info("mindry_started")
    yield
    log.info("mindry_shutdown")


app = FastAPI(
    title="Mindry",
    description="Real-Time Thought Structuring Agent",
    version="1.0.0",
    lifespan=lifespan,
)

# Serve static UI
app.mount("/static", StaticFiles(directory="static"), name="static")


# ── REST Endpoints ────────────────────────────────────────────────────────────
@app.get("/setup")
async def setup_check():
    """Diagnostic: check Ollama connection and detected model."""
    from tools.ollama_client import get_model, OLLAMA_BASE_URL
    try:
        model = await get_model()
        return {"status": "ok", "ollama_url": OLLAMA_BASE_URL, "model": model}
    except Exception as e:
        return {"status": "error", "message": str(e)}
@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse("static/index.html")


class ThoughtRequest(BaseModel):
    transcript: str


@app.post("/think")
async def think(req: ThoughtRequest):
    """Main REST endpoint: submit a thought, get structured plan."""
    result = await orchestrator.process(req.transcript)
    return result


@app.post("/interrupt")
async def interrupt():
    """Trigger an interrupt — simulates user speaking mid-response."""
    orchestrator.interrupt()
    return {"status": "interrupted", "state": orchestrator.sm.state}


@app.get("/state")
async def get_state():
    return {
        "state": orchestrator.sm.state,
        "previous_state": orchestrator.sm.previous_state,
    }


@app.get("/metrics")
async def metrics():
    """Production metrics endpoint."""
    lats = orchestrator._metrics["latencies_ms"]
    avg = int(sum(lats) / len(lats)) if lats else 0
    sorted_lats = sorted(lats)
    p95_idx = int(len(sorted_lats) * 0.95) - 1
    p95 = sorted_lats[max(0, p95_idx)] if sorted_lats else 0
    return {
        "avg_latency_ms": avg,
        "p95_latency_ms": p95,
        "total_requests": orchestrator._metrics["total_requests"],
        "interrupt_count": orchestrator._metrics["interrupt_count"],
        "failed_verifications": orchestrator._metrics["failed_verifications"],
        "schema_failures": orchestrator._metrics["schema_failures"],
    }


@app.get("/memory")
async def get_memory():
    """Retrieve all saved thoughts from long-term memory."""
    return await memory.get_all()
@app.get("/conflicts/timeline")
async def conflict_timeline():
    """All conflicts across all sessions, ordered by date."""
    history = memory.get_conflict_history()
    
    # Group by similar conflict text to find recurring patterns
    patterns = {}
    for entry in history:
        # Normalize: lowercase, strip punctuation for grouping
        key = entry["conflict"].lower().strip(".,!?")
        if key not in patterns:
            patterns[key] = []
        patterns[key].append(entry)
    
    # Only flag as recurring if appears more than once
    recurring = {k: v for k, v in patterns.items() if len(v) > 1}
    
    return {
        "total_conflicts": len(history),
        "recurring_count": len(recurring),
        "all_conflicts": history,
        "recurring_patterns": recurring,
    }

@app.delete("/memory/{idea_id}")
async def delete_memory(idea_id: str):
    await memory.delete(idea_id)
    return {"deleted": idea_id}


# ── WebSocket Endpoint ────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket for real-time streaming interaction.
    Send JSON: {"type": "thought", "text": "..."} or {"type": "interrupt"}
    """
    await websocket.accept()
    log.info("websocket_connected")

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if msg.get("type") == "interrupt":
                orchestrator.interrupt()
                await websocket.send_json({
                    "type": "interrupted",
                    "state": orchestrator.sm.state,
                })
                continue

            if msg.get("type") == "thought":
                transcript = msg.get("text", "").strip()
                if not transcript:
                    continue

                # Send "processing" ack immediately
                await websocket.send_json({
                    "type": "processing",
                    "state": "EXTRACTING",
                })

                result = await orchestrator.process(transcript)
                await websocket.send_json({
                    "type": "result",
                    "data": result.model_dump(),
                })

    except WebSocketDisconnect:
        log.info("websocket_disconnected")
    except Exception as e:
        log.error("websocket_error", error=str(e))
        await websocket.close()
