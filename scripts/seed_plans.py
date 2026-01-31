"""Seed initial plans into the database.

Run with: python -m scripts.seed_plans
"""
from sqlalchemy.orm import Session

from src.core.database import SessionLocal
from src.models.billing import Plan


PLANS = [
    {
        "id": "price_inboxpilot_monthly",
        "stripe_product_id": "prod_inboxpilot",
        "name": "InboxPilot",
        "description": "Email triage and response drafting agent",
        "price_cents": 2900,
        "interval": "month",
        "agents_included": ["inbox"],
        "limits": {
            "emails_per_month": 500,
            "invoices_per_month": 0,
            "meetings_per_month": 0,
        },
        "is_active": True,
    },
    {
        "id": "price_invoicepilot_monthly",
        "stripe_product_id": "prod_invoicepilot",
        "name": "InvoicePilot",
        "description": "Invoice detection and follow-up agent",
        "price_cents": 1900,
        "interval": "month",
        "agents_included": ["invoice"],
        "limits": {
            "emails_per_month": 0,
            "invoices_per_month": 50,
            "meetings_per_month": 0,
        },
        "is_active": True,
    },
    {
        "id": "price_meetingpilot_monthly",
        "stripe_product_id": "prod_meetingpilot",
        "name": "MeetingPilot",
        "description": "Meeting prep and follow-up agent",
        "price_cents": 1900,
        "interval": "month",
        "agents_included": ["meeting"],
        "limits": {
            "emails_per_month": 0,
            "invoices_per_month": 0,
            "meetings_per_month": 30,
        },
        "is_active": True,
    },
    {
        "id": "price_bundle_monthly",
        "stripe_product_id": "prod_bundle",
        "name": "FounderPilot Bundle",
        "description": "All three agents at a discounted price",
        "price_cents": 4900,
        "interval": "month",
        "agents_included": ["inbox", "invoice", "meeting"],
        "limits": {
            "emails_per_month": 500,
            "invoices_per_month": 50,
            "meetings_per_month": 30,
        },
        "is_active": True,
    },
]


def seed_plans(db: Session) -> None:
    """Seed plans into the database."""
    for plan_data in PLANS:
        existing = db.query(Plan).filter(Plan.id == plan_data["id"]).first()
        if existing:
            # Update existing plan
            for key, value in plan_data.items():
                setattr(existing, key, value)
            print(f"Updated plan: {plan_data['name']}")
        else:
            # Create new plan
            plan = Plan(**plan_data)
            db.add(plan)
            print(f"Created plan: {plan_data['name']}")

    db.commit()
    print(f"\nSeeded {len(PLANS)} plans successfully!")


def main():
    """Main entry point."""
    print("Seeding plans into database...\n")
    db = SessionLocal()
    try:
        seed_plans(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
