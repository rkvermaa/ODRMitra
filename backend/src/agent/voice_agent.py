"""Voice Agent — simple single-call LLM for fast voice responses.

No ReAct loop, no tools, no RAG lookup at runtime.
All MSME knowledge is baked into the system prompt.
Seller profile is injected so agent knows who it's talking to + can verify.
Optimized for <2 second response time on voice calls.

Two modes:
- Filing mode (no dispute_id): VOICE_SYSTEM_PROMPT — verify identity + collect 6 fields
- Status mode (dispute_id present): VOICE_CASE_STATUS_PROMPT — answer questions about existing case
"""

import json
from typing import Any

from src.core.logging import log
from src.llm import get_llm_client
from src.agent.prompts.voice import VOICE_SYSTEM_PROMPT, VOICE_CASE_STATUS_PROMPT
from src.agent.context.loader import build_seller_context, build_dispute_context


class VoiceAgent:
    """Fast voice agent — single LLM call with rich prompt."""

    def __init__(
        self,
        user_id: str,
        session_id: str,
        dispute_id: str | None = None,
        seller_profile: dict[str, Any] | None = None,
        dispute_context: dict[str, Any] | None = None,
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.dispute_id = dispute_id
        self.seller_profile = seller_profile or {}
        self.dispute_context = dispute_context or {}
        self.llm = get_llm_client()

    def _build_history_context(self, history: list[dict[str, Any]]) -> str:
        """Extract previously collected fields from conversation history."""
        if not history:
            return ""

        extracted_fields: dict[str, str] = {}
        for msg in history:
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            if "[FIELDS]" in content and "[/FIELDS]" in content:
                try:
                    fields_str = content.split("[FIELDS]")[1].split("[/FIELDS]")[0]
                    extracted_fields.update(json.loads(fields_str))
                except (json.JSONDecodeError, IndexError):
                    pass

        if not extracted_fields:
            return ""

        parts = ["## Fields already collected:"]
        for key, value in extracted_fields.items():
            parts.append(f"  - {key}: {value}")
        parts.append("\nDo NOT ask for these again. Ask the next missing field.")
        return "\n".join(parts)

    def _build_messages(
        self,
        user_message: str,
        history: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build message list: system + context + conversation.

        Filing mode: VOICE_SYSTEM_PROMPT + seller context + collected fields
        Status mode: VOICE_CASE_STATUS_PROMPT + seller context + dispute details
        """
        if self.dispute_context:
            # Status mode — existing case
            system_content = VOICE_CASE_STATUS_PROMPT
        else:
            # Filing mode — new complaint
            system_content = VOICE_SYSTEM_PROMPT

        # Inject seller profile (both modes need it)
        seller_ctx = build_seller_context(self.seller_profile)
        if seller_ctx:
            system_content += f"\n\n{seller_ctx}"

        if self.dispute_context:
            # Inject dispute details for status mode
            dispute_ctx = build_dispute_context(self.dispute_context)
            if dispute_ctx:
                system_content += f"\n\n{dispute_ctx}"
        else:
            # Inject already-collected fields for filing mode
            history_ctx = self._build_history_context(history)
            if history_ctx:
                system_content += f"\n\n{history_ctx}"

        messages = [{"role": "system", "content": system_content}]

        # Add conversation history (only user + assistant, skip tool messages)
        for msg in history:
            role = msg.get("role")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": msg.get("content", "")})

        messages.append({"role": "user", "content": user_message})
        return messages

    async def process_message(
        self,
        user_message: str,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Process a voice message with a single LLM call."""
        history = history or []

        mode = "status" if self.dispute_context else "filing"
        log.info(
            f"VoiceAgent({mode}): user={self.user_id[:8]}... "
            f"session={self.session_id[:8]}... "
            f"seller={self.seller_profile.get('name', '?')} "
            f"history={len(history)}"
        )

        try:
            messages = self._build_messages(user_message, history)

            # Single LLM call — no tools, no loop
            response = await self.llm.chat_completion(
                messages=messages,
                tools=None,
                temperature=0.7,
                max_tokens=300,  # Voice responses should be short
            )

            return {
                "content": response.content or "",
                "usage": response.usage,
                "iterations": 1,
                "model": response.model,
                "tool_calls_made": [],
                "error": None,
            }

        except Exception as e:
            log.exception(f"VoiceAgent processing failed: {e}")
            return {
                "content": "Sorry, kuch error aa gaya. Please try again.",
                "usage": {},
                "iterations": 0,
                "model": "",
                "tool_calls_made": [],
                "error": str(e),
            }
