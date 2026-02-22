"""Seed demo users and sample disputes for ODRMitra."""

import asyncio
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.base import engine, async_session, Base
from src.db.models.user import User, UserRole
from src.db.models.dispute import Dispute, DisputeStatus, DisputeCategory
from src.db.models.invoice import Invoice


DEMO_USERS = [
    {
        "mobile_number": "7409210692",
        "name": "Rajesh Kumar",
        "email": "rajesh@kumar-enterprises.in",
        "role": UserRole.CLAIMANT.value,
        "organization_name": "Kumar Enterprises",
        "udyam_registration": "UDYAM-MH-01-0012345",
        "address": "Plot 45, MIDC Industrial Area, Pune, Maharashtra",
        "business_type": "small",
        "gstin": "27AABCK1234F1Z5",
        "pan": "AABCK1234F",
        "state": "Maharashtra",
        "district": "Pune",
        "pin_code": "411018",
    },
    {
        "mobile_number": "9876543211",
        "name": "Priya Sharma",
        "email": "priya@sharmatextiles.in",
        "role": UserRole.CLAIMANT.value,
        "organization_name": "Sharma Textiles Pvt Ltd",
        "udyam_registration": "UDYAM-RJ-02-0067890",
        "address": "18, Bhilwara Industrial Zone, Rajasthan",
        "business_type": "micro",
        "gstin": "08AABCS5678G1Z3",
        "pan": "AABCS5678G",
        "state": "Rajasthan",
        "district": "Bhilwara",
        "pin_code": "311001",
    },
    {
        "mobile_number": "9876543220",
        "name": "Vikram Singh",
        "email": "vikram@singhautomotive.in",
        "role": UserRole.RESPONDENT.value,
        "organization_name": "Singh Automotive Parts Ltd",
        "udyam_registration": None,
        "address": "Industrial Estate, Gurgaon, Haryana",
        "business_type": None,
        "gstin": "06AABCV9012H1Z7",
        "pan": "AABCV9012H",
        "state": "Haryana",
        "district": "Gurgaon",
        "pin_code": "122001",
    },
    {
        "mobile_number": "9876543230",
        "name": "Dr. Meera Patel",
        "email": "meera.patel@odr-conciliator.in",
        "role": UserRole.CONCILIATOR.value,
        "organization_name": "ODR Conciliation Services",
        "udyam_registration": None,
        "address": "Law Chambers, Connaught Place, New Delhi",
    },
    {
        "mobile_number": "9876543200",
        "name": "Admin User",
        "email": "admin@odrmitra.in",
        "role": UserRole.ADMIN.value,
        "organization_name": "ODRMitra Platform",
        "udyam_registration": None,
        "address": "ODRMitra HQ, New Delhi",
    },
]


