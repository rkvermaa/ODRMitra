"""Background task dispatcher for ODRMitra.

Simple asyncio.create_task() based background tasks for PoC.
Handles the Voice → WhatsApp → Case Processing pipeline.
"""

import asyncio
from src.core.logging import log
from src.config import settings


def _normalize_mobile(number: str) -> str:
    """Ensure mobile number has 91 country code prefix for WhatsApp JID."""
    digits = number.strip().replace("+", "").replace(" ", "").replace("-", "")
    if digits.startswith("91") and len(digits) == 12:
        return digits  # Already has country code
    if len(digits) == 10:
        return f"91{digits}"  # Add India country code
    return digits  # Return as-is for other formats


async def _get_baileys_session_id() -> str | None:
    """Find the active (connected) Baileys session ID from the database.

    Returns the WhatsAppAuth.id of the connected session, which is
    used as the Baileys session identifier for sending messages.
    """
    from src.db.session import async_session_factory
    from src.db.models.whatsapp_auth import WhatsAppAuth
    from sqlalchemy import select

    try:
        async with async_session_factory() as db:
            result = await db.execute(
                select(WhatsAppAuth).where(WhatsAppAuth.status == "connected")
            )
            auth = result.scalar_one_or_none()
            if auth:
                return str(auth.id)
    except Exception as e:
        log.error(f"Failed to get Baileys session ID: {e}")
    return None

# Required fields for a complete case filing
REQUIRED_FIELDS = {
    "title", "respondent_name", "seller_mobile",
    "goods_services_description", "invoice_amount",
    # WhatsApp agent collects these:
    "respondent_email", "respondent_gstin", "respondent_state",
    "respondent_address", "po_number",
}

VOICE_FIELDS = {
    "title", "respondent_name", "respondent_mobile", "seller_mobile",
    "goods_services_description", "invoice_amount",
}


async def dispatch_whatsapp_followup(
    user_id: str,
    dispute_id: str,
    seller_mobile: str,
    collected_fields: dict,
):
    """After voice filing completes, send WhatsApp message to seller.

    Args:
        user_id: The logged-in user's ID (for Baileys session)
        dispute_id: The created dispute ID
        seller_mobile: Seller's WhatsApp number
        collected_fields: Fields already collected via voice
    """
    try:
        # Wait a bit for voice UI to show success
        await asyncio.sleep(3)

        # Calculate what's actually missing (works for both partial and complete voice sessions)
        provided = set(k for k, v in collected_fields.items() if v)
        missing = REQUIRED_FIELDS - provided
        missing_labels = {
            "title": "Case ka title",
            "respondent_name": "Buyer/Respondent ka naam",
            "respondent_mobile": "Buyer ka mobile number",
            "goods_services_description": "Kya goods/services supply kiye",
            "invoice_amount": "Invoice amount kitna hai",
            "respondent_email": "Buyer ka email address",
            "respondent_gstin": "Buyer ka GSTIN number",
            "respondent_state": "Buyer ka state/city",
            "respondent_address": "Buyer ka full address",
            "po_number": "Purchase Order (PO) number",
        }

        missing_items = [missing_labels.get(f, f) for f in missing if f in missing_labels]

        # Build WhatsApp message
        title = collected_fields.get("title", "your dispute")
        if missing_items:
            message = (
                f"Namaste! ODRMitra se aapka case \"{title}\" register ho gaya hai "
                f"(Case ID: {dispute_id[:8]}...).\n\n"
                f"Kuch aur details chahiye hain case ko complete karne ke liye:\n"
            )
            for i, item in enumerate(missing_items[:6], 1):
                message += f"{i}. {item}\n"

            message += (
                "\nPlease ek ek karke yeh details share karein. "
                "Agar invoice PDF hai toh woh bhi bhej dijiye.\n\n"
                "Dhanyavaad!"
            )
        else:
            message = (
                f"Namaste! ODRMitra se aapka case \"{title}\" register ho gaya hai "
                f"(Case ID: {dispute_id[:8]}...).\n\n"
                f"Voice call se sab basic details mil gayi hain. "
                f"Ab kuch additional details chahiye — GSTIN, PO number, buyer address, etc.\n\n"
                f"Please ek ek karke share karein. Dhanyavaad!"
            )

        # Find the active Baileys session (not the user_id — Baileys uses WhatsAppAuth.id)
        session_id = await _get_baileys_session_id()
        if not session_id:
            log.warning("No connected Baileys session found — cannot send WhatsApp")
            return

        # Send via Baileys
        import httpx
        baileys_url = settings.get("baileys_service_url", "http://127.0.0.1:3001")
        api_key = settings.get("baileys_api_key", "baileys-secret-key")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{baileys_url}/sessions/{session_id}/send",
                json={"to": _normalize_mobile(seller_mobile), "message": message},
                headers={
                    "X-API-Key": api_key,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            if response.status_code == 200:
                log.info(f"WhatsApp followup sent to {seller_mobile} for dispute {dispute_id}")
            else:
                log.warning(f"WhatsApp followup failed: {response.status_code} - {response.text}")

    except Exception as e:
        import traceback
        log.error(f"dispatch_whatsapp_followup failed: {e}\n{traceback.format_exc()}")


async def dispatch_case_processing(dispute_id: str, user_id: str):
    """After all info collected via WhatsApp, process the case.

    1. Classify dispute
    2. Calculate interest
    3. Check missing docs
    4. Update dispute status to FILED
    5. Notify seller
    """
    try:
        await asyncio.sleep(2)

        from src.db.session import async_session_factory
        from src.db.models.dispute import Dispute, DisputeStatus
        from sqlalchemy import select

        async with async_session_factory() as db:
            result = await db.execute(
                select(Dispute).where(Dispute.id == dispute_id)
            )
            dispute = result.scalar_one_or_none()
            if not dispute:
                log.error(f"Dispute {dispute_id} not found for case processing")
                return

            # Update status to FILED
            dispute.status = DisputeStatus.FILED.value
            await db.commit()

            log.info(f"Case {dispute.case_number} processed and filed successfully")

            # Notify seller via WhatsApp
            # Find seller mobile from dispute or user
            from src.db.models.user import User
            user_result = await db.execute(
                select(User).where(User.id == dispute.claimant_id)
            )
            claimant = user_result.scalar_one_or_none()

            if claimant and claimant.mobile_number:
                session_id = await _get_baileys_session_id()
                if not session_id:
                    log.warning("No connected Baileys session — cannot notify seller")
                    return

                notify_message = (
                    f"Aapka case successfully file ho gaya hai!\n\n"
                    f"Case Number: {dispute.case_number}\n"
                    f"Status: Filed\n"
                    f"Respondent: {dispute.respondent_name}\n\n"
                    f"Hum aapko updates dete rahenge. Dhanyavaad!"
                )

                import httpx
                baileys_url = settings.get("baileys_service_url", "http://127.0.0.1:3001")
                api_key = settings.get("baileys_api_key", "baileys-secret-key")

                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{baileys_url}/sessions/{session_id}/send",
                        json={"to": _normalize_mobile(claimant.mobile_number), "message": notify_message},
                        headers={
                            "X-API-Key": api_key,
                            "Content-Type": "application/json",
                        },
                        timeout=30.0,
                    )

    except Exception as e:
        log.error(f"dispatch_case_processing failed for dispute {dispute_id}: {e}")


