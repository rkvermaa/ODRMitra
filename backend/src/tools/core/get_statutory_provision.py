"""Get statutory provision tool — MSMED Act section lookup."""

import json
from pathlib import Path
from typing import Any

from src.tools.base import BaseTool


# Load static MSMED Act data
DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _load_msmed_sections() -> dict:
    """Load MSMED Act sections from static JSON."""
    filepath = DATA_DIR / "msmed_act_2006.json"
    if filepath.exists():
        return json.loads(filepath.read_text(encoding="utf-8"))
    return {}


class GetStatutoryProvisionTool(BaseTool):
    """Look up MSMED Act 2006 sections and provisions."""

    name = "get_statutory_provision"
    description = (
        "Look up specific sections of the MSMED Act 2006 and related statutory provisions. "
        "Use for legal references about delayed payment, interest, liability, MSEFC jurisdiction."
    )
    parameters = {
        "type": "object",
        "properties": {
            "section": {
                "type": "string",
                "description": "Section number or keyword (e.g., '15', '16', '18', 'interest', 'liability', 'msefc')",
            },
        },
        "required": ["section"],
    }

    async def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> dict:
        query = arguments["section"].lower().strip()
        sections = _load_msmed_sections()

        if not sections:
            return {"error": "MSMED Act data not loaded. Please search the knowledge base instead."}

        # Direct section number lookup
        if query in sections:
            return {"section": query, **sections[query]}

        # Keyword search across sections
        results = []
        for sec_num, sec_data in sections.items():
            title = sec_data.get("title", "").lower()
            content = sec_data.get("content", "").lower()
            keywords = sec_data.get("keywords", [])

            if (
                query in title
                or query in content
                or any(query in kw.lower() for kw in keywords)
            ):
                results.append({"section": sec_num, **sec_data})

        if results:
            return {"query": query, "results": results}

        return {
            "query": query,
            "message": f"No section found for '{query}'. Try section numbers (15, 16, 18) or keywords (interest, liability, msefc).",
        }
