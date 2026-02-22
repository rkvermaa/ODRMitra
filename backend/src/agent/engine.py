"""Agent Engine — orchestrator that picks the right agent based on channel.

- Voice channel → VoiceAgent (single LLM call, fast, no tools, seller profile injected)
- WhatsApp/web/telegram → ReactAgent (ReAct loop with tools)
"""

from typing import Any

from src.core.logging import log
from src.agent.voice_agent import VoiceAgent
from src.agent.react_agent import ReactAgent


class AgentEngine:
    """Thin orchestrator — delegates to VoiceAgent or ReactAgent.

    Maintains the same interface so callers (chat.py, webhook.py) don't change.
    For voice channel, fetches seller profile from DB before processing.
    """

    def __init__(
        self,
        user_id: str,
        session_id: str,
        dispute_id: str | None = None,
        channel: str = "web",
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.dispute_id = dispute_id
        self.channel = channel

        # For non-voice channels, create agent immediately
        self._agent: VoiceAgent | ReactAgent | None = None

        if channel != "voice":
            self._agent = ReactAgent(
                user_id=user_id,
                session_id=session_id,
                dispute_id=dispute_id,
                channel=channel,
            )

        log.info(
            f"AgentEngine: channel={channel} → "
            f"{'VoiceAgent (lazy)' if channel == 'voice' else 'ReactAgent'}"
        )

    async def _get_voice_agent(self) -> VoiceAgent:
        """Create VoiceAgent with seller profile (and dispute context if existing case)."""
        from src.agent.context.loader import load_seller_profile, load_dispute_context
        from src.db.session import async_session_factory

        seller_profile: dict[str, Any] = {}
        dispute_context: dict[str, Any] = {}
        try:
            async with async_session_factory() as db:
                seller_profile = await load_seller_profile(self.user_id, db)
                if self.dispute_id:
                    dispute_context = await load_dispute_context(
                        self.dispute_id, self.user_id, db
                    )
        except Exception as e:
            log.warning(f"Failed to load voice agent context: {e}")

        return VoiceAgent(
            user_id=self.user_id,
            session_id=self.session_id,
            dispute_id=self.dispute_id,
            seller_profile=seller_profile,
            dispute_context=dispute_context,
        )

    async def process_message(
        self,
        user_message: str,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Process message by delegating to the appropriate agent."""
        if self.channel == "voice":
            # Lazy-create voice agent (needs async DB call for profile)
            if self._agent is None:
                self._agent = await self._get_voice_agent()

        return await self._agent.process_message(
            user_message=user_message,
            history=history,
        )
