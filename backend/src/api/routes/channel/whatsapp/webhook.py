"""WhatsApp webhook handler — Baileys Service integration for ODRMitra

Handles incoming messages from WhatsApp users via the Baileys service.
The Baileys session ID is the WhatsAppAuth.id (bot_id), NOT the user_id.
We resolve bot_id → bot record → find/create sender user → process message.
"""

import asyncio
import json
import re
import uuid
from typing import Annotated

import httpx
from fastapi import APIRouter, Request, HTTPException, status, Header
from sqlalchemy import select

from src.config import settings
from src.core.logging import log
from src.db.session import get_db
from src.db.models.user import User, UserRole
from src.db.models.whatsapp_auth import WhatsAppAuth
from src.db.models.dispute import Dispute, DisputeStatus

router = APIRouter()


def get_baileys_api_key() -> str:
    """Get expected API key for Baileys service."""
    return settings.get("baileys_api_key", "baileys-secret-key")


def verify_api_key(x_api_key: str | None) -> bool:
    """Verify the API key from Baileys service."""
    return x_api_key == get_baileys_api_key()


async def resolve_baileys_session_id(db, session_id: str) -> WhatsAppAuth | None:
    """Resolve a Baileys session ID to a WhatsAppAuth record.

    The session ID could be:
    1. WhatsAppAuth.id (admin bot flow — new)
    2. User.id (original per-user flow — legacy)
    """
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        return None

    # Try as WhatsAppAuth.id first (admin bot flow)
    result = await db.execute(
        select(WhatsAppAuth).where(WhatsAppAuth.id == sid)
    )
    auth = result.scalar_one_or_none()
    if auth:
        return auth

    # Fallback: try as user_id (original flow)
    result = await db.execute(
        select(WhatsAppAuth).where(WhatsAppAuth.user_id == sid)
    )
    auth = result.scalar_one_or_none()
    return auth


