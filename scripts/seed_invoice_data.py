"""Seed test data for InvoicePilot development.

Usage:
    python scripts/seed_invoice_data.py
"""
import asyncio
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import async_session
from src.models.invoice import Invoice, InvoiceReminder, InvoiceAction
from src.models.user import User


async def seed_invoice_data():
    """Seed test invoice data for development."""
    async with async_session() as session:
        # Get or create a test tenant
        test_tenant = await session.execute(
            "SELECT id FROM users WHERE email = 'test@founderpilot.dev' LIMIT 1"
        )
        tenant_id = test_tenant.scalar()

        if not tenant_id:
            print("No test tenant found. Please create a user first.")
            return

        print(f"Using tenant: {tenant_id}")

        # Create test invoices
        invoices_data = [
            {
                "tenant_id": tenant_id,
                "gmail_message_id": f"test-msg-{uuid.uuid4().hex[:8]}",
                "invoice_number": "INV-2026-001",
                "client_name": "Acme Corp",
                "client_email": "billing@acmecorp.com",
                "amount_total": Decimal("5000.00"),
                "amount_paid": Decimal("0.00"),
                "currency": "USD",
                "issue_date": date.today() - timedelta(days=20),
                "due_date": date.today() + timedelta(days=10),
                "status": "pending",
                "confidence": Decimal("0.95"),
                "pdf_url": "/storage/pdfs/invoice-001.pdf",
                "notes": "Website redesign project",
            },
            {
                "tenant_id": tenant_id,
                "gmail_message_id": f"test-msg-{uuid.uuid4().hex[:8]}",
                "invoice_number": "INV-2026-002",
                "client_name": "TechStart Inc",
                "client_email": "ap@techstart.io",
                "amount_total": Decimal("3500.00"),
                "amount_paid": Decimal("0.00"),
                "currency": "USD",
                "issue_date": date.today() - timedelta(days=10),
                "due_date": date.today() - timedelta(days=3),
                "status": "overdue",
                "confidence": Decimal("0.88"),
                "pdf_url": "/storage/pdfs/invoice-002.pdf",
                "notes": "Monthly consulting retainer",
            },
            {
                "tenant_id": tenant_id,
                "gmail_message_id": f"test-msg-{uuid.uuid4().hex[:8]}",
                "invoice_number": "INV-2026-003",
                "client_name": "Global Ventures Ltd",
                "client_email": "finance@globalventures.com",
                "amount_total": Decimal("12000.00"),
                "amount_paid": Decimal("6000.00"),
                "currency": "EUR",
                "issue_date": date.today() - timedelta(days=30),
                "due_date": date.today() - timedelta(days=7),
                "status": "partial",
                "confidence": Decimal("0.92"),
                "pdf_url": "/storage/pdfs/invoice-003.pdf",
                "notes": "App development - Phase 1",
            },
            {
                "tenant_id": tenant_id,
                "gmail_message_id": f"test-msg-{uuid.uuid4().hex[:8]}",
                "invoice_number": "INV-2026-004",
                "client_name": "Startup Hub",
                "client_email": "payments@startuphub.co",
                "amount_total": Decimal("2500.00"),
                "amount_paid": Decimal("2500.00"),
                "currency": "GBP",
                "issue_date": date.today() - timedelta(days=45),
                "due_date": date.today() - timedelta(days=15),
                "status": "paid",
                "confidence": Decimal("0.97"),
                "pdf_url": "/storage/pdfs/invoice-004.pdf",
                "notes": "Workshop facilitation",
            },
            {
                "tenant_id": tenant_id,
                "gmail_message_id": f"test-msg-{uuid.uuid4().hex[:8]}",
                "invoice_number": "INV-2026-005",
                "client_name": "Innovation Labs",
                "client_email": "accounts@innovationlabs.net",
                "amount_total": Decimal("7500.00"),
                "amount_paid": Decimal("0.00"),
                "currency": "USD",
                "issue_date": date.today() - timedelta(days=5),
                "due_date": date.today() + timedelta(days=25),
                "status": "detected",
                "confidence": Decimal("0.72"),
                "pdf_url": "/storage/pdfs/invoice-005.pdf",
                "notes": "Low confidence - needs confirmation",
            },
        ]

        created_invoices = []
        for invoice_data in invoices_data:
            invoice = Invoice(**invoice_data)
            session.add(invoice)
            created_invoices.append(invoice)

            # Add creation action
            action = InvoiceAction(
                invoice_id=invoice.id,
                action_type="detected",
                actor="agent",
                details={
                    "source": "gmail",
                    "confidence": float(invoice.confidence),
                },
                timestamp=datetime.utcnow() - timedelta(days=2),
            )
            session.add(action)

        await session.commit()
        print(f"Created {len(created_invoices)} test invoices")

        # Create reminders for overdue invoice
        overdue_invoice = created_invoices[1]  # TechStart Inc
        reminder = InvoiceReminder(
            invoice_id=overdue_invoice.id,
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            type="post_due_3d",
            status="pending",
            draft_message=(
                "Hi TechStart team,\n\n"
                "I hope this email finds you well. I wanted to follow up on "
                f"invoice {overdue_invoice.invoice_number} for ${overdue_invoice.amount_total} "
                "which was due on {overdue_invoice.due_date.strftime('%B %d, %Y')}.\n\n"
                "Could you please confirm when we can expect payment? "
                "If there are any issues, I'm happy to discuss.\n\n"
                "Best regards"
            ),
        )
        session.add(reminder)

        # Create reminder action
        reminder_action = InvoiceAction(
            invoice_id=overdue_invoice.id,
            action_type="reminder_scheduled",
            actor="agent",
            details={
                "reminder_type": "post_due_3d",
                "scheduled_at": reminder.scheduled_at.isoformat(),
            },
            timestamp=datetime.utcnow(),
        )
        session.add(reminder_action)

        await session.commit()
        print("Created test reminder for overdue invoice")

        # Add payment action for paid invoice
        paid_invoice = created_invoices[3]  # Startup Hub
        payment_action = InvoiceAction(
            invoice_id=paid_invoice.id,
            action_type="marked_paid",
            actor=str(tenant_id),
            details={
                "amount_paid": float(paid_invoice.amount_paid),
                "payment_date": (date.today() - timedelta(days=5)).isoformat(),
                "payment_method": "bank_transfer",
            },
            timestamp=datetime.utcnow() - timedelta(days=5),
        )
        session.add(payment_action)

        await session.commit()
        print("Added payment action for paid invoice")

        print("\n✅ Seed data created successfully!")
        print("\nInvoice Summary:")
        print(f"  - Pending: 1 invoice (Acme Corp - ${invoices_data[0]['amount_total']})")
        print(f"  - Overdue: 1 invoice (TechStart Inc - ${invoices_data[1]['amount_total']})")
        print(f"  - Partial: 1 invoice (Global Ventures - €{invoices_data[2]['amount_total']})")
        print(f"  - Paid: 1 invoice (Startup Hub - £{invoices_data[3]['amount_total']})")
        print(f"  - Detected (low confidence): 1 invoice (Innovation Labs - ${invoices_data[4]['amount_total']})")


if __name__ == "__main__":
    asyncio.run(seed_invoice_data())
