"""Chat routes — conversation handling with ODR agent."""

import asyncio
import json
import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import DBSession, CurrentUserId
from src.core.logging import log
from src.chat.service import ChatService
from src.agent.engine import AgentEngine
from src.db.models.session import Session
from src.db.models.message import Message, MessageRole

router = APIRouter()


class HandoffRequest(BaseModel):
    """Handoff request — create dispute from voice data and dispatch WhatsApp followup."""
    collected_fields: dict = {}
    transcript: list[dict] | None = None  # Full voice conversation [{role, content}, ...]
    session_id: str | None = None


class ChatRequest(BaseModel):
    """Chat request schema."""
    message: str
    session_id: str | None = None
    dispute_id: str | None = None
    channel: str = "web"


class ChatResponse(BaseModel):
    """Chat response schema."""
    response: str
    session_id: str
    usage: dict
    tool_calls_made: list[dict] = []


FIELD_EXTRACTION_PROMPT = """\
You are a data extraction assistant. Analyze the voice conversation transcript below and extract structured fields.

Extract these fields from the conversation:
- title: Case title (usually "Payment dispute - [seller name]")
- respondent_name: The buyer/respondent person's name (e.g. "Brajesh")
- respondent_company: The buyer/respondent's company name (e.g. "Passageway")
- respondent_mobile: Buyer's mobile number (10 digits, no country code)
- seller_mobile: Seller's mobile number (the caller's verified number)
- goods_services_description: What goods or services were supplied
- invoice_amount: Invoice amount as a number (e.g. 50000, not "50 hazaar")

RULES:
- Return ONLY a JSON object with these 7 fields.
- If a field is not found in the conversation, set it to null.
- For invoice_amount: convert Hindi/Hinglish numbers to digits (e.g. "paanch lakh" = 500000, "50 hazaar" = 50000, "2 lakh 30 hazaar" = 230000).
- For mobile numbers: extract only 10-digit numbers, remove any +91 or country code prefix.
- For respondent_name: extract ONLY the person's name. For respondent_company: extract ONLY the company name.
- Do NOT include any text outside the JSON object. No markdown, no explanation.
"""


async def _extract_fields_from_transcript(transcript: list[dict]) -> dict:
    """Use LLM to extract clean structured fields from voice conversation transcript."""
    from src.llm.client import get_llm_client

    # Build transcript text
    lines = []
    for msg in transcript:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            lines.append(f"Caller: {content}")
        elif role == "assistant":
            # Strip [FIELDS]...[/FIELDS] and [FILING_COMPLETE] tags
            clean = re.sub(r'\[FIELDS\][\s\S]*?\[/FIELDS\]', '', content)
            clean = clean.replace("[FILING_COMPLETE]", "").strip()
            if clean:
                lines.append(f"Agent: {clean}")

    transcript_text = "\n".join(lines)

    llm = get_llm_client()
    result = await llm.chat_completion(
        messages=[
            {"role": "system", "content": FIELD_EXTRACTION_PROMPT},
            {"role": "user", "content": f"TRANSCRIPT:\n{transcript_text}"},
        ],
        temperature=0.1,
        max_tokens=500,
    )

    # Parse the JSON response
    try:
        raw = result.content or ""
        # Strip markdown code fences if present
        raw = re.sub(r'^```(?:json)?\s*', '', raw.strip())
        raw = re.sub(r'\s*```$', '', raw.strip())
        extracted = json.loads(raw)
        # Filter out null values
        return {k: v for k, v in extracted.items() if v is not None}
    except (json.JSONDecodeError, TypeError) as e:
        log.warning(f"Failed to parse LLM field extraction: {e}, raw={result.content}")
        return {}


