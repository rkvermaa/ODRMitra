"""Core ODR tools — always available."""

from src.tools.core.classify_dispute import ClassifyDisputeTool
from src.tools.core.analyze_document import AnalyzeDocumentTool
from src.tools.core.check_missing_docs import CheckMissingDocsTool
from src.tools.core.predict_outcome import PredictOutcomeTool
from src.tools.core.draft_settlement import DraftSettlementTool
from src.tools.core.calculate_interest import CalculateInterestTool
from src.tools.core.get_statutory_provision import GetStatutoryProvisionTool
from src.tools.core.search_knowledge import SearchKnowledgeTool
from src.tools.core.lookup_cases import LookupCasesTool

CORE_TOOLS: dict[str, type] = {
    "classify_dispute": ClassifyDisputeTool,
    "analyze_document": AnalyzeDocumentTool,
    "check_missing_docs": CheckMissingDocsTool,
    "predict_outcome": PredictOutcomeTool,
    "draft_settlement": DraftSettlementTool,
    "calculate_interest": CalculateInterestTool,
    "get_statutory_provision": GetStatutoryProvisionTool,
    "search_knowledge": SearchKnowledgeTool,
    "lookup_cases": LookupCasesTool,
}
