"""React Agent — multi-turn tool-calling agent for WhatsApp/web channels.

Uses ReAct loop: LLM → tool calls → results → repeat until response.
Supports skill discovery, RAG context, and tool execution.
Used for WhatsApp (text-based, latency ~5-10s is acceptable).
"""

import json
from typing import Any

from src.config import settings
from src.core.logging import log
from src.llm import get_llm_client
from src.tools.registry import ToolRegistry
from src.skills.loader import SkillLoader
from src.rag.qdrant_search import QdrantSearch, LEGAL_COLLECTION, CASE_DOCS_COLLECTION
from src.agent.prompts.base import BASE_SYSTEM_PROMPT, KNOWLEDGE_PROMPT
from src.agent.prompts.whatsapp import WHATSAPP_GREETING_PROMPT, WHATSAPP_RULES_PROMPT


class ReactAgent:
    """ReAct loop agent for WhatsApp/web channels."""

    MAX_ITERATIONS = 5

    def __init__(
        self,
        user_id: str,
        session_id: str,
        dispute_id: str | None = None,
        channel: str = "whatsapp",
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.dispute_id = dispute_id
        self.channel = channel
        self.llm = get_llm_client()
        self.tool_registry = ToolRegistry()
        self._tool_calls_made: list[dict] = []

    def _discover_skill(self, message: str) -> dict[str, Any] | None:
        """Discover the most relevant skill for the user's message."""
        all_skills = SkillLoader.load_all_skills()
        if not all_skills:
            return None

        message_lower = message.lower()

        keyword_map = {
            "case-filing": [
                "file", "claim", "case", "invoice", "payment", "complaint",
                "soc", "filing", "nai", "naya", "new", "darz",
            ],
            "case-status": [
                "status", "purani", "existing", "check", "update",
                "kya hua", "case number",
            ],
            "whatsapp-filing": [
                "gstin", "pan", "document", "upload", "po number", "address",
            ],
            "digital-guided-pathway": [
                "predict", "outcome", "dgp", "analysis", "settlement", "suggestion",
            ],
            "negotiation": [
                "negotiate", "offer", "counter", "settlement", "agree",
            ],
            "registration": [
                "register", "signup", "eligibility", "udyam", "how", "what is",
            ],
            "legal-info": [
                "section", "act", "law", "legal", "interest", "msefc", "provision",
            ],
        }

        best_skill = None
        best_score = 0

        for skill_slug, keywords in keyword_map.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            if score > best_score:
                best_score = score
                best_skill = skill_slug

        if best_skill and best_skill in all_skills:
            return all_skills[best_skill]

        # Channel-based defaults
        if self.channel == "whatsapp":
            return all_skills.get("whatsapp-filing") or all_skills.get("case-filing")

        if self.dispute_id:
            return all_skills.get("case-filing")
        return all_skills.get("legal-info")

    def _setup_tools(self, skill: dict[str, Any]) -> None:
        """Enable tools for the discovered skill."""
        tool_names = skill.get("tools", [])
        skill_slug = skill.get("slug", "")
        enabled = self.tool_registry.enable_tools_for_skill(tool_names, skill_slug)
        log.debug(f"Enabled {enabled} tools for skill: {skill_slug}")

    def _build_history_context(self, history: list[dict[str, Any]]) -> str:
        """Build conversation history summary for the system prompt."""
        if not history:
            return ""

        user_msgs = [m for m in history if m.get("role") == "user"]
        assistant_msgs = [m for m in history if m.get("role") == "assistant"]

        parts = [f"## Conversation History Context\n"]
        parts.append(
            f"This is an ongoing conversation "
            f"({len(user_msgs)} user messages, {len(assistant_msgs)} assistant responses)."
        )

        # Extract previously extracted fields
        extracted_fields: dict[str, str] = {}
        for msg in assistant_msgs:
            content = msg.get("content", "")
            if "[FIELDS]" in content and "[/FIELDS]" in content:
                try:
                    fields_str = content.split("[FIELDS]")[1].split("[/FIELDS]")[0]
                    extracted_fields.update(json.loads(fields_str))
                except (json.JSONDecodeError, IndexError):
                    pass

        if extracted_fields:
            parts.append(f"\nFields already collected:")
            for key, value in extracted_fields.items():
                parts.append(f"  - {key}: {value}")
            parts.append("\nDo NOT ask for fields that are already collected.")

        if user_msgs:
            last_user = user_msgs[-1].get("content", "")[:200]
            parts.append(f"\nLast user message: \"{last_user}\"")

        return "\n".join(parts)

    def _build_system_prompt(
        self,
        skill: dict[str, Any],
        rag_context: str,
        history: list[dict[str, Any]] | None = None,
    ) -> str:
        """Build system prompt from base + skill + channel prompts + context."""
        from datetime import date

        parts = [
            BASE_SYSTEM_PROMPT,
            f"\n## Today's Date: {date.today().strftime('%d %B %Y')}",
            f"\n## Current Channel: {self.channel}",
            f"\n## Current Skill: {skill['name']}",
            skill.get("system_prompt", ""),
        ]

        if self.dispute_id:
            parts.append(f"\n## Active Dispute\nDispute ID: {self.dispute_id}")

        if rag_context:
            parts.append(f"\n## Reference Context\n{rag_context}")

        # History context
        history_context = self._build_history_context(history or [])
        if history_context:
            parts.append(history_context)

        # Common knowledge
        parts.append(KNOWLEDGE_PROMPT)

        # Channel-specific prompts
        parts.append(WHATSAPP_GREETING_PROMPT)
        parts.append(WHATSAPP_RULES_PROMPT)

        return "\n\n".join(parts)

    def _build_tool_context(self) -> dict[str, Any]:
        """Build context dict passed to tools."""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "dispute_id": self.dispute_id,
            "channel": self.channel,
        }

    def _load_rag_context(self, user_message: str) -> str:
        """Load RAG context from legal + case doc collections."""
        rag_context = ""
        try:
            rag_context = QdrantSearch.build_context(
                user_message,
                collection_name=LEGAL_COLLECTION,
                max_tokens=1000,
            )
        except Exception as e:
            log.warning(f"Legal RAG context loading failed: {e}")

        if self.dispute_id:
            try:
                case_context = QdrantSearch.build_context(
                    user_message,
                    collection_name=CASE_DOCS_COLLECTION,
                    max_tokens=500,
                    filters={"dispute_id": self.dispute_id},
                )
                if case_context:
                    rag_context = (
                        f"{rag_context}\n\n{case_context}" if rag_context else case_context
                    )
            except Exception as e:
                log.warning(f"Case docs RAG context loading failed: {e}")

        return rag_context

    async def process_message(
        self,
        user_message: str,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Process a message using ReAct loop with tools."""
        history = history or []
        self._tool_calls_made = []

        log.info(
            f"ReactAgent: user={self.user_id[:8]}... "
            f"channel={self.channel} session={self.session_id[:8]}... "
            f"history={len(history)}"
        )

        try:
            # 1. Discover skill
            skill = self._discover_skill(user_message)
            if not skill:
                return {
                    "content": "I'm sorry, I couldn't find the right skill. Please try rephrasing.",
                    "usage": {},
                    "iterations": 0,
                    "model": "",
                    "tool_calls_made": [],
                    "error": "no_skill_found",
                }

            log.info(f"Discovered skill: {skill['name']}")

            # 2. Setup tools
            self._setup_tools(skill)

            # 3. Load RAG context
            rag_context = self._load_rag_context(user_message)

            # 4. Build system prompt
            system_prompt = self._build_system_prompt(skill, rag_context, history)

            # 5. Prepare messages
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_prompt}
            ]
            messages.extend(history)
            messages.append({"role": "user", "content": user_message})

            # 6. Get tool definitions
            tools = self.tool_registry.get_tool_definitions()
            log.info(f"Enabled tools: {self.tool_registry.get_enabled_tools()}")

            # 7. ReAct loop
            return await self._react_loop(messages, tools)

        except Exception as e:
            log.exception(f"ReactAgent processing failed: {e}")
            return {
                "content": "I apologize, but I encountered an error. Please try again.",
                "usage": {},
                "iterations": 0,
                "model": "",
                "tool_calls_made": [],
                "error": str(e),
            }

    async def _react_loop(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Execute ReAct loop until response or max iterations."""
        iteration = 0
        total_input = 0
        total_output = 0

        while iteration < self.MAX_ITERATIONS:
            iteration += 1
            log.debug(f"ReAct iteration {iteration}/{self.MAX_ITERATIONS}")

            response = await self.llm.chat_completion(
                messages=messages,
                tools=tools if tools else None,
                temperature=0.7,
            )

            total_input += response.usage.get("input_tokens", 0)
            total_output += response.usage.get("output_tokens", 0)

            if response.has_tool_calls:
                tool_results = await self._execute_tools(response.tool_calls)

                messages.append({
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [tc.to_dict() for tc in response.tool_calls],
                })

                for tool_call, result in zip(response.tool_calls, tool_results):
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
                continue

            return {
                "content": response.content or "",
                "usage": {"input_tokens": total_input, "output_tokens": total_output},
                "iterations": iteration,
                "model": response.model,
                "tool_calls_made": self._tool_calls_made,
                "error": None,
            }

        return {
            "content": "I'm having trouble processing. Please try again with a simpler question.",
            "usage": {"input_tokens": total_input, "output_tokens": total_output},
            "iterations": iteration,
            "model": self.llm.model_name,
            "tool_calls_made": self._tool_calls_made,
            "error": "max_iterations_reached",
        }

    async def _execute_tools(self, tool_calls: list) -> list[str]:
        """Execute tool calls and return results."""
        results = []
        tool_context = self._build_tool_context()

        for tc in tool_calls:
            log.info(f"Executing tool: {tc.name} args={tc.arguments}")
            try:
                result = await self.tool_registry.execute_tool(
                    name=tc.name, arguments=tc.arguments, context=tool_context,
                )
                self._tool_calls_made.append({
                    "tool": tc.name,
                    "arguments": tc.arguments,
                    "success": True,
                })
                result_str = json.dumps(result) if isinstance(result, dict) else str(result)
                results.append(result_str)
                log.info(f"Tool {tc.name} result: {result_str[:200]}...")
            except Exception as e:
                log.error(f"Tool {tc.name} failed: {e}")
                self._tool_calls_made.append({
                    "tool": tc.name,
                    "arguments": tc.arguments,
                    "success": False,
                    "error": str(e),
                })
                results.append(json.dumps({"error": str(e)}))

        return results