@router.post("/handoff")
async def handoff_to_whatsapp(
    request: HandoffRequest,
    user_id: CurrentUserId,
    db: DBSession,
):
    """Create dispute from voice data and dispatch WhatsApp followup.

    If transcript is provided, uses LLM to extract clean fields from conversation.
    Falls back to collected_fields if no transcript or extraction fails.
    """
    fields = dict(request.collected_fields)

    # If transcript provided, extract fields via LLM (overrides raw collected_fields)
    if request.transcript and len(request.transcript) > 0:
        try:
            extracted = await _extract_fields_from_transcript(request.transcript)
            log.info(f"LLM extracted fields: {extracted}")
            if extracted:
                # Merge: LLM extraction takes priority, fall back to collected_fields
                for k, v in extracted.items():
                    if v:
                        fields[k] = str(v)
        except Exception as e:
            log.warning(f"Field extraction from transcript failed, using raw fields: {e}")

    seller_mobile = fields.get("seller_mobile")
    # Allow "pending" or missing seller_mobile — dispute is created, WhatsApp skipped
    has_valid_mobile = seller_mobile and seller_mobile != "pending"

    from src.db.models.dispute import Dispute
    from src.api.routes.disputes import _generate_case_number

    case_number = await _generate_case_number(db)

    # Build respondent_name: "Person (Company)" if both present
    person_name = fields.get("respondent_name", "")
    company_name = fields.get("respondent_company", "")
    if person_name and company_name:
        full_respondent_name = f"{person_name} ({company_name})"
    else:
        full_respondent_name = person_name or company_name or None

    dispute = Dispute(
        claimant_id=user_id,
        case_number=case_number,
        title=fields.get("title", "MSME Payment Dispute"),
        category="delayed_payment",
        respondent_name=full_respondent_name,
        respondent_mobile=fields.get("respondent_mobile"),
        goods_services_description=fields.get("goods_services_description"),
    )

    # Parse invoice_amount
    invoice_amount_str = fields.get("invoice_amount", "")
    if invoice_amount_str:
        try:
            amount = float(re.sub(r'[^\d.]', '', str(invoice_amount_str)))
            dispute.invoice_amount = amount
            dispute.claimed_amount = amount
        except (ValueError, TypeError):
            pass

    db.add(dispute)
    await db.flush()
    await db.refresh(dispute)

    log.info(f"Handoff: Created dispute {dispute.id} (case: {dispute.case_number}, fields: {list(fields.keys())})")

    await db.commit()

    # Check if we have enough info to send buyer intimation right away
    has_buyer_mobile = fields.get("respondent_mobile") and fields.get("respondent_mobile") != "pending"

    if has_valid_mobile and has_buyer_mobile:
        # All key fields collected — send intimation to both buyer and seller
        from src.tasks.dispatcher import dispatch_buyer_and_seller_intimation
        asyncio.create_task(
            dispatch_buyer_and_seller_intimation(
                dispute_id=str(dispute.id),
                user_id=user_id,
            )
        )
    elif has_valid_mobile:
        # Have seller mobile but missing buyer mobile — send WhatsApp followup to seller
        from src.tasks.dispatcher import dispatch_whatsapp_followup
        asyncio.create_task(
            dispatch_whatsapp_followup(
                user_id=user_id,
                dispute_id=str(dispute.id),
                seller_mobile=seller_mobile,
                collected_fields=fields,
            )
        )

    return {"dispute_id": str(dispute.id), "case_number": dispute.case_number}


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    user_id: CurrentUserId,
    db: DBSession,
):
    """Send a message and get agent response."""
    chat_service = ChatService(db)

    # Use existing session if provided, otherwise create new
    session = None
    if request.session_id:
        from sqlalchemy import select as sa_select
        result = await db.execute(
            sa_select(Session).where(
                Session.id == request.session_id,
                Session.user_id == user_id,
            )
        )
        session = result.scalar_one_or_none()

    if not session:
        session = await chat_service.get_or_create_session(
            user_id=user_id,
            channel=request.channel,
            dispute_id=request.dispute_id,
        )

    # Save user message
    await chat_service.save_message(
        session_id=session.id,
        role=MessageRole.USER.value,
        content=request.message,
        channel_source=request.channel,
    )

    # Get conversation history for agent
    history = await chat_service.get_history_for_agent(session.id)

    # Process with agent
    agent = AgentEngine(
        user_id=user_id,
        session_id=str(session.id),
        dispute_id=request.dispute_id,
        channel=request.channel,
    )

    try:
        result = await agent.process_message(
            user_message=request.message,
            history=history,
        )
    except Exception as e:
        log.exception("Agent processing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message",
        )

    # Save assistant message
    await chat_service.save_message(
        session_id=session.id,
        role=MessageRole.ASSISTANT.value,
        content=result["content"],
        input_tokens=result["usage"].get("input_tokens"),
        output_tokens=result["usage"].get("output_tokens"),
    )

    # Save tool call messages if any
    for tc in result.get("tool_calls_made", []):
        await chat_service.save_message(
            session_id=session.id,
            role=MessageRole.TOOL_CALL.value,
            content=f"Called {tc['tool']}",
            tool_name=tc["tool"],
            tool_call_data=tc,
        )

    await db.commit()

    # Note: [FILING_COMPLETE] handling is now done by the frontend via /chat/handoff.
    # The _handle_filing_complete fallback is kept for non-voice channels only (e.g. web chat).
    if "[FILING_COMPLETE]" in result["content"] and request.channel not in ("voice",):
        try:
            await _handle_filing_complete(
                response_text=result["content"],
                user_id=user_id,
                db=db,
            )
        except Exception as e:
            log.warning(f"_handle_filing_complete fallback failed (non-critical): {e}")

    return ChatResponse(
        response=result["content"],
        session_id=str(session.id),
        usage=result["usage"],
        tool_calls_made=result.get("tool_calls_made", []),
    )


