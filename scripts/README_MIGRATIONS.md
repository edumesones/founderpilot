# Database Migrations Guide

## Running Migrations

### Using Docker Compose (Recommended)

1. Start the database:
```bash
docker-compose up -d postgres
```

2. Run migrations:
```bash
docker-compose exec api alembic upgrade head
```

3. Verify current migration:
```bash
docker-compose exec api alembic current
```

### Local Development

1. Ensure PostgreSQL is running and DATABASE_URL is set in .env

2. Run migrations:
```bash
python -m alembic upgrade head
```

3. Check current version:
```bash
python -m alembic current
```

## Testing Migrations

### Test Upgrade
```bash
# Using Docker
docker-compose exec api alembic upgrade head

# Local
python -m alembic upgrade head
```

### Test Downgrade
```bash
# Using Docker
docker-compose exec api alembic downgrade -1

# Local
python -m alembic downgrade -1
```

### Test Full Cycle
```bash
# Downgrade to base
alembic downgrade base

# Upgrade to latest
alembic upgrade head
```

## Seeding Test Data

After running migrations, seed test data for development:

```bash
# Using Docker
docker-compose exec api python scripts/seed_invoice_data.py

# Local
python scripts/seed_invoice_data.py
```

This will create:
- 5 test invoices in various states (pending, overdue, partial, paid, detected)
- 1 pending reminder for an overdue invoice
- Audit trail actions for all invoices

## Migration Files

### Invoice Pilot Migration
- **File**: `alembic/versions/004_create_invoice_pilot_tables.py`
- **Revision**: 004
- **Dependencies**: 003 (Meeting Pilot tables)

Creates:
- `invoices` table - Core invoice data
- `invoice_reminders` table - Scheduled reminders
- `invoice_actions` table - Audit trail

### Indexes Created
- `idx_invoice_tenant_status` - For filtering by tenant and status
- `idx_invoice_tenant_due_date` - For finding due invoices per tenant
- `idx_invoice_status_due_date` - For global due date queries
- `idx_reminder_invoice_status` - For reminder status tracking
- `idx_reminder_status_scheduled` - For finding pending reminders
- `idx_action_invoice_timestamp` - For audit trail queries
- `idx_action_type_timestamp` - For action type analytics

### Constraints
- Unique constraint on `(tenant_id, gmail_message_id)` to prevent duplicate invoice detection
- Foreign keys with CASCADE delete for data integrity

## Troubleshooting

### Connection Refused
If you get a connection error, ensure PostgreSQL is running:
```bash
docker-compose up -d postgres
docker-compose ps
```

### Migration Already Applied
If migration is already at head:
```bash
alembic current
# Should show: 004 (head)
```

### Reset Database (⚠️ DESTRUCTIVE)
```bash
# Drop all tables and re-run migrations
alembic downgrade base
alembic upgrade head
python scripts/seed_invoice_data.py
```

## Creating New Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Create empty migration
alembic revision -m "Description of changes"
```

Always review auto-generated migrations before committing!
