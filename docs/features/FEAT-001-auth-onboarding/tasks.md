# FEAT-001: Tasks

## Pre-Implementation Checklist
- [x] spec.md complete and approved
- [x] design.md complete and approved
- [x] Branch created: `feat/FEAT-001`
- [x] status.md updated to "In Progress"

---

## Phase 1: Backend Foundation

| # | Task | Status | Files |
|---|------|--------|-------|
| 1.1 | Create project structure | ✅ | src/, tests/, alembic/ |
| 1.2 | Setup config with pydantic-settings | ✅ | src/core/config.py |
| 1.3 | Setup async database connection | ✅ | src/core/database.py |
| 1.4 | Create SQLAlchemy models | ✅ | src/models/*.py |
| 1.5 | Create Alembic migration | ✅ | alembic/versions/001_*.py |
| 1.6 | Implement TokenEncryptionService | ✅ | src/services/token_encryption.py |
| 1.7 | Implement JWTService | ✅ | src/services/jwt.py |
| 1.8 | Create custom exceptions | ✅ | src/core/exceptions.py |
| 1.9 | Unit tests for services | ✅ | tests/unit/test_*.py |

### Detailed Phase 1 Tasks

- [x] **1.1**: Create project structure
  - [x] Create src/api/, src/core/, src/models/, src/schemas/, src/services/, src/middleware/
  - [x] Create __init__.py files
  - [x] Create requirements.txt with dependencies
  - [x] Create .env.example

- [x] **1.2**: Setup config (src/core/config.py)
  - [x] Define Settings class with all env vars
  - [x] Database URL, Redis URL
  - [x] JWT keys (private/public)
  - [x] OAuth credentials (Google, Slack)
  - [x] Encryption key

- [x] **1.3**: Database setup (src/core/database.py)
  - [x] Create async engine with asyncpg
  - [x] Create async session factory
  - [x] Create Base declarative class
  - [x] Create get_db dependency

- [x] **1.4**: SQLAlchemy models
  - [x] src/models/base.py - Base class with common fields
  - [x] src/models/user.py - User model
  - [x] src/models/integration.py - Integration model
  - [x] src/models/refresh_token.py - RefreshToken model
  - [x] src/models/audit_log.py - AuditLog model
  - [x] src/models/__init__.py - Export all models

- [x] **1.5**: Alembic migration
  - [x] alembic init alembic
  - [x] Configure alembic/env.py for async
  - [x] Create 001_initial_auth_tables.py migration

- [x] **1.6**: TokenEncryptionService
  - [x] Implement encrypt/decrypt with Fernet
  - [x] Unit test encryption roundtrip

- [x] **1.7**: JWTService
  - [x] Implement create_access_token
  - [x] Implement verify_token
  - [x] Handle token expiration
  - [x] Unit tests for JWT operations

- [x] **1.8**: Custom exceptions
  - [x] TokenExpiredError
  - [x] InvalidTokenError
  - [x] OAuthError
  - [x] IntegrationError

- [x] **1.9**: Unit tests
  - [x] tests/conftest.py with fixtures
  - [x] tests/unit/test_token_encryption.py
  - [x] tests/unit/test_jwt_service.py

---

## Phase 2: Google OAuth

| # | Task | Status | Files |
|---|------|--------|-------|
| 2.1 | Implement GoogleOAuthService | ✅ | src/services/google_oauth.py |
| 2.2 | Implement AuthService | ✅ | src/services/auth.py |
| 2.3 | Implement AuditService | ✅ | src/services/audit.py |
| 2.4 | Create Pydantic schemas | ✅ | src/schemas/*.py |
| 2.5 | Create auth routes | ✅ | src/api/routes/auth.py |
| 2.6 | Create dependencies | ✅ | src/api/dependencies.py |
| 2.7 | Add rate limiting middleware | ✅ | src/middleware/rate_limit.py |
| 2.8 | Create FastAPI main app | ✅ | src/api/main.py |
| 2.9 | Integration tests | ⬜ | tests/integration/test_auth_routes.py |

### Detailed Phase 2 Tasks

- [x] **2.1**: GoogleOAuthService
  - [x] get_authorization_url() - Generate OAuth URL with PKCE
  - [x] exchange_code() - Exchange code for tokens
  - [x] get_user_info() - Get user profile from Google
  - [x] Store state/verifier in Redis

- [x] **2.2**: AuthService
  - [x] get_google_auth_url() - Generate URL with state
  - [x] handle_google_callback() - Full callback handling
  - [x] _get_or_create_user() - Upsert user
  - [x] _create_refresh_token() - Create and store refresh token
  - [x] refresh_tokens() - Rotate tokens
  - [x] logout() - Blacklist tokens

- [x] **2.3**: AuditService
  - [x] log() - Create audit log entry
  - [x] get_user_logs() - Retrieve logs for user

- [x] **2.4**: Pydantic schemas
  - [x] src/schemas/auth.py - TokenResponse, RefreshRequest
  - [x] src/schemas/user.py - UserResponse, UserCreate
  - [x] src/schemas/common.py - ErrorResponse

- [x] **2.5**: Auth routes
  - [x] GET /api/v1/auth/google
  - [x] GET /api/v1/auth/google/callback
  - [x] POST /api/v1/auth/refresh
  - [x] POST /api/v1/auth/logout
  - [x] GET /api/v1/auth/me

- [x] **2.6**: Dependencies
  - [x] get_db() - Database session
  - [x] get_current_user() - Verify JWT, return user
  - [x] get_auth_service() - AuthService instance
  - [x] get_redis() - Redis connection

- [x] **2.7**: Rate limiting
  - [x] Redis-based rate limiter
  - [x] 10 req/min for /auth/* endpoints
  - [x] Return 429 when exceeded

- [x] **2.8**: FastAPI main app
  - [x] Create FastAPI instance
  - [x] Add CORS middleware
  - [x] Include auth router
  - [x] Exception handlers

- [ ] **2.9**: Integration tests
  - [ ] Test Google OAuth flow (mocked)
  - [ ] Test token refresh
  - [ ] Test logout
  - [ ] Test /me endpoint

---

## Phase 3: Gmail & Slack Integration

| # | Task | Status | Files |
|---|------|--------|-------|
| 3.1 | Implement GmailOAuthService | ✅ | src/services/gmail_oauth.py |
| 3.2 | Implement SlackOAuthService | ✅ | src/services/slack_oauth.py |
| 3.3 | Implement IntegrationService | ✅ | src/services/integration.py |
| 3.4 | Create integration schemas | ✅ | src/schemas/integration.py |
| 3.5 | Create integration routes | ✅ | src/api/routes/integrations.py |
| 3.6 | Create onboarding routes | ✅ | src/api/routes/onboarding.py |
| 3.7 | Integration tests | ⬜ | tests/integration/test_integration_routes.py |

### Detailed Phase 3 Tasks

- [x] **3.1**: GmailOAuthService
  - [x] get_auth_url() - OAuth URL with Gmail scopes
  - [x] handle_callback() - Exchange code, store tokens encrypted
  - [x] refresh_token() - Refresh Gmail token
  - [x] verify_connection() - Test API call

- [x] **3.2**: SlackOAuthService
  - [x] get_auth_url() - Slack OAuth URL
  - [x] handle_callback() - Install bot, get tokens
  - [x] verify_connection() - Test Slack API
  - [x] get_workspace_info() - Get workspace details

- [x] **3.3**: IntegrationService
  - [x] get_status() - Get all integration statuses
  - [x] disconnect() - Remove integration
  - [x] get_integration() - Get single integration
  - [x] is_connected() - Check if provider connected

- [x] **3.4**: Integration schemas
  - [x] IntegrationStatus
  - [x] IntegrationsStatusResponse
  - [x] DisconnectResponse

- [x] **3.5**: Integration routes
  - [x] GET /api/v1/integrations/gmail/connect
  - [x] GET /api/v1/integrations/gmail/callback
  - [x] DELETE /api/v1/integrations/gmail
  - [x] GET /api/v1/integrations/slack/connect
  - [x] GET /api/v1/integrations/slack/callback
  - [x] DELETE /api/v1/integrations/slack
  - [x] GET /api/v1/integrations/status

- [x] **3.6**: Onboarding routes
  - [x] GET /api/v1/onboarding/status
  - [x] POST /api/v1/onboarding/complete

- [ ] **3.7**: Integration tests
  - [ ] Test Gmail connect flow (mocked)
  - [ ] Test Slack connect flow (mocked)
  - [ ] Test disconnect flows
  - [ ] Test status endpoint

---

## Phase 4: Frontend Auth

| # | Task | Status | Files |
|---|------|--------|-------|
| 4.1 | Setup Next.js project | ✅ | frontend/ |
| 4.2 | Create API client | ✅ | frontend/src/lib/api/*.ts |
| 4.3 | Create useAuth hook | ✅ | frontend/src/lib/hooks/useAuth.ts |
| 4.4 | Create AuthGuard component | ✅ | frontend/src/components/auth/AuthGuard.tsx |
| 4.5 | Create login page | ✅ | frontend/src/app/auth/login/page.tsx |
| 4.6 | Create GoogleLoginButton | ✅ | frontend/src/components/auth/GoogleLoginButton.tsx |

### Detailed Phase 4 Tasks

- [x] **4.1**: Setup Next.js
  - [x] npx create-next-app@latest frontend
  - [x] Configure TypeScript
  - [x] Add Tailwind CSS
  - [ ] Add shadcn/ui (skipped - using Tailwind directly)

- [x] **4.2**: API client
  - [x] Create axios instance
  - [x] Add interceptor for 401 -> refresh
  - [x] Export API methods

- [x] **4.3**: useAuth hook
  - [x] State: user, loading, error
  - [x] Methods: login, logout, refreshUser
  - [x] Auto-fetch user on mount

- [x] **4.4**: AuthGuard
  - [x] Check auth state
  - [x] Redirect to /auth/login if not authenticated
  - [x] Show loading while checking

- [x] **4.5**: Login page
  - [x] Minimal design
  - [x] FounderPilot logo
  - [x] "Continue with Google" button
  - [x] Error handling

- [x] **4.6**: GoogleLoginButton
  - [x] Google branding colors
  - [x] Google icon
  - [x] Loading state
  - [x] Redirect to /api/v1/auth/google

---

## Phase 5: Frontend Onboarding

| # | Task | Status | Files |
|---|------|--------|-------|
| 5.1 | Create OnboardingStepper | ✅ | frontend/src/components/onboarding/OnboardingStepper.tsx |
| 5.2 | Create onboarding page | ✅ | frontend/src/app/onboarding/page.tsx |
| 5.3 | Create GmailConnectCard | ✅ | frontend/src/components/onboarding/GmailConnectCard.tsx |
| 5.4 | Create Gmail step page | ⏭️ | (integrated into main onboarding page) |
| 5.5 | Create SlackConnectCard | ✅ | frontend/src/components/onboarding/SlackConnectCard.tsx |
| 5.6 | Create Slack step page | ⏭️ | (integrated into main onboarding page) |
| 5.7 | Create connections dashboard | ✅ | frontend/src/app/dashboard/connections/page.tsx |
| 5.8 | Create ConnectionCard | ✅ | frontend/src/components/connections/ConnectionCard.tsx |
| 5.9 | Create useIntegrations hook | ✅ | frontend/src/lib/hooks/useIntegrations.ts |

### Detailed Phase 5 Tasks

- [x] **5.1**: OnboardingStepper
  - [x] 3 steps: Google (done), Gmail, Slack
  - [x] Visual progress indicator
  - [x] Step status (complete, current, pending)

- [x] **5.2**: Onboarding main page
  - [x] Fetch onboarding status
  - [x] Route to current step

- [x] **5.3**: GmailConnectCard
  - [x] Gmail icon
  - [x] "Connect Gmail" button
  - [x] Scopes explanation
  - [x] Connected/disconnected state

- [x] **5.4**: Gmail step page (integrated into main onboarding)
  - [x] Use GmailConnectCard
  - [x] Show what permissions are needed
  - [x] "Skip for now" option

- [x] **5.5**: SlackConnectCard
  - [x] Slack icon
  - [x] "Add to Slack" button
  - [x] Workspace selection if multiple

- [x] **5.6**: Slack step page (integrated into main onboarding)
  - [x] Use SlackConnectCard
  - [x] Explain bot functionality
  - [x] "Skip for now" option
  - [x] "Complete Setup" button

- [x] **5.7**: Connections dashboard
  - [x] List all integrations
  - [x] Status indicators
  - [x] Disconnect buttons
  - [x] Re-connect options

- [x] **5.8**: ConnectionCard
  - [x] Provider icon
  - [x] Connection status
  - [x] Connected date
  - [x] Disconnect/reconnect action

- [x] **5.9**: useIntegrations hook
  - [x] Fetch integration status
  - [x] Connect/disconnect methods
  - [x] Loading states

---

## Phase 6: Testing & Polish

| # | Task | Status | Files |
|---|------|--------|-------|
| 6.1 | E2E tests setup | ⬜ | tests/e2e/ |
| 6.2 | E2E login flow | ⬜ | tests/e2e/test_login.py |
| 6.3 | E2E onboarding flow | ⬜ | tests/e2e/test_onboarding.py |
| 6.4 | Add loading states | ✅ | (included in components) |
| 6.5 | Add error boundaries | ✅ | frontend/src/app/error.tsx |
| 6.6 | Add docker-compose | ✅ | docker-compose.yml, Dockerfile.api |

### Detailed Phase 6 Tasks

- [ ] **6.1**: E2E setup
  - [ ] Install playwright or pytest-httpx
  - [ ] Configure test database
  - [ ] Setup fixtures

- [ ] **6.2**: E2E login flow
  - [ ] Test complete Google OAuth flow
  - [ ] Test redirect to onboarding
  - [ ] Test redirect to dashboard

- [ ] **6.3**: E2E onboarding flow
  - [ ] Test Gmail connect
  - [ ] Test Slack connect
  - [ ] Test skip options
  - [ ] Test complete onboarding

- [x] **6.4**: Loading states
  - [x] Login button loading
  - [x] Connect button loading
  - [x] Page transitions

- [x] **6.5**: Error boundaries
  - [x] Global error boundary
  - [x] OAuth error page
  - [x] Network error handling

- [x] **6.6**: Docker compose
  - [x] PostgreSQL service
  - [x] Redis service
  - [x] API service
  - [ ] Frontend service (optional - skipped)

---

## DevOps Tasks

| # | Task | Status | Files |
|---|------|--------|-------|
| O1 | Create .env.example | ✅ | .env.example |
| O2 | Create Dockerfile.api | ✅ | Dockerfile.api |
| O3 | Create docker-compose.yml | ✅ | docker-compose.yml |

---

## Documentation Tasks

| # | Task | Status | Files |
|---|------|--------|-------|
| D1 | API documentation | ⬜ | Auto-generated by FastAPI |
| D2 | Setup instructions | ⬜ | README.md |
| D3 | Environment variables doc | ⬜ | .env.example comments |

---

## Progress Tracking

### Status Legend
| Symbol | Meaning |
|--------|---------|
| ⬜ | Pending |
| 🟡 | In Progress |
| ✅ | Completed |
| 🔴 | Blocked |
| ⏭️ | Skipped |

### Current Progress

| Phase | Done | Total | % |
|-------|------|-------|---|
| Phase 1: Foundation | 9 | 9 | 100% |
| Phase 2: Google OAuth | 8 | 9 | 89% |
| Phase 3: Integrations | 6 | 7 | 86% |
| Phase 4: Frontend Auth | 6 | 6 | 100% |
| Phase 5: Onboarding | 9 | 9 | 100% |
| Phase 6: Testing | 3 | 6 | 50% |
| DevOps | 3 | 3 | 100% |
| Documentation | 0 | 3 | 0% |
| **TOTAL** | **44** | **52** | **85%** |

---

## Notes

### Blockers
_None currently_

### Decisions Made During Implementation
_Document any decisions made while implementing_

### Technical Debt
_Track any shortcuts taken that need future work_

---

*Last updated: 2026-01-31*
*Created by: Ralph Loop*