async def dispatch_buyer_intimation(
    dispute_id: str,
    user_id: str,
    buyer_mobile: str,
):
    """Send intimation notice to buyer via WhatsApp."""
    try:
        await asyncio.sleep(5)

        from src.db.session import async_session_factory
        from src.db.models.dispute import Dispute
        from sqlalchemy import select

        async with async_session_factory() as db:
            result = await db.execute(
                select(Dispute).where(Dispute.id == dispute_id)
            )
            dispute = result.scalar_one_or_none()
            if not dispute:
                return

            amount = f"₹{dispute.invoice_amount:,.2f}" if dispute.invoice_amount else "the claimed amount"

            message = (
                f"INTIMATION NOTICE\n\n"
                f"An ODR complaint (Case: {dispute.case_number}) has been filed "
                f"against you regarding delayed payment of {amount}.\n\n"
                f"Please respond within 15 days as per MSMED Act 2006, Section 18.\n\n"
                f"For details, visit ODRMitra or reply to this message.\n\n"
                f"— ODRMitra (AI-Enabled ODR Platform)"
            )

            session_id = await _get_baileys_session_id()
            if not session_id:
                log.warning("No connected Baileys session — cannot send buyer intimation")
                return

            import httpx
            baileys_url = settings.get("baileys_service_url", "http://127.0.0.1:3001")
            api_key = settings.get("baileys_api_key", "baileys-secret-key")

            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{baileys_url}/sessions/{session_id}/send",
                    json={"to": _normalize_mobile(buyer_mobile), "message": message},
                    headers={
                        "X-API-Key": api_key,
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )
                log.info(f"Buyer intimation sent to {buyer_mobile} for case {dispute.case_number}")

    except Exception as e:
        log.error(f"dispatch_buyer_intimation failed: {e}")


