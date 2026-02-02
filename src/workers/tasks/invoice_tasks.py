"""Celery tasks for InvoicePilot operations."""
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def scan_invoices_for_all_tenants(self) -> Dict:
    """
    Scan Gmail inboxes for new invoices across all tenants.

    Runs periodically (every 5 minutes) to detect new invoice emails.
    Uses the InvoicePilotAgent to scan sent emails and extract invoice data.

    Returns:
        Dict with scan statistics including tenants processed, invoices detected, and errors
    """
    import asyncio
    from src.core.database import get_async_session
    from src.services.invoice_service import InvoiceService
    from src.agents.invoice_pilot import InvoicePilotAgent

    async def _scan_all() -> Dict:
        """Async function to scan all tenants."""
        stats = {
            "tenants_processed": 0,
            "invoices_detected": 0,
            "invoices_confirmed": 0,
            "errors": 0,
            "start_time": datetime.utcnow().isoformat(),
        }

        async with get_async_session() as db:
            service = InvoiceService(db)

            # Get all tenants with InvoicePilot enabled
            # TODO: Add method to get enabled tenants from settings/config
            # For now, get all tenants that have invoice settings
            try:
                enabled_tenants = await service.get_enabled_tenants()
            except Exception as e:
                logger.error(f"Failed to fetch enabled tenants: {e}")
                stats["errors"] += 1
                return stats

            for tenant_id in enabled_tenants:
                try:
                    logger.info(f"Scanning invoices for tenant {tenant_id}")

                    # Initialize agent for this tenant
                    agent = InvoicePilotAgent(
                        db=db,
                        tenant_id=tenant_id,
                    )

                    # Scan inbox for new invoices
                    result = await agent.scan_inbox(
                        lookback_days=1,  # Only scan last 24 hours for periodic scans
                    )

                    stats["tenants_processed"] += 1
                    stats["invoices_detected"] += result.get("invoices_detected", 0)
                    stats["invoices_confirmed"] += result.get("invoices_confirmed", 0)

                    logger.info(
                        f"Tenant {tenant_id}: detected {result.get('invoices_detected', 0)} invoices, "
                        f"confirmed {result.get('invoices_confirmed', 0)}"
                    )

                except Exception as e:
                    logger.error(f"Error scanning invoices for tenant {tenant_id}: {e}", exc_info=True)
                    stats["errors"] += 1

            stats["end_time"] = datetime.utcnow().isoformat()
            return stats

    # Run async function
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(_scan_all())

    logger.info(
        f"Invoice scan complete: {result['tenants_processed']} tenants, "
        f"{result['invoices_detected']} detected, {result['errors']} errors"
    )

    return result


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def scan_invoices_for_tenant(self, tenant_id: int, lookback_days: int = 30) -> Dict:
    """
    Scan Gmail inbox for invoices for a specific tenant.

    Used for manual/on-demand scans or initial setup.

    Args:
        tenant_id: The tenant ID to scan
        lookback_days: How many days back to scan (default 30)

    Returns:
        Dict with scan results
    """
    import asyncio
    from src.core.database import get_async_session
    from src.agents.invoice_pilot import InvoicePilotAgent

    async def _scan_tenant() -> Dict:
        """Async function to scan a single tenant."""
        async with get_async_session() as db:
            agent = InvoicePilotAgent(
                db=db,
                tenant_id=tenant_id,
            )

            result = await agent.scan_inbox(lookback_days=lookback_days)

            logger.info(
                f"Manual scan for tenant {tenant_id}: "
                f"detected {result.get('invoices_detected', 0)} invoices"
            )

            return result

    # Run async function
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_scan_tenant())


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def process_invoice_detection(
    self,
    tenant_id: int,
    gmail_message_id: str,
    pdf_url: str,
) -> Dict:
    """
    Process a single invoice detection.

    Extracts data from an invoice PDF using LLM and stores it.

    Args:
        tenant_id: The tenant ID
        gmail_message_id: Gmail message ID containing the invoice
        pdf_url: URL or path to the PDF file

    Returns:
        Dict with extraction result
    """
    import asyncio
    from src.core.database import get_async_session
    from src.agents.invoice_pilot import InvoicePilotAgent

    async def _process_detection() -> Dict:
        """Async function to process detection."""
        async with get_async_session() as db:
            agent = InvoicePilotAgent(
                db=db,
                tenant_id=tenant_id,
            )

            result = await agent.extract_and_store_invoice(
                gmail_message_id=gmail_message_id,
                pdf_url=pdf_url,
            )

            return result

    # Run async function
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_process_detection())


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def check_invoice_reminders(self) -> Dict:
    """
    Check for invoice reminders that are due and send them.

    Runs daily at 9am to check all tenants for reminders that need to be sent.
    Drafts reminder messages, awaits approval, and sends approved reminders.

    Returns:
        Dict with reminder processing statistics
    """
    import asyncio
    from src.core.database import get_async_session
    from src.services.invoice_service import InvoiceService
    from src.agents.invoice_pilot import InvoicePilotAgent

    async def _check_all_reminders() -> Dict:
        """Async function to check reminders for all tenants."""
        stats = {
            "tenants_processed": 0,
            "reminders_scheduled": 0,
            "reminders_sent": 0,
            "errors": 0,
            "start_time": datetime.utcnow().isoformat(),
        }

        async with get_async_session() as db:
            service = InvoiceService(db)

            # Get all tenants with InvoicePilot enabled
            try:
                enabled_tenants = await service.get_enabled_tenants()
            except Exception as e:
                logger.error(f"Failed to fetch enabled tenants: {e}")
                stats["errors"] += 1
                return stats

            for tenant_id in enabled_tenants:
                try:
                    logger.info(f"Checking reminders for tenant {tenant_id}")

                    # Initialize agent for this tenant
                    agent = InvoicePilotAgent(
                        db=db,
                        tenant_id=tenant_id,
                    )

                    # Check and process due reminders
                    result = await agent.check_reminders_due()

                    stats["tenants_processed"] += 1
                    stats["reminders_scheduled"] += result.get("reminders_scheduled", 0)
                    stats["reminders_sent"] += result.get("reminders_sent", 0)

                    logger.info(
                        f"Tenant {tenant_id}: scheduled {result.get('reminders_scheduled', 0)} reminders, "
                        f"sent {result.get('reminders_sent', 0)}"
                    )

                except Exception as e:
                    logger.error(f"Error checking reminders for tenant {tenant_id}: {e}", exc_info=True)
                    stats["errors"] += 1

            stats["end_time"] = datetime.utcnow().isoformat()
            return stats

    # Run async function
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(_check_all_reminders())

    logger.info(
        f"Reminder check complete: {result['tenants_processed']} tenants, "
        f"{result['reminders_sent']} sent, {result['errors']} errors"
    )

    return result


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def check_problem_patterns(self) -> Dict:
    """
    Check for problem patterns and escalate to founders.

    Runs daily at 10am to detect invoices with 3+ reminders and no payment.
    Escalates morose clients to Slack for founder attention.

    Returns:
        Dict with escalation statistics
    """
    import asyncio
    from src.core.database import get_async_session
    from src.services.invoice_service import InvoiceService
    from src.agents.invoice_pilot import InvoicePilotAgent

    async def _check_all_problems() -> Dict:
        """Async function to check problem patterns for all tenants."""
        stats = {
            "tenants_processed": 0,
            "problems_detected": 0,
            "escalations_sent": 0,
            "errors": 0,
            "start_time": datetime.utcnow().isoformat(),
        }

        async with get_async_session() as db:
            service = InvoiceService(db)

            # Get all tenants with InvoicePilot enabled
            try:
                enabled_tenants = await service.get_enabled_tenants()
            except Exception as e:
                logger.error(f"Failed to fetch enabled tenants: {e}")
                stats["errors"] += 1
                return stats

            for tenant_id in enabled_tenants:
                try:
                    logger.info(f"Checking problem patterns for tenant {tenant_id}")

                    # Initialize agent for this tenant
                    agent = InvoicePilotAgent(
                        db=db,
                        tenant_id=tenant_id,
                    )

                    # Detect and escalate problem patterns
                    result = await agent.detect_problem_pattern()

                    stats["tenants_processed"] += 1
                    stats["problems_detected"] += result.get("problems_detected", 0)
                    stats["escalations_sent"] += result.get("escalations_sent", 0)

                    logger.info(
                        f"Tenant {tenant_id}: detected {result.get('problems_detected', 0)} problems, "
                        f"sent {result.get('escalations_sent', 0)} escalations"
                    )

                except Exception as e:
                    logger.error(f"Error checking problems for tenant {tenant_id}: {e}", exc_info=True)
                    stats["errors"] += 1

            stats["end_time"] = datetime.utcnow().isoformat()
            return stats

    # Run async function
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(_check_all_problems())

    logger.info(
        f"Problem pattern check complete: {result['tenants_processed']} tenants, "
        f"{result['problems_detected']} detected, {result['errors']} errors"
    )

    return result