async def seed():
    """Create tables and seed demo data."""
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        try:
            # Seed users — skip if already exists
            users = {}
            for user_data in DEMO_USERS:
                from sqlalchemy import select
                result = await db.execute(
                    select(User).where(User.mobile_number == user_data["mobile_number"])
                )
                existing = result.scalar_one_or_none()
                if existing:
                    print(f"  User {user_data['name']} already exists, skipping")
                    users[user_data["mobile_number"]] = existing
                else:
                    user = User(**user_data)
                    db.add(user)
                    users[user_data["mobile_number"]] = user
                    print(f"  Created user: {user_data['name']}")

            await db.flush()

            # Check if disputes already exist
            existing_disputes = await db.execute(
                select(Dispute).where(Dispute.case_number == "ODR-2026-0001")
            )
            if existing_disputes.scalar_one_or_none():
                print("  Disputes already exist, skipping")
                await db.commit()
                print("\nSeed complete (admin user added if new)!")
                return

            # Seed sample disputes
            claimant = users["7409210692"]
            respondent = users["9876543220"]

            dispute1 = Dispute(
                case_number="ODR-2026-0001",
                claimant_id=claimant.id,
                respondent_id=respondent.id,
                respondent_name="Singh Automotive Parts Ltd",
                respondent_mobile="9876543220",
                respondent_email="vikram@singhautomotive.in",
                respondent_category="company",
                respondent_gstin="06AABCV9012H1Z7",
                respondent_pan="AABCV9012H",
                respondent_state="Haryana",
                respondent_district="Gurgaon",
                respondent_pin_code="122001",
                respondent_address="Industrial Estate, Gurgaon, Haryana",
                title="Delayed payment for auto parts supply — Invoice #INV-2025-0456",
                description=(
                    "Supplied 500 units of brake pads and clutch plates to Singh Automotive "
                    "Parts Ltd on 15-Aug-2025. Invoice amount INR 8,50,000. Payment was due "
                    "within 45 days as per MSMED Act but remains unpaid after 150+ days."
                ),
                category=DisputeCategory.DELAYED_PAYMENT.value,
                claimed_amount=935000.00,
                invoice_amount=850000.00,
                amount_received=0.00,
                principal_amount=850000.00,
                interest_rate=24.00,
                interest_start_date=date(2025, 9, 29),
                interest_amount=85000.00,
                total_amount_due=935000.00,
                po_number="PO-2025-0456",
                po_date=date(2025, 7, 20),
                payment_terms="45 days from invoice date as per MSMED Act Section 15",
                goods_services_description="500 units brake pads (Part# BP-200) + 200 units clutch plates (Part# CP-100)",
                cause_of_action=(
                    "The respondent placed PO-2025-0456 on 20-Jul-2025 for auto parts. Goods were "
                    "delivered on 15-Aug-2025 and accepted without objection. Invoice INV-2025-0456 "
                    "for INR 8,50,000 was raised the same day with 45-day payment terms. Despite "
                    "multiple follow-ups, no payment has been received as of date, violating Section "
                    "15 of MSMED Act 2006."
                ),
                relief_sought=(
                    "1. Payment of principal amount INR 8,50,000\n"
                    "2. Interest under Section 16 of MSMED Act 2006 at 3x RBI bank rate (24% p.a.)\n"
                    "3. Costs of the proceedings"
                ),
                correspondence_summary="Email reminders sent on 01-Oct-2025, 15-Nov-2025, 01-Jan-2026. No response received.",
                buyer_objections=[],
                msefc_council="MSEFC Maharashtra",
                status=DisputeStatus.DGP.value,
            )

            dispute2 = Dispute(
                case_number="ODR-2026-0002",
                claimant_id=users["9876543211"].id,
                respondent_name="Metro Fashion House",
                respondent_mobile="9876500000",
                respondent_email="accounts@metrofashion.in",
                respondent_category="company",
                respondent_state="Delhi",
                respondent_district="South Delhi",
                respondent_pin_code="110017",
                respondent_address="45, Nehru Place, New Delhi",
                title="Non-payment for textile consignment — Order #PO-2025-789",
                description=(
                    "Delivered 2000 meters of cotton fabric to Metro Fashion House on "
                    "01-Oct-2025. Total amount INR 3,20,000. No payment received despite "
                    "multiple reminders."
                ),
                category=DisputeCategory.NON_PAYMENT.value,
                claimed_amount=345000.00,
                invoice_amount=320000.00,
                amount_received=0.00,
                principal_amount=320000.00,
                interest_rate=24.00,
                interest_start_date=date(2025, 11, 15),
                interest_amount=25000.00,
                total_amount_due=345000.00,
                po_number="PO-2025-789",
                po_date=date(2025, 9, 15),
                payment_terms="45 days from delivery",
                goods_services_description="2000m premium cotton fabric (Grade A, 60-count)",
                cause_of_action=(
                    "The respondent ordered 2000m of premium cotton fabric via PO-2025-789. "
                    "Goods were delivered on 01-Oct-2025 and accepted. Invoice for INR 3,20,000 "
                    "was raised. Payment was due by 15-Nov-2025. No payment has been received."
                ),
                relief_sought=(
                    "1. Payment of principal INR 3,20,000\n"
                    "2. Compound interest under Section 16 MSMED Act\n"
                    "3. Costs of proceedings"
                ),
                correspondence_summary="Demand notice sent via registered post on 01-Dec-2025. Follow-up email on 15-Jan-2026.",
                msefc_council="MSEFC Delhi",
                status=DisputeStatus.FILED.value,
            )

            db.add_all([dispute1, dispute2])
            await db.flush()

            # Seed invoices
            inv1 = Invoice(
                dispute_id=dispute1.id,
                invoice_number="INV-2025-0456",
                invoice_date=date(2025, 8, 15),
                invoice_amount=850000.00,
                acceptance_date=date(2025, 8, 15),
                amount_received=0.00,
                last_payment_date=None,
                balance_due=850000.00,
            )
            inv2 = Invoice(
                dispute_id=dispute2.id,
                invoice_number="INV-2025-0789",
                invoice_date=date(2025, 10, 1),
                invoice_amount=320000.00,
                acceptance_date=date(2025, 10, 1),
                amount_received=0.00,
                last_payment_date=None,
                balance_due=320000.00,
            )
            db.add_all([inv1, inv2])

            await db.commit()

            print("Demo data seeded successfully!")
            print(f"  Users: {len(DEMO_USERS)}")
            print(f"  Disputes: 2")
            print(f"  Invoices: 2")
            print()
            print("Login credentials (mobile numbers):")
            for u in DEMO_USERS:
                print(f"  {u['name']:20s} — {u['mobile_number']} ({u['role']})")

        except Exception as e:
            await db.rollback()
            print(f"Error seeding data: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed())
