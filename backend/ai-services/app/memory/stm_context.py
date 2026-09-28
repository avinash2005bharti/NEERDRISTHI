"""
ORCA STM (Short-Term Memory) Context Parser.

In the ORCA dual-layer architecture:
- MongoDB is the primary source of truth for STM, managed exclusively by Node.js.
- Node.js transmits relevant recent conversation history, user preferences, and query context to FastAPI.
- This module formats and merges the incoming STM payload into the LangGraph AgentState.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class STMContextPayload(BaseModel):
    conversation_id: str
    recent_messages: List[Dict[str, Any]] = Field(default_factory=list, description="Recent user/assistant chat turns from MongoDB")
    user_preferences: Dict[str, Any] = Field(default_factory=dict, description="Active user settings, language, vessel class")
    current_location: Optional[Dict[str, Any]] = None
    active_analysis: Optional[Dict[str, Any]] = None


class STMContextManager:
    """
    Parses and extracts STM (Short-Term Memory) context sent from Node.js Express gateway.
    """

    @staticmethod
    def extract_context_summary(stm_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not stm_payload:
            return {
                "has_stm": False,
                "history_turns": 0,
                "context_notes": []
            }

        recent = stm_payload.get("recent_messages", [])
        prefs = stm_payload.get("user_preferences", {})

        notes = []
        if prefs.get("preferredLanguage"):
            notes.append(f"Preferred language: {prefs['preferredLanguage']}")
        if prefs.get("vesselClass"):
            notes.append(f"Vessel class: {prefs['vesselClass']}")

        # Extract last user query topic if present
        for msg in reversed(recent):
            if msg.get("role") == "user":
                notes.append(f"Preceding query: {msg.get('content', '')[:100]}")
                break

        return {
            "has_stm": len(recent) > 0 or bool(prefs),
            "history_turns": len(recent),
            "context_notes": notes,
            "preferences": prefs,
        }


stm_manager = STMContextManager()
