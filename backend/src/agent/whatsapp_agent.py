"""WhatsApp agent — framework-native (LangChain `create_agent`).

One autonomous agent replaces the hand-rolled router graph: the model gets
ALL ODR tools plus a unified system prompt carrying the conversation flow
(menu → selection → per-branch process), the user's full context (profile,
cases filed by them, cases filed against them), and the filing skills'
collection rules. The framework runs the tool-calling loop natively.

WhatsApp tolerates the extra latency of an autonomous loop — the channel
shows a live typing indicator while the agent works.
"""

import json
from datetime import date
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool

from src.core.logging import log
from src.llm import get_llm_client
from src.skills.loader import SkillLoader
from src.tools.core import CORE_TOOLS
from src.agent.prompts.base import BASE_SYSTEM_PROMPT, KNOWLEDGE_PROMPT
from src.agent.prompts.whatsapp import WHATSAPP_GREETING_PROMPT, WHATSAPP_RULES_PROMPT

# Skills whose collection rules ([FIELDS] tags, completion markers) the agent
# must follow — merged into the prompt instead of routed to exclusively.
_PROCESS_SKILLS = ("case-filing", "whatsapp-filing")

# On WhatsApp, persistence happens through TOOLS, not text tags — tool calls
# are what an autonomous agent executes reliably. This section is appended
# LAST so it supersedes the [FIELDS]/[FILING_COMPLETE] instructions that the
# merged skill processes carry for the voice/web channels.
_TOOL_SAVING_OVERRIDE = """\
## DATA SAVING ON WHATSAPP — OVERRIDES THE [FIELDS] TAG RULES ABOVE

On this channel do NOT emit [FIELDS], [FILING_COMPLETE], or
[WA_COLLECTION_COMPLETE] tags. Persist data by CALLING TOOLS:

1. Existing case — the moment the user provides ANY detail (buyer email,
   GSTIN, state, address, PO number, cause of action...), call
   `save_case_details` with that case's dispute_id and the detail. One
   answer = one immediate save. Never batch, never wait for the rest.
   When the last key detail arrives (buyer email or GSTIN + state + PO
   number), include filing_complete=true in that same call.
2. New complaint — collect the basics one by one (buyer name, buyer mobile,
   what was supplied, invoice amount; the user's own name and mobile come
   from SELLER INFO). Then call `create_new_case` — it files the case AND
   sends the buyer the Section 18 intimation. Share the returned case
   number with the user.

Never claim something is saved unless the tool call succeeded — report the
tool's actual result.\
"""