async def find_or_create_sender_user(db, phone_number: str, sender_name: str) -> User:
    """Find an existing user by phone number or create a new one."""
    # Clean phone number (remove leading + or country code variations)
    clean_number = phone_number.lstrip("+")

    result = await db.execute(
        select(User).where(User.mobile_number == clean_number)
    )
    user = result.scalar_one_or_none()

    if user:
        return user

    # Also try with/without country code prefix "91"
    if clean_number.startswith("91") and len(clean_number) > 10:
        short_number = clean_number[2:]
        result = await db.execute(
            select(User).where(User.mobile_number == short_number)
        )
        user = result.scalar_one_or_none()
        if user:
            return user
    elif len(clean_number) == 10:
        long_number = "91" + clean_number
        result = await db.execute(
            select(User).where(User.mobile_number == long_number)
        )
        user = result.scalar_one_or_none()
        if user:
            return user

    # Create new user for this WhatsApp sender
    new_user = User(
        mobile_number=clean_number,
        name=sender_name or f"WhatsApp User {clean_number[-4:]}",
        role=UserRole.CLAIMANT.value,
        whatsapp_connected=True,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    log.info(f"Created new user for WhatsApp sender: {clean_number} ({sender_name})")
    return new_user


@router.post("/message")
async def handle_baileys_message(
    request: Request,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
):
    """Handle incoming messages from Baileys service."""
    if not verify_api_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    body = await request.json()
    log.info(f"Baileys webhook received: {body}")

    baileys_session_id = body.get("userId")  # This is the Baileys session ID (bot_id or user_id)
    sender = body.get("from") or body.get("sender", "")
    sender_name = body.get("fromName") or body.get("senderName") or sender
    sender_jid = body.get("fromJid", "")
    message_text = body.get("message", "")

    if not baileys_session_id or not sender or not message_text:
        log.warning("Invalid Baileys payload: missing required fields")
        return {"status": "ignored", "reason": "missing required fields"}

    log.info(f"WhatsApp message from {sender_name} ({sender}) via session {baileys_session_id}: {message_text[:50]}...")

    try:
        response_text = await process_whatsapp_message(
            baileys_session_id=baileys_session_id,
            sender_number=sender,
            sender_name=sender_name,
            message_text=message_text,
        )

        if response_text:
            reply_to = sender_jid if sender_jid else sender
            await send_whatsapp_response(
                baileys_session_id=baileys_session_id,
                to_number=reply_to,
                message=response_text,
            )

        return {"status": "processed"}

    except Exception as e:
        log.exception(f"Failed to process WhatsApp message: {e}")
        return {"status": "error", "reason": str(e)}


@router.post("/status")
async def handle_baileys_status(
    request: Request,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
):
    """Handle status updates from Baileys service."""
    if not verify_api_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    body = await request.json()
    log.info(f"Baileys status webhook: {body}")

    baileys_session_id = body.get("userId")
    event = body.get("event")
    phone_number = body.get("phoneNumber")

    if not baileys_session_id or not event:
        return {"status": "ignored", "reason": "missing required fields"}

    await update_bot_status(baileys_session_id, event == "connected", phone_number)

    return {"status": "received"}


async def update_bot_status(baileys_session_id: str, connected: bool, phone_number: str | None = None):
    """Update WhatsApp bot status in database."""
    try:
        async for db in get_db():
            auth = await resolve_baileys_session_id(db, baileys_session_id)

            if auth:
                auth.status = "connected" if connected else "disconnected"
                if phone_number:
                    auth.phone_number = phone_number
                log.info(f"Updated bot {auth.id} status: connected={connected}, phone={phone_number}")
            else:
                log.warning(f"No WhatsAppAuth found for session {baileys_session_id}")

            await db.commit()
            break
    except Exception as e:
        log.error(f"Failed to update bot status: {e}")


async def send_whatsapp_response(baileys_session_id: str, to_number: str, message: str) -> bool:
    """Send a WhatsApp message via Baileys service."""
    try:
        baileys_url = settings.get("baileys_service_url", "http://127.0.0.1:3001")
        api_key = settings.get("baileys_api_key", "baileys-secret-key")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{baileys_url}/sessions/{baileys_session_id}/send",
                json={"to": to_number, "message": message},
                headers={
                    "X-API-Key": api_key,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return True
    except Exception as e:
        log.error(f"Failed to send WhatsApp response to {to_number}: {e}")
        return False


async def process_whatsapp_message(
    baileys_session_id: str,
    sender_number: str,
    sender_name: str,
    message_text: str,
) -> str | None:
    """
    Process an incoming WhatsApp message with the ODRMitra agent.

    Flow:
    1. Resolve baileys_session_id → WhatsAppAuth record (the bot)
    2. Find or create a User for the sender (by phone number)
    3. Create/get chat session for the sender
    4. Process with AgentEngine in context of the sender
    5. Return cleaned response text
    """
    from src.agent.engine import AgentEngine
    from src.chat.service import ChatService
    from src.db.models.message import MessageRole

    response_text: str | None = None

    async for db in get_db():
        try:
            # Resolve the bot
            auth = await resolve_baileys_session_id(db, baileys_session_id)
            if not auth:
                log.warning(f"No bot found for Baileys session {baileys_session_id}")
                response_text = "Sorry, this bot is not configured. Please contact support."
                break

            # Find or create user for the sender
            sender_user = await find_or_create_sender_user(db, sender_number, sender_name)
            sender_user_id = str(sender_user.id)

            chat = ChatService(db)

            # Look up sender's latest dispute to link the session
            latest_dispute_result = await db.execute(
                select(Dispute).where(Dispute.claimant_id == sender_user_id)
                .order_by(Dispute.created_at.desc()).limit(1)
            )
            linked_dispute = latest_dispute_result.scalar_one_or_none()
            linked_dispute_id = str(linked_dispute.id) if linked_dispute else None

            # Get or create WhatsApp session for this sender
            session = await chat.get_or_create_session(
                user_id=sender_user_id,
                channel="whatsapp",
                dispute_id=linked_dispute_id,
            )

            log.info(f"Using session: {session.id} for WhatsApp sender {sender_number} (user {sender_user_id})")

            # Save user message
            await chat.save_message(
                session_id=session.id,
                role=MessageRole.USER.value,
                content=message_text,
                channel_source="whatsapp",
            )

            # Get conversation history
            history = await chat.get_history_for_agent(session.id)

            # Process with agent — will auto-discover appropriate skill
            agent = AgentEngine(
                user_id=sender_user_id,
                session_id=str(session.id),
                dispute_id=linked_dispute_id,
                channel="whatsapp",
            )

            agent_result = await agent.process_message(
                user_message=message_text,
                history=history,
            )

            response_text = agent_result["content"]

            # Clean response — remove [FIELDS] and [WA_COLLECTION_COMPLETE] tags
            clean_response = re.sub(r'\[FIELDS\][\s\S]*?\[/FIELDS\]', '', response_text).strip()
            clean_response = clean_response.replace('[WA_COLLECTION_COMPLETE]', '').strip()
            clean_response = clean_response.replace('[FILING_COMPLETE]', '').strip()

            # Save agent response
            await chat.save_message(
                session_id=session.id,
                role=MessageRole.ASSISTANT.value,
                content=response_text,
                input_tokens=agent_result.get("usage", {}).get("input_tokens"),
                output_tokens=agent_result.get("usage", {}).get("output_tokens"),
            )

            await db.commit()

            # Check if collection is complete — trigger case processing + intimation
            if '[WA_COLLECTION_COMPLETE]' in response_text or '[FILING_COMPLETE]' in response_text:
                log.info(f"WhatsApp collection complete for sender {sender_number}")

                # Extract fields from the response and update dispute
                if linked_dispute:
                    fields_matches = re.findall(r'\[FIELDS\]([\s\S]*?)\[/FIELDS\]', response_text)
                    wa_fields: dict = {}
                    for match in fields_matches:
                        try:
                            wa_fields.update(json.loads(match))
                        except json.JSONDecodeError:
                            pass

                    # Update dispute with WhatsApp-collected fields
                    field_map = {
                        "respondent_email": "respondent_email",
                        "respondent_gstin": "respondent_gstin",
                        "respondent_state": "respondent_state",
                        "respondent_district": "respondent_district",
                        "respondent_pin_code": "respondent_pin_code",
                        "respondent_address": "respondent_address",
                        "respondent_mobile": "respondent_mobile",
                        "respondent_name": "respondent_name",
                        "po_number": "po_number",
                        "cause_of_action": "cause_of_action",
                        "seller_gstin": "respondent_pan",  # seller's GSTIN stored as claimant info
                        "goods_services_description": "goods_services_description",
                    }
                    for src_field, dest_field in field_map.items():
                        val = wa_fields.get(src_field)
                        if val and not getattr(linked_dispute, dest_field, None):
                            setattr(linked_dispute, dest_field, val)

                    linked_dispute.status = DisputeStatus.FILED.value
                    await db.commit()
                    log.info(f"Updated dispute {linked_dispute.id} with WhatsApp fields")

                    # Dispatch intimation to both parties
                    from src.tasks.dispatcher import dispatch_buyer_and_seller_intimation
                    asyncio.create_task(
                        dispatch_buyer_and_seller_intimation(
                            dispute_id=str(linked_dispute.id),
                            user_id=sender_user_id,
                        )
                    )

            response_text = clean_response

        except Exception as e:
            log.exception(f"Error processing WhatsApp message: {e}")
            response_text = "Sorry, I encountered an error. Please try again."

        break

    return response_text