@router.get("/sessions")
async def list_sessions(
    user_id: CurrentUserId,
    db: DBSession,
    dispute_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """List chat sessions for current user."""
    conditions = [Session.user_id == user_id]
    if dispute_id:
        conditions.append(Session.dispute_id == dispute_id)

    count_result = await db.execute(
        select(func.count(Session.id)).where(*conditions)
    )
    total = count_result.scalar()

    result = await db.execute(
        select(Session)
        .where(*conditions)
        .order_by(desc(Session.last_message_at))
        .limit(limit)
        .offset(offset)
    )
    sessions = result.scalars().all()

    return {
        "total": total,
        "sessions": [
            {
                "id": str(s.id),
                "dispute_id": str(s.dispute_id) if s.dispute_id else None,
                "channel": s.channel,
                "session_type": s.session_type,
                "status": s.status,
                "created_at": s.created_at.isoformat(),
                "last_message_at": s.last_message_at.isoformat() if s.last_message_at else None,
            }
            for s in sessions
        ],
    }


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    user_id: CurrentUserId,
    db: DBSession,
):
    """Get messages for a session."""
    # Verify session belongs to user
    result = await db.execute(
        select(Session)
        .where(Session.id == session_id)
        .where(Session.user_id == user_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    chat_service = ChatService(db)
    messages = await chat_service.get_session_messages(session_id)

    return {
        "session_id": session_id,
        "dispute_id": str(session.dispute_id) if session.dispute_id else None,
        "messages": messages,
    }


async def _handle_filing_complete(
    response_text: str,
    user_id: str,
    db: AsyncSession,
):
    """After voice agent returns [FILING_COMPLETE], parse fields and dispatch WhatsApp followup."""
    try:
        # Extract all [FIELDS] blocks and merge them
        fields_matches = re.findall(r'\[FIELDS\]([\s\S]*?)\[/FIELDS\]', response_text)
        collected_fields: dict = {}

        for match in fields_matches:
            try:
                parsed = json.loads(match)
                collected_fields.update(parsed)
            except json.JSONDecodeError:
                pass

        seller_mobile = collected_fields.get("seller_mobile")
        if not seller_mobile:
            log.warning("FILING_COMPLETE but no seller_mobile in fields")
            return

        log.info(f"Filing complete. Fields: {list(collected_fields.keys())}. Seller mobile: {seller_mobile}")

        # Create dispute record with basic info
        from src.db.models.dispute import Dispute

        # Guard: check if a dispute was already created for this user recently (via /handoff)
        from datetime import timedelta
        recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=2)
        existing_result = await db.execute(
            select(Dispute).where(
                Dispute.claimant_id == user_id,
                Dispute.created_at >= recent_cutoff,
            ).order_by(Dispute.created_at.desc()).limit(1)
        )
        if existing_result.scalar_one_or_none():
            log.info("Skipping _handle_filing_complete: dispute already created via /handoff")
            return

        from src.api.routes.disputes import _generate_case_number
        case_number = await _generate_case_number(db)

        dispute = Dispute(
            claimant_id=user_id,
            case_number=case_number,
            title=collected_fields.get("title", "MSME Payment Dispute"),
            category="delayed_payment",
            respondent_name=collected_fields.get("respondent_name"),
            respondent_mobile=collected_fields.get("respondent_mobile"),
            goods_services_description=collected_fields.get("goods_services_description"),
        )

        # Parse invoice_amount
        invoice_amount_str = collected_fields.get("invoice_amount", "")
        if invoice_amount_str:
            try:
                amount = float(re.sub(r'[^\d.]', '', str(invoice_amount_str)))
                dispute.invoice_amount = amount
                dispute.claimed_amount = amount
            except (ValueError, TypeError):
                pass

        db.add(dispute)
        await db.flush()
        await db.commit()
        await db.refresh(dispute)

        log.info(f"Created dispute {dispute.id} (case: {dispute.case_number})")

        # Dispatch WhatsApp followup as background task
        from src.tasks.dispatcher import dispatch_whatsapp_followup
        asyncio.create_task(
            dispatch_whatsapp_followup(
                user_id=user_id,
                dispute_id=str(dispute.id),
                seller_mobile=seller_mobile,
                collected_fields=collected_fields,
            )
        )

    except Exception as e:
        log.error(f"_handle_filing_complete failed: {e}")
