# FEAT-010: Fix UI - Frontend Bug Fixes

## Summary

Fix all frontend issues introduced during FEAT-009 (Frontend Polish). The build is broken and there are runtime issues throughout the login flow and beyond.

**Priority:** P0 - Build is broken
**Type:** Bug fix

---

## Known Issues

### Build-Breaking (P0)

1. **Wrong import path for StaggerContainer**
   - File: `src/app/dashboard/connections/page.tsx:14`
   - Error: `Module not found: Can't resolve '@/components/animated/StaggerContainer'`
   - Fix: Import from `@/components/layout/StaggerContainer`

2. **Invalid AnimatedBadge variant**
   - File: `src/components/connections/ConnectionCard.tsx:67`
   - Error: `"default"` is not a valid variant (only success/warning/error/info)
   - Fix: Use `"info"` instead of `"default"`

### Runtime Issues (To Investigate)

3. **Login flow issues** - User reported problems from login onwards
4. **Additional runtime errors** - Need to start dev server and test each page

---

## Acceptance Criteria

- [ ] `npm run build` succeeds with 0 errors
- [ ] Login page renders correctly
- [ ] Auth callback works
- [ ] Dashboard loads after login
- [ ] All pages accessible without console errors
- [ ] All animated components render properly
- [ ] Dark mode works correctly

---

## Technical Decisions

| # | Decision | Value | Rationale |
|---|----------|-------|-----------|
| 1 | Approach | Fix in place | Minimal changes, fix only what's broken |
| 2 | Testing | Build + dev server | Verify build then runtime |

---

## Scope

### In Scope
- Fix all build errors
- Fix all runtime errors from login flow
- Fix component import/export issues
- Fix type errors

### Out of Scope
- New features
- Design changes
- Performance optimization
- Backend fixes

---

*Created: 2026-02-04*
*Status: Interview Complete*
