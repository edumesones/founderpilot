# FEAT-001: Technical Design

## Overview

Sistema de autenticacion y onboarding para FounderPilot usando Google OAuth2 como proveedor principal, JWT para sesiones stateless, y OAuth2 flows separados para Gmail y Slack integrations. El flujo guia al usuario desde signup hasta tener todas las conexiones activas en 3 pasos.

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    FRONTEND (Next.js)                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │  /auth/     │  │ /onboarding │  │ /dashboard  │  │ /settings   │                 │
│  │  login      │  │ /gmail      │  │ /connections│  │ /connections│                 │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │
└─────────┼────────────────┼────────────────┼────────────────┼────────────────────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                  BACKEND API (FastAPI)                               │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                              API Routes                                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │  │
│  │  │ /auth/*     │  │/integrations│  │ /onboarding │  │  /users/*   │          │  │
│  │  │ google,     │  │ gmail,slack │  │ status,     │  │  me, update │          │  │
│  │  │ callback    │  │ connect,    │  │ complete    │  │             │          │  │
│  │  │ refresh,    │  │ callback,   │  │             │  │             │          │  │
│  │  │ logout      │  │ disconnect  │  │             │  │             │          │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘          │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                             │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                              Services                                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │  │
│  │  │ AuthService │  │ GoogleOAuth │  │ GmailOAuth  │  │ SlackOAuth  │          │  │
│  │  │             │  │   Service   │  │  Service    │  │  Service    │          │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                           │  │
│  │  │ JWTService  │  │TokenService │  │ AuditService│                           │  │
│  │  │             │  │ (encrypt)   │  │             │                           │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                           │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                             │
└────────────────────────────────────────┼─────────────────────────────────────────────┘
                                         │
          ┌──────────────────────────────┼──────────────────────────────┐
          │                              │                              │
          ▼                              ▼                              ▼
┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
│   PostgreSQL    │          │     Redis       │          │   External      │
│                 │          │                 │          │                 │
│  - users        │          │  - token        │          │  - Google OAuth │
│  - integrations │          │    blacklist    │          │  - Gmail API    │
│  - refresh_tkns │          │  - rate limits  │          │  - Slack OAuth  │
│  - audit_logs   │          │                 │          │                 │
└─────────────────┘          └─────────────────┘          └─────────────────┘
```

### OAuth2 Flow Sequence

```
┌──────┐          ┌──────────┐          ┌──────────┐          ┌──────────┐
│ User │          │ Frontend │          │ Backend  │          │ Google   │
└──┬───┘          └────┬─────┘          └────┬─────┘          └────┬─────┘
   │                   │                     │                     │
   │ Click "Login"     │                     │                     │
   │──────────────────>│                     │                     │
   │                   │ GET /auth/google    │                     │
   │                   │────────────────────>│                     │
   │                   │                     │ Generate state+PKCE │
   │                   │                     │────────────────────>│
   │                   │ 302 Redirect        │                     │
   │                   │<────────────────────│                     │
   │ Redirect to Google│                     │                     │
   │<──────────────────│                     │                     │
   │                   │                     │                     │
   │ Authorize         │                     │                     │
   │─────────────────────────────────────────────────────────────>│
   │                   │                     │                     │
   │ Callback with code│                     │                     │
   │<─────────────────────────────────────────────────────────────│
   │                   │                     │                     │
   │ Redirect to callback                    │                     │
   │──────────────────────────────────────-->│                     │
   │                   │                     │ Exchange code       │
   │                   │                     │────────────────────>│
   │                   │                     │ Tokens              │
   │                   │                     │<────────────────────│
   │                   │                     │                     │
   │                   │                     │ Create/Get User     │
   │                   │                     │ Generate JWT        │
   │                   │                     │ Store RefreshToken  │
   │                   │                     │                     │
   │                   │ Set cookies + redirect                    │
   │<──────────────────────────────────────────────────────────────│
   │                   │                     │                     │
```

---

## File Structure

### New Files to Create

```
src/
├── api/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entrypoint
│   ├── dependencies.py            # Auth dependencies
│   └── routes/
│       ├── __init__.py
│       ├── auth.py                # /api/v1/auth/*
│       ├── integrations.py        # /api/v1/integrations/*
│       ├── onboarding.py          # /api/v1/onboarding/*
│       └── users.py               # /api/v1/users/*
│
├── core/
│   ├── __init__.py
│   ├── config.py                  # Settings with pydantic-settings
│   ├── database.py                # SQLAlchemy async engine
│   ├── security.py                # JWT, encryption helpers
│   └── exceptions.py              # Custom exceptions
│
├── models/
│   ├── __init__.py
│   ├── user.py                    # User SQLAlchemy model
│   ├── integration.py             # Integration model
│   ├── refresh_token.py           # RefreshToken model
│   └── audit_log.py               # AuditLog model
│
├── schemas/
│   ├── __init__.py
│   ├── auth.py                    # Token schemas
│   ├── user.py                    # User request/response
│   ├── integration.py             # Integration schemas
│   └── onboarding.py              # Onboarding schemas
│
├── services/
│   ├── __init__.py
│   ├── auth.py                    # AuthService
│   ├── jwt.py                     # JWTService
│   ├── token_encryption.py        # TokenEncryptionService
│   ├── google_oauth.py            # GoogleOAuthService
│   ├── gmail_oauth.py             # GmailOAuthService
│   ├── slack_oauth.py             # SlackOAuthService
│   └── audit.py                   # AuditService
│
└── middleware/
    ├── __init__.py
    ├── auth.py                    # JWT verification middleware
    └── rate_limit.py              # Rate limiting middleware

frontend/
├── app/
│   ├── auth/
│   │   ├── login/page.tsx         # Login page
│   │   └── callback/page.tsx      # OAuth callback handler
│   ├── onboarding/
│   │   ├── page.tsx               # Onboarding stepper
│   │   ├── gmail/page.tsx         # Gmail connect step
│   │   └── slack/page.tsx         # Slack connect step
│   └── dashboard/
│       └── connections/page.tsx   # Connections management
├── components/
│   ├── auth/
│   │   ├── GoogleLoginButton.tsx
│   │   └── AuthGuard.tsx
│   ├── onboarding/
│   │   ├── OnboardingStepper.tsx
│   │   ├── GmailConnectCard.tsx
│   │   └── SlackConnectCard.tsx
│   └── connections/
│       └── ConnectionCard.tsx
└── lib/
    ├── api.ts                     # API client
    ├── auth.ts                    # Auth utilities
    └── hooks/
        ├── useAuth.ts
        └── useIntegrations.ts

tests/
├── unit/
│   ├── test_jwt_service.py
│   ├── test_token_encryption.py
│   └── test_auth_service.py
├── integration/
│   ├── test_auth_routes.py
│   ├── test_integration_routes.py
│   └── test_onboarding_routes.py
└── conftest.py

alembic/
└── versions/
    └── 001_initial_auth_tables.py
```

### Files to Modify

| File | Changes |
|------|---------|
| `requirements.txt` | Add fastapi, sqlalchemy, pyjwt, cryptography, httpx, redis |
| `.env.example` | Add all OAuth credentials placeholders |
| `docker-compose.yml` | Add postgres, redis services |

---

## Data Model

### Database Schema

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    picture_url VARCHAR(512),
    google_id VARCHAR(255) UNIQUE NOT NULL,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_google_id ON users(google_id);

-- Integrations table
CREATE TABLE integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,  -- 'gmail', 'slack'
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    scopes TEXT[],  -- Array of granted scopes
    metadata JSONB DEFAULT '{}',  -- Provider-specific data
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'expired', 'revoked'
    connected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(user_id, provider)  -- One integration per provider per user
);

CREATE INDEX idx_integrations_user_id ON integrations(user_id);
CREATE INDEX idx_integrations_provider ON integrations(provider);

-- Refresh tokens table
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);

-- Audit logs table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,  -- 'signup', 'login', 'gmail_connect', etc.
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
```

### SQLAlchemy Models

```python
# src/models/user.py
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    picture_url = Column(String(512))
    google_id = Column(String(255), unique=True, nullable=False, index=True)
    onboarding_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    integrations = relationship("Integration", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
```

---

## Service Layer

### AuthService

```python
# src/services/auth.py
class AuthService:
    def __init__(
        self,
        db: AsyncSession,
        jwt_service: JWTService,
        google_oauth: GoogleOAuthService,
        audit_service: AuditService
    ):
        self.db = db
        self.jwt = jwt_service
        self.google = google_oauth
        self.audit = audit_service

    async def get_google_auth_url(self, redirect_uri: str) -> tuple[str, str]:
        """Generate Google OAuth URL with state and PKCE."""
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = self._generate_pkce_challenge(code_verifier)

        # Store state and verifier in Redis (5 min TTL)
        await self._store_oauth_state(state, code_verifier)

        url = self.google.get_authorization_url(
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge
        )
        return url, state

    async def handle_google_callback(
        self, code: str, state: str, redirect_uri: str
    ) -> tuple[User, str, str]:
        """Exchange code for tokens, create/get user, return JWT."""
        # Verify state and get code_verifier
        code_verifier = await self._verify_oauth_state(state)

        # Exchange code for tokens
        tokens = await self.google.exchange_code(
            code=code,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier
        )

        # Get user info from Google
        user_info = await self.google.get_user_info(tokens.access_token)

        # Create or get user
        user = await self._get_or_create_user(user_info)

        # Generate JWT and refresh token
        access_token = self.jwt.create_access_token(user.id)
        refresh_token = await self._create_refresh_token(user.id)

        # Audit log
        await self.audit.log(
            user_id=user.id,
            action="login" if user.created_at != user.updated_at else "signup",
            details={"provider": "google"}
        )

        return user, access_token, refresh_token
```

### JWTService

```python
# src/services/jwt.py
class JWTService:
    def __init__(self, settings: Settings):
        self.private_key = settings.jwt_private_key
        self.public_key = settings.jwt_public_key
        self.algorithm = "RS256"
        self.access_token_expire = timedelta(hours=24)

    def create_access_token(self, user_id: UUID) -> str:
        payload = {
            "sub": str(user_id),
            "exp": datetime.utcnow() + self.access_token_expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        return jwt.encode(payload, self.private_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm]
            )
            if payload.get("type") != "access":
                raise InvalidTokenError("Invalid token type")
            return payload
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(str(e))
```

### TokenEncryptionService

```python
# src/services/token_encryption.py
from cryptography.fernet import Fernet

class TokenEncryptionService:
    def __init__(self, settings: Settings):
        self.fernet = Fernet(settings.encryption_key.encode())

    def encrypt(self, plaintext: str) -> str:
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self.fernet.decrypt(ciphertext.encode()).decode()
```

---

## API Endpoints

### Auth Routes

```python
# src/api/routes/auth.py
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.get("/google")
async def google_login(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Initiate Google OAuth2 flow."""
    redirect_uri = str(request.url_for("google_callback"))
    auth_url, state = await auth_service.get_google_auth_url(redirect_uri)

    response = RedirectResponse(url=auth_url)
    response.set_cookie("oauth_state", state, httponly=True, max_age=300)
    return response

@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str,
    state: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Handle Google OAuth2 callback."""
    # Verify state cookie
    cookie_state = request.cookies.get("oauth_state")
    if cookie_state != state:
        raise HTTPException(400, "Invalid state parameter")

    redirect_uri = str(request.url_for("google_callback"))
    user, access_token, refresh_token = await auth_service.handle_google_callback(
        code=code,
        state=state,
        redirect_uri=redirect_uri
    )

    # Determine redirect based on onboarding status
    frontend_url = settings.frontend_url
    if not user.onboarding_completed:
        redirect_url = f"{frontend_url}/onboarding"
    else:
        redirect_url = f"{frontend_url}/dashboard"

    response = RedirectResponse(url=redirect_url)
    response.set_cookie(
        "access_token", access_token,
        httponly=True, secure=True, samesite="lax", max_age=86400
    )
    response.set_cookie(
        "refresh_token", refresh_token,
        httponly=True, secure=True, samesite="lax", max_age=604800
    )
    response.delete_cookie("oauth_state")
    return response

@router.post("/refresh")
async def refresh_token(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token using refresh token."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(401, "Refresh token required")

    new_access, new_refresh = await auth_service.refresh_tokens(refresh_token)

    response = JSONResponse({"message": "Token refreshed"})
    response.set_cookie(
        "access_token", new_access,
        httponly=True, secure=True, samesite="lax", max_age=86400
    )
    response.set_cookie(
        "refresh_token", new_refresh,
        httponly=True, secure=True, samesite="lax", max_age=604800
    )
    return response

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logout user and blacklist tokens."""
    await auth_service.logout(current_user.id)

    response = JSONResponse({"message": "Logged out"})
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return current_user
```

### Integration Routes

```python
# src/api/routes/integrations.py
router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])

@router.get("/gmail/connect")
async def connect_gmail(
    request: Request,
    current_user: User = Depends(get_current_user),
    gmail_service: GmailOAuthService = Depends(get_gmail_service)
):
    """Initiate Gmail OAuth2 flow."""
    redirect_uri = str(request.url_for("gmail_callback"))
    auth_url, state = await gmail_service.get_auth_url(
        user_id=current_user.id,
        redirect_uri=redirect_uri
    )
    return RedirectResponse(url=auth_url)

@router.get("/gmail/callback")
async def gmail_callback(
    request: Request,
    code: str,
    state: str,
    current_user: User = Depends(get_current_user),
    gmail_service: GmailOAuthService = Depends(get_gmail_service)
):
    """Handle Gmail OAuth2 callback."""
    await gmail_service.handle_callback(
        user_id=current_user.id,
        code=code,
        state=state,
        redirect_uri=str(request.url_for("gmail_callback"))
    )
    return RedirectResponse(url=f"{settings.frontend_url}/onboarding/slack")

@router.delete("/gmail")
async def disconnect_gmail(
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Disconnect Gmail integration."""
    await integration_service.disconnect(current_user.id, "gmail")
    return {"message": "Gmail disconnected"}

# Similar endpoints for Slack...

@router.get("/status", response_model=IntegrationsStatusResponse)
async def get_integrations_status(
    current_user: User = Depends(get_current_user),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """Get status of all integrations."""
    return await integration_service.get_status(current_user.id)
```

---

## Error Handling

| Error | HTTP Code | Response |
|-------|-----------|----------|
| Invalid OAuth state | 400 | `{"error": "invalid_state", "message": "Invalid or expired OAuth state"}` |
| OAuth cancelled | 400 | `{"error": "oauth_cancelled", "message": "Authorization was cancelled"}` |
| Invalid token | 401 | `{"error": "invalid_token", "message": "Token is invalid or expired"}` |
| Insufficient scopes | 403 | `{"error": "insufficient_scopes", "message": "Required scopes not granted"}` |
| Integration not found | 404 | `{"error": "not_found", "message": "Integration not found"}` |
| Rate limited | 429 | `{"error": "rate_limited", "message": "Too many requests"}` |
| Provider error | 502 | `{"error": "provider_error", "message": "Error communicating with provider"}` |

---

## Security Considerations

- [x] PKCE flow for all OAuth2 requests (prevent authorization code interception)
- [x] State parameter verification (CSRF protection)
- [x] Tokens stored encrypted in database (Fernet/AES-256)
- [x] JWT signed with RS256 (asymmetric keys)
- [x] Refresh token rotation on each use
- [x] Token blacklist in Redis for logout/revocation
- [x] Rate limiting: 10 req/min on auth endpoints
- [x] Secure cookies: HttpOnly, Secure, SameSite=Lax
- [x] No tokens in URL parameters or logs

---

## Dependencies

### New Packages

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | ^0.109.0 | Web framework |
| uvicorn | ^0.27.0 | ASGI server |
| sqlalchemy[asyncio] | ^2.0.0 | ORM |
| asyncpg | ^0.29.0 | PostgreSQL driver |
| pydantic-settings | ^2.1.0 | Settings management |
| python-jose[cryptography] | ^3.3.0 | JWT handling |
| cryptography | ^42.0.0 | Token encryption |
| httpx | ^0.26.0 | HTTP client for OAuth |
| redis | ^5.0.0 | Token blacklist, rate limiting |
| alembic | ^1.13.0 | Database migrations |

---

## Implementation Order

### Phase 1: Foundation (Backend Core)
1. Create project structure and config
2. Setup database connection and models
3. Create Alembic migrations
4. Implement TokenEncryptionService
5. Implement JWTService

### Phase 2: Google OAuth
1. Implement GoogleOAuthService
2. Create /auth/google and /auth/google/callback routes
3. Implement AuthService
4. Add rate limiting middleware
5. Unit tests for auth flow

### Phase 3: Gmail & Slack Integration
1. Implement GmailOAuthService
2. Implement SlackOAuthService
3. Create integration routes
4. Integration tests

### Phase 4: Frontend Auth
1. Create login page with Google button
2. Implement AuthGuard component
3. Create useAuth hook
4. Handle callback and token storage

### Phase 5: Frontend Onboarding
1. Create OnboardingStepper component
2. Gmail connect step
3. Slack connect step
4. Connections dashboard

### Phase 6: Testing & Polish
1. E2E tests for complete flow
2. Error handling improvements
3. Loading states and UX polish

---

## Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/founderpilot

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_PRIVATE_KEY=...  # RSA private key
JWT_PUBLIC_KEY=...   # RSA public key

# Encryption
ENCRYPTION_KEY=...   # 32-byte Fernet key

# Google OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Gmail OAuth (same app, different scopes)
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...

# Slack OAuth
SLACK_CLIENT_ID=...
SLACK_CLIENT_SECRET=...
SLACK_SIGNING_SECRET=...

# Frontend
FRONTEND_URL=http://localhost:3000

# Server
API_HOST=0.0.0.0
API_PORT=8000
```

---

## Open Technical Questions

- [x] Single Google app for auth + Gmail, or separate apps? **Decision: Single app, request additional scopes during Gmail connect**
- [x] Store JWT in cookies or localStorage? **Decision: HttpOnly cookies for security**
- [x] How to handle token refresh in frontend? **Decision: Axios interceptor, retry on 401**

---

## References

- [FastAPI OAuth2 Tutorial](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [Google OAuth2 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Gmail API Scopes](https://developers.google.com/gmail/api/auth/scopes)
- [Slack OAuth2 Documentation](https://api.slack.com/authentication/oauth-v2)
- [PKCE RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)

---

*Created: 2026-01-31*
*Last updated: 2026-01-31*
*Approved: [x] Ready for implementation*
