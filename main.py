"""
Mindry — Real-Time Thought Structuring Agent
Run: uvicorn main:app --reload --port 8000
"""
from api.server import app

__all__ = ["app"]
