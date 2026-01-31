# FounderPilot

AI-powered productivity assistant for founders.

## Features

- **Google OAuth Authentication** - Secure sign-in with Google accounts
- **Gmail Integration** - Connect Gmail for email management
- **Slack Integration** - Add FounderPilot bot to your Slack workspace
- **Onboarding Flow** - Guided setup for new users

## Tech Stack

### Backend
- **FastAPI** - Modern async Python web framework
- **SQLAlchemy** - Async ORM with PostgreSQL
- **Redis** - Session caching and rate limiting
- **JWT (RS256)** - Secure token-based authentication
- **Fernet** - Encryption for OAuth tokens

### Frontend
- **Next.js 16** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **Zustand** - Lightweight state management

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker and Docker Compose
- Google Cloud Console project (for OAuth)
- Slack App (for Slack integration)

### Environment Setup

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Configure the required environment variables in `.env`:
   - `GOOGLE_CLIENT_ID` - From Google Cloud Console
   - `GOOGLE_CLIENT_SECRET` - From Google Cloud Console
   - `SLACK_CLIENT_ID` - From Slack App settings
   - `SLACK_CLIENT_SECRET` - From Slack App settings
   - `JWT_PRIVATE_KEY` - RSA private key (RS256)
   - `JWT_PUBLIC_KEY` - RSA public key (RS256)
   - `ENCRYPTION_KEY` - Fernet key for token encryption

### Generate JWT Keys

```bash
# Generate RSA key pair
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem

# Set as environment variables (escape newlines)
export JWT_PRIVATE_KEY=$(cat private.pem | tr '\n' '|')
export JWT_PUBLIC_KEY=$(cat public.pem | tr '\n' '|')
```

### Generate Encryption Key

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### Running with Docker

```bash
# Start all services (PostgreSQL, Redis, API)
docker-compose up -d

# View logs
docker-compose logs -f api

# Run database migrations
docker-compose exec api alembic upgrade head
```

### Running Locally

#### Backend

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start the server
uvicorn src.api.main:app --reload
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Create local environment file
cp .env.local.example .env.local

# Start development server
npm run dev
```

## API Documentation

When running in debug mode, API documentation is available at:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Project Structure

```
.
├── src/
│   ├── api/           # FastAPI routes and app
│   │   ├── routes/    # API endpoint handlers
│   │   ├── dependencies.py
│   │   └── main.py
│   ├── core/          # Configuration and database
│   │   ├── config.py
│   │   ├── database.py
│   │   └── exceptions.py
│   ├── middleware/    # Custom middleware
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   └── services/      # Business logic
├── frontend/
│   ├── src/
│   │   ├── app/       # Next.js pages
│   │   ├── components/
│   │   └── lib/       # Hooks and API client
│   └── package.json
├── alembic/           # Database migrations
├── tests/             # Test suites
├── docker-compose.yml
└── requirements.txt
```

## OAuth Configuration

### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API and Gmail API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs:
   - `http://localhost:8000/api/v1/auth/google/callback` (development)
   - `http://localhost:8000/api/v1/integrations/gmail/callback` (Gmail)

### Slack App

1. Go to [Slack API](https://api.slack.com/apps)
2. Create a new app
3. Add OAuth scopes: `chat:write`, `im:write`, `users:read`
4. Add redirect URL:
   - `http://localhost:8000/api/v1/integrations/slack/callback`

## License

Proprietary - All rights reserved