class WhatsAppAgent:
    """Autonomous WhatsApp agent: all tools, unified prompt, native loop."""

    def __init__(
        self,
        user_id: str,
        session_id: str,
        dispute_id: str | None = None,
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.dispute_id = dispute_id
        self._tool_calls_made: list[dict] = []

    # ── Tools ────────────────────────────────────────────────────────────

    def _build_tools(self) -> list[StructuredTool]:
        """Wrap every core ODR tool as a LangChain tool bound to this
        conversation's context (user, session, dispute)."""
        context = {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "dispute_id": self.dispute_id,
            "channel": "whatsapp",
        }

        wrapped: list[StructuredTool] = []
        for name, tool_cls in CORE_TOOLS.items():
            tool = tool_cls()

            def _make_runner(t=tool, tool_name=name):
                async def _run(**kwargs: Any) -> str:
                    try:
                        result = await t.execute(kwargs, context)
                        self._tool_calls_made.append(
                            {"tool": tool_name, "arguments": kwargs, "success": True}
                        )
                        return (
                            json.dumps(result)
                            if isinstance(result, (dict, list))
                            else str(result)
                        )
                    except Exception as e:  # tool errors go back to the model
                        log.error(f"Tool {tool_name} failed: {e}")
                        self._tool_calls_made.append(
                            {
                                "tool": tool_name,
                                "arguments": kwargs,
                                "success": False,
                                "error": str(e),
                            }
                        )
                        return json.dumps({"error": str(e)})

                return _run

            wrapped.append(
                StructuredTool.from_function(
                    coroutine=_make_runner(),
                    name=name,
                    description=tool.description,
                    args_schema=tool.parameters,
                )
            )
        return wrapped

    # ── Prompt ───────────────────────────────────────────────────────────

    async def _build_system_prompt(self) -> str:
        """Base prompt + user context (both sides) + flow + skill processes."""
        from src.agent.context.loader import (
            build_case_list_context,
            build_dispute_context,
            build_respondent_context,
            build_seller_context,
            load_dispute_context,
            load_disputes_against_user,
            load_seller_profile,
            load_user_disputes,
        )
        from src.db.session import async_session_factory

        async with async_session_factory() as db:
            profile = await load_seller_profile(self.user_id, db)
            filed_by = await load_user_disputes(self.user_id, db)
            against = await load_disputes_against_user(self.user_id, db)
            dispute_info = (
                await load_dispute_context(self.dispute_id, self.user_id, db)
                if self.dispute_id
                else {}
            )

        skill_sections: list[str] = []
        all_skills = SkillLoader.load_all_skills()
        for slug in _PROCESS_SKILLS:
            skill = all_skills.get(slug)
            if skill and skill.get("system_prompt"):
                skill_sections.append(
                    f"## PROCESS: {skill['name']}\n{skill['system_prompt']}"
                )

        parts = [
            BASE_SYSTEM_PROMPT,
            f"\n## Today's Date: {date.today().strftime('%d %B %Y')}",
            "\n## Current Channel: whatsapp",
        ]
        if self.dispute_id:
            parts.append(f"\n## Active Dispute\nDispute ID: {self.dispute_id}")

        parts += [
            build_seller_context(profile),
            build_case_list_context(filed_by),
            build_respondent_context(against),
            build_dispute_context(dispute_info),
            KNOWLEDGE_PROMPT,
            WHATSAPP_GREETING_PROMPT,
            WHATSAPP_RULES_PROMPT,
            *skill_sections,
            _TOOL_SAVING_OVERRIDE,
        ]
        return "\n\n".join(p for p in parts if p)

    # ── Turn ─────────────────────────────────────────────────────────────

    @staticmethod
    def _to_lc_messages(history: list[dict[str, Any]]) -> list:
        """Convert stored user/assistant history to LangChain messages."""
        messages = []
        for m in history:
            role = m.get("role")
            content = m.get("content", "")
            if not content:
                continue
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        return messages

    async def process_message(
        self,
        user_message: str,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """One turn. Same result shape as ReactAgent.process_message."""
        self._tool_calls_made = []

        try:
            system_prompt = await self._build_system_prompt()
            llm = get_llm_client()
            agent = create_agent(
                model=llm.client,
                tools=self._build_tools(),
                system_prompt=system_prompt,
            )

            messages = self._to_lc_messages(history or [])
            messages.append(HumanMessage(content=user_message))

            result = await agent.ainvoke({"messages": messages})

            reply = ""
            total_input = 0
            total_output = 0
            for m in result["messages"]:
                usage = getattr(m, "usage_metadata", None)
                if usage:
                    total_input += usage.get("input_tokens", 0)
                    total_output += usage.get("output_tokens", 0)
            for m in reversed(result["messages"]):
                if isinstance(m, AIMessage) and not getattr(m, "tool_calls", None):
                    reply = m.content if isinstance(m.content, str) else str(m.content)
                    break

            return {
                "content": reply or "I apologize, but I encountered an error. Please try again.",
                "usage": {"input_tokens": total_input, "output_tokens": total_output},
                "iterations": len(self._tool_calls_made) + 1,
                "model": llm.model_name,
                "tool_calls_made": self._tool_calls_made,
                "error": None,
            }

        except Exception as e:
            log.exception(f"WhatsAppAgent processing failed: {e}")
            return {
                "content": "I apologize, but I encountered an error. Please try again.",
                "usage": {},
                "iterations": 0,
                "model": "",
                "tool_calls_made": self._tool_calls_made,
                "error": str(e),
            }
