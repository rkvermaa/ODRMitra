"""Agent prompts — separated by channel and purpose."""

from src.agent.prompts.base import BASE_SYSTEM_PROMPT, KNOWLEDGE_PROMPT
from src.agent.prompts.voice import VOICE_SYSTEM_PROMPT, VOICE_CASE_STATUS_PROMPT
from src.agent.prompts.whatsapp import WHATSAPP_GREETING_PROMPT, WHATSAPP_RULES_PROMPT

__all__ = [
    "BASE_SYSTEM_PROMPT",
    "KNOWLEDGE_PROMPT",
    "VOICE_SYSTEM_PROMPT",
    "VOICE_CASE_STATUS_PROMPT",
    "WHATSAPP_GREETING_PROMPT",
    "WHATSAPP_RULES_PROMPT",
]
