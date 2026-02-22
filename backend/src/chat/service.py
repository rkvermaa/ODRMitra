"""Chat Service — session and message management.

Simplified from reference (no Redis cache for now — direct DB).
"""

from datetime import datetime, timezone, timedelta
from typing import Any
import uuid

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import log
from src.db.models.session import Session, SessionStatus, SessionType
from src.db.models.message import Message, MessageRole


class ChatService:
    """Manages chat sessions and message history."""

    SESSION_TIMEOUT_HOURS = 24
    HISTORY_LIMIT_FOR_AGENT = 40

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_session(
        self,
        user_id: str,
        channel: str = "web",
        dispute_id: str | None = None,
        session_type: str = "general",
    ) -> Session:
        """Get existing active session or create new one."""
        timeout_threshold = datetime.now(timezone.utc) - timedelta(hours=self.SESSION_TIMEOUT_HOURS)

        # Find existing active session
        conditions = [
            Session.user_id == uuid.UUID(user_id),
            Session.channel == channel,
            Session.status == SessionStatus.ACTIVE.value,
        ]
        if dispute_id:
            conditions.append(Session.dispute_id == uuid.UUID(dispute_id))

        result = await self.db.execute(
            select(Session)
            .where(and_(*conditions))
            .order_by(desc(Session.last_message_at))
            .limit(1)
        )
        session = result.scalar_one_or_none()

        if session and session.last_message_at and session.last_message_at > timeout_threshold:
            log.debug(f"Found existing session: {session.id}")
            return session

        # Create new session
        session = Session(
            user_id=uuid.UUID(user_id),
            dispute_id=uuid.UUID(dispute_id) if dispute_id else None,
            channel=channel,
            session_type=session_type,
            status=SessionStatus.ACTIVE.value,
            last_message_at=datetime.now(timezone.utc),
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)

        log.info(f"Created new session: {session.id}")
        return session

    async def save_message(
        self,
        session_id: str | uuid.UUID,
        role: str,
        content: str,
        tool_call_id: str | None = None,
        tool_name: str | None = None,
        tool_call_data: dict | None = None,
        channel_source: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> Message:
        """Save a message to the session."""
        message = Message(
            session_id=uuid.UUID(str(session_id)),
            role=role,
            content=content,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            tool_call_data=tool_call_data,
            channel_source=channel_source,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        self.db.add(message)

        # Update session last_message_at
        result = await self.db.execute(
            select(Session).where(Session.id == uuid.UUID(str(session_id)))
        )
        session = result.scalar_one_or_none()
        if session:
            session.last_message_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(message)

        log.debug(f"Saved message: {message.id} role={role}")
        return message

    async def get_history_for_agent(
        self,
        session_id: str | uuid.UUID,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get conversation history formatted for agent.

        If there are more messages than the limit, older messages are
        summarized into a context summary and saved on the session.
        This way no information is ever lost.
        """
        limit = limit or self.HISTORY_LIMIT_FOR_AGENT

        # Get session for context summary
        result = await self.db.execute(
            select(Session).where(Session.id == uuid.UUID(str(session_id)))
        )
        session = result.scalar_one_or_none()
        if not session:
            return []

        # Count total messages
        from sqlalchemy import func as sa_func
        count_result = await self.db.execute(
            select(sa_func.count(Message.id))
            .where(Message.session_id == uuid.UUID(str(session_id)))
            .where(Message.role.in_([MessageRole.USER.value, MessageRole.ASSISTANT.value]))
        )
        total_count = count_result.scalar() or 0

        # If messages exceed limit, summarize the older ones
        if total_count > limit:
            await self._summarize_old_messages(session, limit)

        # Get recent messages
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == uuid.UUID(str(session_id)))
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        messages = list(result.scalars().all())
        messages.reverse()

        history = []

        if session.context_summary:
            history.append({
                "role": "system",
                "content": f"[Conversation summary so far — DO NOT ask for information already collected here]\n{session.context_summary}",
            })

        for msg in messages:
            if msg.role in (MessageRole.USER.value, MessageRole.ASSISTANT.value):
                history.append({"role": msg.role, "content": msg.content or ""})
            elif msg.role == MessageRole.TOOL_CALL.value:
                history.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": msg.tool_call_data.get("tool_calls", []) if msg.tool_call_data else [],
                })
            elif msg.role == MessageRole.TOOL_RESULT.value:
                history.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id or "",
                    "content": msg.content or "",
                })

        return history

    async def _summarize_old_messages(
        self,
        session: Session,
        keep_recent: int,
    ) -> None:
        """Summarize older messages into context_summary on the session.

        Builds a structured summary listing all extracted information
        so the agent never re-asks questions.
        """
        # Get ALL messages ordered by time
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session.id)
            .where(Message.role.in_([MessageRole.USER.value, MessageRole.ASSISTANT.value]))
            .order_by(Message.created_at)
        )
        all_messages = list(result.scalars().all())

        if len(all_messages) <= keep_recent:
            return

        # Messages to summarize (the older ones)
        to_summarize = all_messages[:-keep_recent]

        # Build a structured summary from the conversation
        summary_parts = []
        if session.context_summary:
            summary_parts.append(session.context_summary)

        summary_parts.append("\n--- Information from earlier conversation ---")
        for msg in to_summarize:
            prefix = "User" if msg.role == MessageRole.USER.value else "Agent"
            content = (msg.content or "")[:200]  # Truncate very long messages
            summary_parts.append(f"{prefix}: {content}")

        # Extract any [FIELDS] blocks from assistant messages
        import re
        fields_collected = {}
        for msg in all_messages:
            if msg.role == MessageRole.ASSISTANT.value and msg.content:
                match = re.search(r'\[FIELDS\](.*?)\[/FIELDS\]', msg.content, re.DOTALL)
                if match:
                    try:
                        import json
                        fields = json.loads(match.group(1))
                        fields_collected.update(fields)
                    except Exception:
                        pass

        if fields_collected:
            summary_parts.append("\n--- Extracted fields so far ---")
            for k, v in fields_collected.items():
                summary_parts.append(f"  {k}: {v}")

        session.context_summary = "\n".join(summary_parts)
        log.info(f"Summarized {len(to_summarize)} old messages into context_summary")

    async def get_session_messages(
        self,
        session_id: str | uuid.UUID,
        limit: int = 50,
    ) -> list[dict]:
        """Get messages for display (not for agent)."""
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == uuid.UUID(str(session_id)))
            .order_by(Message.created_at)
            .limit(limit)
        )
        messages = result.scalars().all()

        return [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "tool_name": m.tool_name,
                "channel_source": m.channel_source,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]
