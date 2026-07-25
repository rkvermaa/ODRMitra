"""LangGraph orchestration for the WhatsApp channel.

A deterministic router classifies every inbound message into one of three
intents, then a dedicated node runs the ReAct agent with the matching skill:

    START -> route_intent --+-- new_complaint      -> ReactAgent(case-filing)
                            +-- existing_complaint -> ReactAgent(whatsapp-filing + status tools)
                            +-- general            -> ReactAgent(legal-info)

The branch nodes reuse the tested ReactAgent (tools, RAG, context blocks,
channel prompts); the graph only decides WHICH process the conversation
follows, per the user's selection.
"""

import json
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from src.core.logging import log
from src.llm import get_llm_client
from src.agent.react_agent import ReactAgent

ROUTER_PROMPT = """\
You route WhatsApp messages for ODRMitra (MSME payment dispute assistant).

Classify the user's latest message into exactly one intent:

- "new_complaint": the user wants to file a NEW complaint / naya case
  (e.g. "nayi complaint file karni hai", "I want to file a case"), OR the
  ongoing conversation is collecting details for a new complaint and this
  message continues it (an answer like a buyer name, mobile number, amount).
- "existing_complaint": the user asks about an already-filed complaint —
  status, next steps, selecting from the complaint menu (a bare number like
  "1" or "2"), providing missing details for an existing case, or documents.
  Greetings (hi/hello/namaste/menu) also go here — the menu is shown.
- "general": general legal or process questions not tied to a specific case
  (e.g. "Section 16 kya hai?", "MSEFC kya hota hai?", "interest kitna lagta hai?").

Stay consistent with the ongoing flow: if the last assistant message was
collecting details for a new complaint, answers continue "new_complaint";
if it was about an existing case, answers continue "existing_complaint".

Reply with ONLY this JSON, nothing else:
{"intent": "new_complaint" | "existing_complaint" | "general"}
"""


class WhatsAppState(TypedDict, total=False):
    """State carried through the WhatsApp graph."""

    user_message: str
    history: list[dict[str, Any]]
    intent: str
    result: dict[str, Any]


class WhatsAppGraph:
    """Three-branch LangGraph agent for WhatsApp conversations."""

    def __init__(
        self,
        user_id: str,
        session_id: str,
        dispute_id: str | None = None,
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.dispute_id = dispute_id
        self.llm = get_llm_client()
        self._graph = self._build()

    def _build(self):
        graph = StateGraph(WhatsAppState)
        graph.add_node("route_intent", self._route_intent)
        graph.add_node("new_complaint", self._new_complaint)
        graph.add_node("existing_complaint", self._existing_complaint)
        graph.add_node("general", self._general)

        graph.set_entry_point("route_intent")
        graph.add_conditional_edges(
            "route_intent",
            lambda state: state["intent"],
            {
                "new_complaint": "new_complaint",
                "existing_complaint": "existing_complaint",
                "general": "general",
            },
        )
        graph.add_edge("new_complaint", END)
        graph.add_edge("existing_complaint", END)
        graph.add_edge("general", END)
        return graph.compile()

    async def _route_intent(self, state: WhatsAppState) -> dict[str, Any]:
        """Classify the message; default to existing_complaint on any failure."""
        # Last few turns give the router the ongoing-flow context.
        tail = [
            f"{m.get('role', 'user')}: {str(m.get('content', ''))[:200]}"
            for m in (state.get("history") or [])[-4:]
        ]
        convo = "\n".join(tail) if tail else "(no prior messages)"

        intent = "existing_complaint"
        try:
            response = await self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": ROUTER_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Recent conversation:\n{convo}\n\n"
                            f"Latest user message: {state['user_message']}"
                        ),
                    },
                ],
                temperature=0.0,
                max_tokens=30,
            )
            raw = (response.content or "").strip()
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed = json.loads(raw)
            if parsed.get("intent") in ("new_complaint", "existing_complaint", "general"):
                intent = parsed["intent"]
        except Exception as e:
            log.warning(f"WhatsApp router failed, defaulting to existing_complaint: {e}")

        log.info(f"WhatsApp router: intent={intent}")
        return {"intent": intent}

    async def _run_agent(
        self,
        state: WhatsAppState,
        skill: str,
        extra_tools: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run the ReAct agent with a deterministically chosen skill."""
        agent = ReactAgent(
            user_id=self.user_id,
            session_id=self.session_id,
            dispute_id=self.dispute_id,
            channel="whatsapp",
            forced_skill=skill,
            extra_tools=extra_tools,
        )
        result = await agent.process_message(
            user_message=state["user_message"],
            history=state.get("history") or [],
        )
        return {"result": result}

    async def _new_complaint(self, state: WhatsAppState) -> dict[str, Any]:
        """File a brand-new complaint: collect details one by one via case-filing."""
        return await self._run_agent(state, "case-filing")

    async def _existing_complaint(self, state: WhatsAppState) -> dict[str, Any]:
        """Menu / status / missing-info collection for already-filed complaints."""
        return await self._run_agent(
            state,
            "whatsapp-filing",
            extra_tools=[
                "lookup_cases",
                "get_statutory_provision",
                "predict_outcome",
                "calculate_interest",
            ],
        )

    async def _general(self, state: WhatsAppState) -> dict[str, Any]:
        """General MSMED Act / process questions via legal-info."""
        return await self._run_agent(state, "legal-info")

    async def process_message(
        self,
        user_message: str,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Same interface as ReactAgent.process_message."""
        final_state = await self._graph.ainvoke(
            {"user_message": user_message, "history": history or []}
        )
        result = final_state.get("result") or {
            "content": "I apologize, but I encountered an error. Please try again.",
            "usage": {},
            "iterations": 0,
            "model": "",
            "tool_calls_made": [],
            "error": "graph_no_result",
        }
        result["intent"] = final_state.get("intent")
        return result
