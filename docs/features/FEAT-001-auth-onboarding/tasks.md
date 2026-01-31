# FEAT-001: Tasks

## Pre-Implementation Checklist
- [x] spec.md complete and approved
- [x] design.md complete and approved
- [ ] Branch created: `feat/FEAT-001`
- [ ] status.md updated to "In Progress"

---

## Phase 1: Backend Foundation

| # | Task | Status | Files |
|---|------|--------|-------|
| 1.1 | Create project structure | ⬜ | src/, tests/, alembic/ |
| 1.2 | Setup config with pydantic-settings | ⬜ | src/core/config.py |
| 1.3 | Setup async database connection | ⬜ | src/core/database.py |
| 1.4 | Create SQLAlchemy models | ⬜ | src/models/*.py |
| 1.5 | Create Alembic migration | ⬜ | alembic/versions/001_*.py |
| 1.6 | Implement TokenEncryptionService | ⬜ | src/services/token_encryption.py |
| 1.7 | Implement JWTService | ⬜ | src/services/jwt.py |
| 1.8 | Create custom exceptions | ⬜ | src/core/exceptions.py |
| 1.9 | Unit tests for services | ⬜ | tests/unit/test_*.py |

### Detailed Phase 1 Tasks

- [ ] **1.1**: Create project structure
  - [ ] Create src/api/, src/core/, src/models/, src/schemas/, src/services/, src/middleware/
  - [ ] Create __init__.py files
  - [ ] Create requirements.txt with dependencies
  - [ ] Create .env.example

- [ ] **1.2**: Setup config (src/core/config.py)
  - [ ] Define Settings class with all env vars
  - [ ] Database URL, Redis URL
  - [ ] JWT keys (private/public)
  - [ ] OAuth credentials (Google, Slack)
  - [ ] Encryption key

- [ ] **1.3**: Database setup (src/core/database.py)
  - [ ] Create async engine with asyncpg
  - [ ] Create async session factory
  - [ ] Create Base declarative class
  - [ ] Create get_db dependency

- [ ] **1.4**: SQLAlchemy models
  - [ ] src/models/base.py - Base class with common fields
  - [ ] src/models/user.py - User model
  - [ ] src/models/integration.py - Integration model
  - [ ] src/models/refresh_token.py - RefreshToken model
  - [ ] src/models/audit_log.py - AuditLog model
  - [ ] src/models/__init__.py - Export all models

- [ ] **1.5**: Alembic migration
  - [ ] alembic init alembic
  - [ ] Configure alembic/env.py for async
  - [ ] Create 001_initial_auth_tables.py migration

- [ ] **1.6**: TokenEncryptionService
  - [ ] Implement encrypt/decrypt with Fernet
  - [ ] Unit test encryption roundtrip

- [ ] **1.7**: JWTService
  - [ ] Implement create_access_token
  - [ ] Implement verify_token
  - [ ] Handle token expiration
  - [ ] Unit tests for JWT operations

- [ ] **1.8**: Custom exceptions
  - [ ] TokenExpiredError
  - [ ] InvalidTokenError
  - [ ] OAuthError
  - [ ] IntegrationError

- [ ] **1.9**: Unit tests
  - [ ] tests/conftest.py with fixtures
  - [ ] tests/unit/test_token_encryption.py
  - [ ] tests/unit/test_jwt_service.py

---

## Phase 2: Google OAuth

| # | Task | Status | Files |
|---|------|--------|-------|
| 2.1 | Implement GoogleOAuthService | ⬜ | src/services/google_oauth.py |
| 2.2 | Implement AuthService | ⬜ | src/services/auth.py |
| 2.3 | Implement AuditService | ⬜ | src/services/audit.py |
| 2.4 | Create Pydantic schemas | ⬜ | src/schemas/*.py |
| 2.5 | Create auth routes | ⬜ | src/api/routes/auth.py |
| 2.6 | Create dependencies | ⬜ | src/api/dependencies.py |
| 2.7 | Add rate limiting middleware | ⬜ | src/middleware/rate_limit.py |
| 2.8 | Create FastAPI main app | ⬜ | src/api/main.py |
| 2.9 | Integration tests | ⬜ | tests/integration/test_auth_routes.py |

### Detailed Phase 2 Tasks

- [ ] **2.1**: GoogleOAuthService
  - [ ] get_authorization_url() - Generate OAuth URL with PKCE
  - [ ] exchange_code() - Exchange code for tokens
  - [ ] get_user_info() - Get user profile from Google
  - [ ] Store state/verifier in Redis

- [ ] **2.2**: AuthService
  - [ ] get_google_auth_url() - Generate URL with state
  - [ ] handle_google_callback() - Full callback handling
  - [ ] _get_or_create_user() - Upsert user
  - [ ] _create_refresh_token() - Create and store refresh token
  - [ ] refresh_tokens() - Rotate tokens
  - [ ] logout() - Blacklist tokens

- [ ] **2.3**: AuditService
  - [ ] log() - Create audit log entry
  - [ ] get_user_logs() - Retrieve logs for user

- [ ] **2.4**: Pydantic schemas
  - [ ] src/schemas/auth.py - TokenResponse, RefreshRequest
  - [ ] src/schemas/user.py - UserResponse, UserCreate
  - [ ] src/schemas/common.py - ErrorResponse

- [ ] **2.5**: Auth routes
  - [ ] GET /api/v1/auth/google
  - [ ] GET /api/v1/auth/google/callback
  - [ ] POST /api/v1/auth/refresh
  - [ ] POST /api/v1/auth/logout
  - [ ] GET /api/v1/auth/me

- [ ] **2.6**: Dependencies
  - [ ] get_db() - Database session
  - [ ] get_current_user() - Verify JWT, return user
  - [ ] get_auth_service() - AuthService instance
  - [ ] get_redis() - Redis connection

- [ ] **2.7**: Rate limiting
  - [ ] Redis-based rate limiter
  - [ ] 10 req/min for /auth/* endpoints
  - [ ] Return 429 when exceeded

- [ ] **2.8**: FastAPI main app
  - [ ] Create FastAPI instance
  - [ ] Add CORS middleware
  - [ ] Include auth router
  - [ ] Exception handlers

- [ ] **2.9**: Integration tests
  - [ ] Test Google OAuth flow (mocked)
  - [ ] Test token refresh
  - [ ] Test logout
  - [ ] Test /me endpoint

---

## Phase 3: Gmail & Slack Integration

| # | Task | Status | Files |
|---|------|--------|-------|
| 3.1 | Implement GmailOAuthService | ⬜ | src/services/gmail_oauth.py |
| 3.2 | Implement SlackOAuthService | ⬜ | src/services/slack_oauth.py |
| 3.3 | Implement IntegrationService | ⬜ | src/services/integration.py |
| 3.4 | Create integration schemas | ⬜ | src/schemas/integration.py |
| 3.5 | Create integration routes | ⬜ | src/api/routes/integrations.py |
| 3.6 | Create onboarding routes | ⬜ | src/api/routes/onboarding.py |
| 3.7 | Integration tests | ⬜ | tests/integration/test_integration_routes.py |

### Detailed Phase 3 Tasks

- [ ] **3.1**: GmailOAuthService
  - [ ] get_auth_url() - OAuth URL with Gmail scopes
  - [ ] handle_callback() - Exchange code, store tokens encrypted
  - [ ] refresh_token() - Refresh Gmail token
  - [ ] verify_connection() - Test API call

- [ ] **3.2**: SlackOAuthService
  - [ ] get_auth_url() - Slack OAuth URL
  - [ ] handle_callback() - Install bot, get tokens
  - [ ] verify_connection() - Test Slack API
  - [ ] get_workspace_info() - Get workspace details

- [ ] **3.3**: IntegrationService
  - [ ] get_status() - Get all integration statuses
  - [ ] disconnect() - Remove integration
  - [ ] get_integration() - Get single integration
  - [ ] is_connected() - Check if provider connected

- [ ] **3.4**: Integration schemas
  - [ ] IntegrationStatus
  - [ ] IntegrationsStatusResponse
  - [ ] DisconnectResponse

- [ ] **3.5**: Integration routes
  - [ ] GET /api/v1/integrations/gmail/connect
  - [ ] GET /api/v1/integrations/gmail/callback
  - [ ] DELETE /api/v1/integrations/gmail
  - [ ] GET /api/v1/integrations/slack/connect
  - [ ] GET /api/v1/integrations/slack/callback
  - [ ] DELETE /api/v1/integrations/slack
  - [ ] GET /api/v1/integrations/status

- [ ] **3.6**: Onboarding routes
  - [ ] GET /api/v1/onboarding/status
  - [ ] POST /api/v1/onboarding/complete

- [ ] **3.7**: Integration tests
  - [ ] Test Gmail connect flow (mocked)
  - [ ] Test Slack connect flow (mocked)
  - [ ] Test disconnect flows
  - [ ] Test status endpoint

---

## Phase 4: Frontend Auth

| # | Task | Status | Files |
|---|------|--------|-------|
| 4.1 | Setup Next.js project | ⬜ | frontend/ |
| 4.2 | Create API client | ⬜ | frontend/lib/api.ts |
| 4.3 | Create useAuth hook | ⬜ | frontend/lib/hooks/useAuth.ts |
| 4.4 | Create AuthGuard component | ⬜ | frontend/components/auth/AuthGuard.tsx |
| 4.5 | Create login page | ⬜ | frontend/app/auth/login/page.tsx |
| 4.6 | Create GoogleLoginButton | ⬜ | frontend/components/auth/GoogleLoginButton.tsx |

### Detailed Phase 4 Tasks

- [ ] **4.1**: Setup Next.js
  - [ ] npx create-next-app@latest frontend
  - [ ] Configure TypeScript
  - [ ] Add Tailwind CSS
  - [ ] Add shadcn/ui

- [ ] **4.2**: API client
  - [ ] Create axios instance
  - [ ] Add interceptor for 401 -> refresh
  - [ ] Export API methods

- [ ] **4.3**: useAuth hook
  - [ ] State: user, loading, error
  - [ ] Methods: login, logout, refreshUser
  - [ ] Auto-fetch user on mount

- [ ] **4.4**: AuthGuard
  - [ ] Check auth state
  - [ ] Redirect to /auth/login if not authenticated
  - [ ] Show loading while checking

- [ ] **4.5**: Login page
  - [ ] Minimal design
  - [ ] FounderPilot logo
  - [ ] "Continue with Google" button
  - [ ] Error handling

- [ ] **4.6**: GoogleLoginButton
  - [ ] Google branding colors
  - [ ] Google icon
  - [ ] Loading state
  - [ ] Redirect to /api/v1/auth/google

---

## Phase 5: Frontend Onboarding

| # | Task | Status | Files |
|---|------|--------|-------|
| 5.1 | Create OnboardingStepper | ⬜ | frontend/components/onboarding/OnboardingStepper.tsx |
| 5.2 | Create onboarding page | ⬜ | frontend/app/onboarding/page.tsx |
| 5.3 | Create GmailConnectCard | ⬜ | frontend/components/onboarding/GmailConnectCard.tsx |
| 5.4 | Create Gmail step page | ⬜ | frontend/app/onboarding/gmail/page.tsx |
| 5.5 | Create SlackConnectCard | ⬜ | frontend/components/onboarding/SlackConnectCard.tsx |
| 5.6 | Create Slack step page | ⬜ | frontend/app/onboarding/slack/page.tsx |
| 5.7 | Create connections dashboard | ⬜ | frontend/app/dashboard/connections/page.tsx |
| 5.8 | Create ConnectionCard | ⬜ | frontend/components/connections/ConnectionCard.tsx |
| 5.9 | Create useIntegrations hook | ⬜ | frontend/lib/hooks/useIntegrations.ts |

### Detailed Phase 5 Tasks

- [ ] **5.1**: OnboardingStepper
  - [ ] 3 steps: Google (done), Gmail, Slack
  - [ ] Visual progress indicator
  - [ ] Step status (complete, current, pending)

- [ ] **5.2**: Onboarding main page
  - [ ] Fetch onboarding status
  - [ ] Route to current step

- [ ] **5.3**: GmailConnectCard
  - [ ] Gmail icon
  - [ ] "Connect Gmail" button
  - [ ] Scopes explanation
  - [ ] Connected/disconnected state

- [ ] **5.4**: Gmail step page
  - [ ] Use GmailConnectCard
  - [ ] Show what permissions are needed
  - [ ] "Skip for now" option

- [ ] **5.5**: SlackConnectCard
  - [ ] Slack icon
  - [ ] "Add to Slack" button
  - [ ] Workspace selection if multiple

- [ ] **5.6**: Slack step page
  - [ ] Use SlackConnectCard
  - [ ] Explain bot functionality
  - [ ] "Skip for now" option
  - [ ] "Complete Setup" button

- [ ] **5.7**: Connections dashboard
  - [ ] List all integrations
  - [ ] Status indicators
  - [ ] Disconnect buttons
  - [ ] Re-connect options

- [ ] **5.8**: ConnectionCard
  - [ ] Provider icon
  - [ ] Connection status
  - [ ] Connected date
  - [ ] Disconnect/reconnect action

- [ ] **5.9**: useIntegrations hook
  - [ ] Fetch integration status
  - [ ] Connect/disconnect methods
  - [ ] Loading states

---

## Phase 6: Testing & Polish

| # | Task | Status | Files |
|---|------|--------|-------|
| 6.1 | E2E tests setup | ⬜ | tests/e2e/ |
| 6.2 | E2E login flow | ⬜ | tests/e2e/test_login.py |
| 6.3 | E2E onboarding flow | ⬜ | tests/e2e/test_onboarding.py |
| 6.4 | Add loading states | ⬜ | frontend/components/ |
| 6.5 | Add error boundaries | ⬜ | frontend/app/error.tsx |
| 6.6 | Add docker-compose | ⬜ | docker-compose.yml |

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

- [ ] **6.4**: Loading states
  - [ ] Login button loading
  - [ ] Connect button loading
  - [ ] Page transitions

- [ ] **6.5**: Error boundaries
  - [ ] Global error boundary
  - [ ] OAuth error page
  - [ ] Network error handling

- [ ] **6.6**: Docker compose
  - [ ] PostgreSQL service
  - [ ] Redis service
  - [ ] API service
  - [ ] Frontend service (optional)

---

## DevOps Tasks

| # | Task | Status | Files |
|---|------|--------|-------|
| O1 | Create .env.example | ⬜ | .env.example |
| O2 | Create Dockerfile.api | ⬜ | Dockerfile.api |
| O3 | Create docker-compose.yml | ⬜ | docker-compose.yml |

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
| Phase 1: Foundation | 0 | 9 | 0% |
| Phase 2: Google OAuth | 0 | 9 | 0% |
| Phase 3: Integrations | 0 | 7 | 0% |
| Phase 4: Frontend Auth | 0 | 6 | 0% |
| Phase 5: Onboarding | 0 | 9 | 0% |
| Phase 6: Testing | 0 | 6 | 0% |
| DevOps | 0 | 3 | 0% |
| Documentation | 0 | 3 | 0% |
| **TOTAL** | **0** | **52** | **0%** |

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