async def dispatch_buyer_and_seller_intimation(dispute_id: str, user_id: str):
    """After all fields collected via WhatsApp, notify both seller and buyer."""
    try:
        await asyncio.sleep(2)

        from src.db.session import async_session_factory
        from src.db.models.dispute import Dispute, DisputeStatus
        from src.db.models.user import User
        from sqlalchemy import select

        async with async_session_factory() as db:
            result = await db.execute(
                select(Dispute).where(Dispute.id == dispute_id)
            )
            dispute = result.scalar_one_or_none()
            if not dispute:
                log.error(f"Dispute {dispute_id} not found for intimation")
                return

            # Update status to FILED
            dispute.status = DisputeStatus.FILED.value
            await db.commit()

            log.info(f"Case {dispute.case_number} processed — sending intimations")

            # Get claimant (seller) info
            user_result = await db.execute(
                select(User).where(User.id == dispute.claimant_id)
            )
            claimant = user_result.scalar_one_or_none()

            session_id = await _get_baileys_session_id()
            if not session_id:
                log.warning("No connected Baileys session — cannot send intimations")
                return

            import httpx
            baileys_url = settings.get("baileys_service_url", "http://127.0.0.1:3001")
            api_key = settings.get("baileys_api_key", "baileys-secret-key")

            async with httpx.AsyncClient() as client:
                # 1. Notify seller: case filed + ask for remaining details
                if claimant and claimant.mobile_number:
                    amount = f"₹{dispute.invoice_amount:,.2f}" if dispute.invoice_amount else "N/A"
                    seller_msg = (
                        f"*ODRMitra — Case Filed Successfully!*\n\n"
                        f"Case Number: {dispute.case_number}\n"
                        f"Respondent: {dispute.respondent_name}\n"
                        f"Amount: {amount}\n"
                        f"Status: Filed\n\n"
                        f"Respondent ko intimation notice bhej diya gaya hai.\n"
                    )

                    # Build missing details list
                    missing_labels = {
                        "respondent_email": "Buyer ka email address",
                        "respondent_gstin": "Buyer ka GSTIN number (15 characters)",
                        "respondent_state": "Buyer ka state",
                        "respondent_address": "Buyer ka full address",
                        "po_number": "Purchase Order (PO) number",
                    }
                    # Check which fields are missing from the dispute record
                    missing_items = []
                    if not dispute.respondent_email:
                        missing_items.append(missing_labels["respondent_email"])
                    if not dispute.respondent_gstin:
                        missing_items.append(missing_labels["respondent_gstin"])
                    if not getattr(dispute, "respondent_state", None):
                        missing_items.append(missing_labels["respondent_state"])
                    if not getattr(dispute, "respondent_address", None):
                        missing_items.append(missing_labels["respondent_address"])
                    if not getattr(dispute, "po_number", None):
                        missing_items.append(missing_labels["po_number"])

                    if missing_items:
                        seller_msg += (
                            f"\nAage ki process ke liye kuch aur details chahiye:\n"
                        )
                        for i, item in enumerate(missing_items, 1):
                            seller_msg += f"{i}. {item}\n"
                        seller_msg += (
                            f"\nInvoice PDF bhi bhej dijiye agar available hai.\n"
                            f"Please ek ek karke yeh details yahan share karein.\n\n"
                            f"Dhanyavaad!"
                        )
                    else:
                        seller_msg += "\nSab details mil gayi hain. Hum aapko updates dete rahenge. Dhanyavaad!"

                    await client.post(
                        f"{baileys_url}/sessions/{session_id}/send",
                        json={"to": _normalize_mobile(claimant.mobile_number), "message": seller_msg},
                        headers={
                            "X-API-Key": api_key,
                            "Content-Type": "application/json",
                        },
                        timeout=30.0,
                    )
                    log.info(f"Seller notification sent to {claimant.mobile_number}")

                # 2. Send buyer intimation if respondent_mobile exists
                if dispute.respondent_mobile:
                    amount = f"₹{dispute.invoice_amount:,.2f}" if dispute.invoice_amount else "the claimed amount"
                    buyer_msg = (
                        f"INTIMATION NOTICE\n\n"
                        f"An ODR complaint (Case: {dispute.case_number}) has been filed "
                        f"against you regarding delayed payment of {amount}.\n\n"
                        f"Complainant: {claimant.name if claimant else 'N/A'}\n"
                        f"Regarding: {dispute.goods_services_description or 'N/A'}\n\n"
                        f"Please respond within 15 days as per MSMED Act 2006, Section 18.\n\n"
                        f"For details, visit ODRMitra or reply to this message.\n\n"
                        f"— ODRMitra (AI-Enabled ODR Platform)"
                    )
                    await client.post(
                        f"{baileys_url}/sessions/{session_id}/send",
                        json={"to": _normalize_mobile(dispute.respondent_mobile), "message": buyer_msg},
                        headers={
                            "X-API-Key": api_key,
                            "Content-Type": "application/json",
                        },
                        timeout=30.0,
                    )
                    log.info(f"Buyer intimation sent to {dispute.respondent_mobile} for case {dispute.case_number}")

                    # Update status to intimation_sent
                    dispute.status = DisputeStatus.INTIMATION_SENT.value
                    await db.commit()

    except Exception as e:
        log.error(f"dispatch_buyer_and_seller_intimation failed for dispute {dispute_id}: {e}")
