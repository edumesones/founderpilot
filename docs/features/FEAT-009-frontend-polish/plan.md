# FEAT-009: Frontend Polish - Implementation Plan

**Date:** 2026-02-03
**Phase:** Plan (3/8)
**Status:** Ready for approval
**Estimated effort:** 20-25 hours (3-4 days)

---

## Plan Overview

**Strategy:** Component-first approach with incremental integration

**Phases:**
1. **Setup** (1h) - Dependencies + configuration
2. **Component Library** (8h) - Build 15 animated components
3. **Page Integration** (8h) - Apply to all 10 pages
4. **Polish & Testing** (3h) - Performance, accessibility, visual QA
5. **Documentation** (1h) - Component docs + migration guide

**Total:** 21 hours estimated

---

## Task Breakdown

### Phase 1: Setup & Dependencies (3 tasks, ~1h)

#### Task 1.1: Install Dependencies
**Estimated:** 15min
**Files:** `frontend/package.json`

```bash
cd frontend
npm install framer-motion@^11 \
  @radix-ui/react-dialog@^1 \
  @radix-ui/react-dropdown-menu@^2 \
  @radix-ui/react-tooltip@^1 \
  @radix-ui/react-progress@^1 \
  class-variance-authority@^0.7 \
  clsx@^2 \
  tailwind-merge@^2
```

**Acceptance:**
- [ ] All dependencies installed
- [ ] `package-lock.json` updated
- [ ] No version conflicts
- [ ] `npm run build` succeeds

---

#### Task 1.2: Configure Tailwind for Glassmorphism
**Estimated:** 20min
**Files:** `frontend/src/app/globals.css`

Add CSS custom properties for glass effects:

```css
:root {
  /* Glass effects */
  --glass-bg: rgba(255, 255, 255, 0.1);
  --glass-border: rgba(255, 255, 255, 0.2);
  --glass-blur: 10px;

  /* Gradients */
  --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

  /* Shadows */
  --shadow-glass: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
}

.dark {
  --glass-bg: rgba(0, 0, 0, 0.3);
  --glass-border: rgba(255, 255, 255, 0.1);
}
```

**Acceptance:**
- [ ] CSS variables defined
- [ ] Dark mode variants included
- [ ] No conflicts with existing styles

---

#### Task 1.3: Create Utility Functions
**Estimated:** 25min
**Files:**
- `frontend/src/lib/utils.ts` (create)
- `frontend/src/lib/animation-config.ts` (create)

**utils.ts:**
```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**animation-config.ts:**
```ts
import { Variants } from "framer-motion";

// Spring presets
export const springConfig = {
  type: "spring",
  stiffness: 300,
  damping: 30,
};

// Animation variants
export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

export const slideUp: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: { opacity: 1, scale: 1 },
};

export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};
```

**Acceptance:**
- [ ] Both utility files created
- [ ] TypeScript compiles without errors
- [ ] Exports are correct

---

### Phase 2: Component Library (12 tasks, ~8h)

#### Task 2.1: Create AnimatedCard Component
**Estimated:** 30min
**Files:** `frontend/src/components/animated/AnimatedCard.tsx`

**Features:**
- Glass effect background
- Hover scale animation
- Optional gradient border
- Variants: default, glass, glass-dark

**Props:**
```ts
interface AnimatedCardProps {
  children: React.ReactNode;
  variant?: "default" | "glass" | "glass-dark";
  hover?: boolean;
  className?: string;
}
```

**Acceptance:**
- [ ] Component renders with glass effect
- [ ] Hover animation works (scale 1.02)
- [ ] Dark mode supported
- [ ] Accessible (proper ARIA)

---

#### Task 2.2: Create AnimatedButton Component
**Estimated:** 40min
**Files:** `frontend/src/components/animated/AnimatedButton.tsx`

**Features:**
- CVA variants (primary, secondary, ghost, outline)
- Hover effects (scale, shadow)
- Loading state with spinner
- Disabled state

**Props:**
```ts
interface AnimatedButtonProps {
  variant?: "primary" | "secondary" | "ghost" | "outline";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
}
```

**Acceptance:**
- [ ] All 4 variants render correctly
- [ ] Hover effects smooth (scale 1.05)
- [ ] Loading state shows spinner
- [ ] Keyboard accessible

---

#### Task 2.3: Create AnimatedProgress Component
**Estimated:** 35min
**Files:** `frontend/src/components/animated/AnimatedProgress.tsx`

**Features:**
- Gradient fill (uses Radix Progress)
- Animated number counter
- Shimmer effect for loading
- Color based on percentage (green/yellow/red)

**Props:**
```ts
interface AnimatedProgressProps {
  value: number;
  max?: number;
  showPercentage?: boolean;
  variant?: "default" | "gradient";
}
```

**Acceptance:**
- [ ] Progress bar animates smoothly
- [ ] Gradient renders correctly
- [ ] Color changes at 80% and 100%
- [ ] Number counter animates

---

#### Task 2.4: Create AnimatedBadge Component
**Estimated:** 25min
**Files:** `frontend/src/components/animated/AnimatedBadge.tsx`

**Features:**
- Variants: success, warning, error, info
- Optional pulse animation
- Glow effect on hover

**Props:**
```ts
interface AnimatedBadgeProps {
  variant?: "success" | "warning" | "error" | "info";
  pulse?: boolean;
  children: React.ReactNode;
}
```

**Acceptance:**
- [ ] All variants render with correct colors
- [ ] Pulse animation works
- [ ] Glow effect on hover

---

#### Task 2.5: Create AnimatedModal Component
**Estimated:** 45min
**Files:** `frontend/src/components/animated/AnimatedModal.tsx`

**Features:**
- Uses Radix Dialog
- Slide-in animation from bottom
- Backdrop blur
- Focus trap
- ESC to close

**Props:**
```ts
interface AnimatedModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
}
```

**Acceptance:**
- [ ] Modal slides in from bottom
- [ ] Backdrop has blur effect
- [ ] Focus trapped in modal
- [ ] ESC closes modal
- [ ] Click outside closes modal

---

#### Task 2.6: Create AnimatedInput Component
**Estimated:** 30min
**Files:** `frontend/src/components/animated/AnimatedInput.tsx`

**Features:**
- Focus ring animation
- Label float animation
- Error state

**Props:**
```ts
interface AnimatedInputProps {
  label?: string;
  error?: string;
  type?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
}
```

**Acceptance:**
- [ ] Focus ring animates in
- [ ] Label floats on focus
- [ ] Error state shows red border

---

#### Task 2.7: Create AnimatedTable Component
**Estimated:** 40min
**Files:** `frontend/src/components/animated/AnimatedTable.tsx`

**Features:**
- Row stagger animation on mount
- Hover row highlight
- Sort animation
- Virtualization support (via prop)

**Props:**
```ts
interface AnimatedTableProps {
  headers: string[];
  rows: any[][];
  onRowClick?: (index: number) => void;
  maxStagger?: number; // Cap at 20 rows
}
```

**Acceptance:**
- [ ] Rows stagger in (max 20)
- [ ] Hover highlights row
- [ ] Click handler works
- [ ] Performance good on 100+ rows

---

#### Task 2.8: Create LoadingSkeleton Component
**Estimated:** 25min
**Files:** `frontend/src/components/animated/LoadingSkeleton.tsx`

**Features:**
- Shimmer animation
- Configurable width/height
- Multiple variants (text, circle, rect)

**Props:**
```ts
interface LoadingSkeletonProps {
  variant?: "text" | "circle" | "rect";
  width?: string | number;
  height?: string | number;
  count?: number;
}
```

**Acceptance:**
- [ ] Shimmer animation smooth
- [ ] All variants render correctly
- [ ] Multiple skeletons render with count

---

#### Task 2.9: Create PageTransition Component
**Estimated:** 35min
**Files:** `frontend/src/components/layout/PageTransition.tsx`

**Features:**
- Wraps page content
- Fade + slide transition on route change
- Uses usePathname() to detect route change

**Props:**
```ts
interface PageTransitionProps {
  children: React.ReactNode;
}
```

**Acceptance:**
- [ ] Page transitions work on route change
- [ ] Animation duration 400ms
- [ ] No layout shift
- [ ] Works with Next.js App Router

---

#### Task 2.10: Create StaggerContainer Component
**Estimated:** 20min
**Files:** `frontend/src/components/layout/StaggerContainer.tsx`

**Features:**
- Wraps list items
- Staggers children animations
- Configurable stagger delay

**Props:**
```ts
interface StaggerContainerProps {
  children: React.ReactNode;
  staggerDelay?: number; // Default 0.1s
  maxItems?: number; // Cap stagger at N items
}
```

**Acceptance:**
- [ ] Children stagger in
- [ ] Delay configurable
- [ ] Max items respected

---

#### Task 2.11: Create GlassPanel Component
**Estimated:** 20min
**Files:** `frontend/src/components/animated/GlassPanel.tsx`

**Features:**
- Reusable glass container
- Backdrop blur
- Border glow

**Props:**
```ts
interface GlassPanelProps {
  children: React.ReactNode;
  className?: string;
}
```

**Acceptance:**
- [ ] Glass effect renders
- [ ] Backdrop blur works
- [ ] Border has subtle glow

---

#### Task 2.12: Create Animated Components Index
**Estimated:** 10min
**Files:**
- `frontend/src/components/animated/index.ts`
- `frontend/src/components/layout/index.ts`

Export all components for easy importing.

**Acceptance:**
- [ ] All components exported
- [ ] Named exports work
- [ ] No circular dependencies

---

### Phase 3: Page Integration (10 tasks, ~8h)

#### Task 3.1: Integrate Auth Login Page
**Estimated:** 45min
**Files:** `frontend/src/app/auth/login/page.tsx`

**Changes:**
- Replace div → AnimatedCard
- Replace button → AnimatedButton
- Add logo bounce animation on load
- Add glass background

**Acceptance:**
- [ ] Glass card renders
- [ ] Button animates on hover
- [ ] Logo bounces on load
- [ ] Auth flow still works

---

#### Task 3.2: Integrate Auth Callback Page
**Estimated:** 30min
**Files:** `frontend/src/app/auth/callback/page.tsx`

**Changes:**
- Add LoadingSkeleton for loading state
- Add AnimatedCard for error state

**Acceptance:**
- [ ] Loading skeleton shows during auth
- [ ] Error state uses glass card
- [ ] Redirect still works

---

#### Task 3.3: Integrate Onboarding Page
**Estimated:** 60min
**Files:**
- `frontend/src/app/onboarding/page.tsx`
- `frontend/src/components/onboarding/OnboardingStepper.tsx`

**Changes:**
- Wrap steps in StaggerContainer
- Replace cards → AnimatedCard
- Replace buttons → AnimatedButton
- Add AnimatedProgress for step indicator

**Acceptance:**
- [ ] Steps stagger in
- [ ] Progress bar animates
- [ ] Cards have glass effect
- [ ] Onboarding flow works

---

#### Task 3.4: Integrate Dashboard Home Page
**Estimated:** 45min
**Files:** `frontend/src/app/dashboard/page.tsx`

**Changes:**
- Wrap in PageTransition
- Replace cards → AnimatedCard
- Replace buttons → AnimatedButton
- Add glass header

**Acceptance:**
- [ ] Page transition works
- [ ] All cards use glass effect
- [ ] Header has glass background
- [ ] Links still work

---

#### Task 3.5: Integrate UsageWidget
**Estimated:** 50min
**Files:** `frontend/src/components/usage/UsageWidget.tsx`

**Changes:**
- Wrap in AnimatedCard
- Replace progress bars → AnimatedProgress
- Replace alerts → AnimatedBadge
- Add number counter animations

**Acceptance:**
- [ ] Widget has glass effect
- [ ] Progress bars animate
- [ ] Alerts have badges
- [ ] Numbers count up on load
- [ ] Auto-refresh still works

---

#### Task 3.6: Integrate Connections Page
**Estimated:** 45min
**Files:**
- `frontend/src/app/dashboard/connections/page.tsx`
- `frontend/src/components/connections/ConnectionCard.tsx`

**Changes:**
- Wrap cards in StaggerContainer
- Replace cards → AnimatedCard
- Add status badge animations

**Acceptance:**
- [ ] Cards stagger in
- [ ] Status badges animate
- [ ] Hover effects work
- [ ] Connection logic works

---

#### Task 3.7: Integrate Audit Dashboard Page
**Estimated:** 60min
**Files:**
- `frontend/src/app/dashboard/audit/page.tsx`
- `frontend/src/components/audit/AuditTable.tsx`
- `frontend/src/components/audit/AuditDetailModal.tsx`

**Changes:**
- Replace table → AnimatedTable
- Replace modal → AnimatedModal
- Add row animations
- Add glass panel for filters

**Acceptance:**
- [ ] Table rows animate in
- [ ] Modal slides from bottom
- [ ] Backdrop blur works
- [ ] Audit data displays correctly
- [ ] Modal interactions work

---

#### Task 3.8: Integrate Error Page
**Estimated:** 20min
**Files:** `frontend/src/app/error.tsx`

**Changes:**
- Add AnimatedCard for error message
- Add bounce animation for icon

**Acceptance:**
- [ ] Error card has glass effect
- [ ] Icon bounces on load
- [ ] Error message displays

---

#### Task 3.9: Integrate 404 Page
**Estimated:** 20min
**Files:** `frontend/src/app/not-found.tsx`

**Changes:**
- Add AnimatedCard
- Add bounce animation for 404 text

**Acceptance:**
- [ ] Card has glass effect
- [ ] 404 text animates

---

#### Task 3.10: Integrate Root Layout
**Estimated:** 30min
**Files:** `frontend/src/app/layout.tsx`

**Changes:**
- Add PageTransition wrapper
- Add glass background pattern

**Acceptance:**
- [ ] Page transitions work globally
- [ ] Background pattern subtle
- [ ] No layout shift
- [ ] All pages still load

---

### Phase 4: Polish & Testing (4 tasks, ~3h)

#### Task 4.1: Performance Optimization
**Estimated:** 60min

**Actions:**
- Add `will-change` only where needed
- Implement dynamic imports for AnimatedModal
- Add virtualization for long lists
- Test on low-end device

**Acceptance:**
- [ ] Lighthouse Performance > 90
- [ ] Animation FPS stable at 60fps
- [ ] No jank on scroll
- [ ] Modal loads lazily

---

#### Task 4.2: Accessibility Audit
**Estimated:** 45min

**Actions:**
- Add ARIA labels to all interactive elements
- Test keyboard navigation
- Add focus indicators
- Test with screen reader
- Implement prefers-reduced-motion

**Acceptance:**
- [ ] Lighthouse Accessibility > 95
- [ ] All elements keyboard accessible
- [ ] Focus indicators visible
- [ ] Reduced motion disables animations

---

#### Task 4.3: Dark Mode Testing
**Estimated:** 30min

**Actions:**
- Test all pages in dark mode
- Validate glass effect contrast
- Check color accessibility

**Acceptance:**
- [ ] All pages look good in dark mode
- [ ] Glass effects have correct colors
- [ ] WCAG AA contrast met

---

#### Task 4.4: Visual QA
**Estimated:** 45min

**Actions:**
- Test on Chrome, Firefox, Safari
- Test responsive breakpoints
- Check animation smoothness
- Validate design consistency

**Acceptance:**
- [ ] All browsers render correctly
- [ ] Mobile/tablet responsive
- [ ] Animations smooth across browsers
- [ ] Design consistent across pages

---

### Phase 5: Documentation (2 tasks, ~1h)

#### Task 5.1: Component Documentation
**Estimated:** 40min
**Files:** `frontend/src/components/animated/README.md`

**Contents:**
- Component usage examples
- Props documentation
- Animation configuration guide
- Performance tips

**Acceptance:**
- [ ] All components documented
- [ ] Examples provided
- [ ] Props table complete

---

#### Task 5.2: Migration Guide
**Estimated:** 20min
**Files:** `frontend/ANIMATION_GUIDE.md`

**Contents:**
- How to use animated components
- Glassmorphism style guide
- Performance best practices
- Accessibility guidelines

**Acceptance:**
- [ ] Guide complete
- [ ] Examples clear
- [ ] Best practices documented

---

## Performance Budgets

| Metric | Target | Validation |
|--------|--------|------------|
| Lighthouse Performance | > 90 | Lighthouse CI |
| Lighthouse Accessibility | > 95 | Lighthouse CI |
| First Contentful Paint | < 1.5s | Lighthouse |
| Time to Interactive | < 3s | Lighthouse |
| Cumulative Layout Shift | < 0.1 | Lighthouse |
| Animation FPS | 60fps | Chrome DevTools |
| Bundle size increase | < 60KB | webpack-bundle-analyzer |

---

## Testing Strategy

### Unit Tests (Optional - defer to post-MVP)
- Component rendering with different props
- Animation state transitions
- Accessibility attributes

### Integration Tests
- Page transitions
- Modal interactions
- Form submissions with animated inputs

### Visual QA (Manual)
- All pages in light/dark mode
- Responsive breakpoints (mobile, tablet, desktop)
- Browser compatibility (Chrome, Firefox, Safari)
- Animation smoothness

### Performance Tests
- Lighthouse CI on each page
- FPS monitoring during animations
- Bundle size analysis

---

## Risk Mitigation Plan

| Risk | Mitigation | Task |
|------|------------|------|
| Performance degradation | Add performance monitoring, reduce blur on mobile | Task 4.1 |
| Bundle size >60KB | Dynamic imports for modals, tree-shaking | Task 4.1 |
| Animation tuning takes too long | Use preset spring values, time-box tuning | All tasks |
| Dark mode edge cases | Systematic testing with prefers-color-scheme | Task 4.3 |
| Accessibility issues | Audit with axe-core, test keyboard nav | Task 4.2 |

---

## Dependencies

**Requires:**
- ✅ FEAT-008 Usage Tracking (merged)
- ✅ Node.js 18+
- ✅ Tailwind CSS v4

**Blocks:**
- Nothing (visual polish layer)

---

## Open Questions for Implementation

1. **Storybook:** Defer to post-MVP ✅ (decided)
2. **Dark mode toggle:** Use auto-detect only ✅ (decided)
3. **Virtualization library:** Use react-window if needed ✅ (decided)
4. **Animation duration:** Use presets (200-400ms micro, 400-600ms transitions) ✅ (decided)

---

## Commit Strategy

**Commits per phase:**
- Phase 1 (Setup): 1 commit
- Phase 2 (Components): 3-4 commits (group related components)
- Phase 3 (Integration): 3-4 commits (group by page type)
- Phase 4 (Polish): 2 commits (performance + accessibility)
- Phase 5 (Docs): 1 commit

**Total:** ~10-12 commits

**Commit message format:**
```
feat(FEAT-009): <brief description>

<detailed description>

Phase: <phase name>
Task: <task ID>
```

---

## Success Criteria

### Must Have (P0)
- [ ] All 10 pages have glassmorphism style
- [ ] All 15 components created and working
- [ ] Animations smooth (60fps)
- [ ] Dark mode supported
- [ ] Accessibility WCAG AA compliant
- [ ] Performance budgets met

### Should Have (P1)
- [ ] Keyboard navigation excellent
- [ ] Reduced motion support
- [ ] Component documentation complete
- [ ] Migration guide written

### Nice to Have (P2)
- [ ] Storybook stories (deferred)
- [ ] Unit test coverage (deferred)
- [ ] E2E animation tests (deferred)

---

## Rollback Plan

If critical issues arise:
1. **Performance issues:** Revert to previous commit, disable animations
2. **Browser compatibility:** Add feature detection, graceful degradation
3. **Accessibility issues:** Fix immediately or revert
4. **Bundle size too large:** Remove Radix components, use simpler alternatives

---

## Approval

**Plan status:** ✅ **READY FOR APPROVAL**

**Estimated effort:** 21 hours (3-4 days)
**Task count:** 31 tasks
**Confidence:** 85%

**Next step:** Create branch and begin implementation (Phase 4)

---

*Plan created: 2026-02-03 15:15*
*Last updated: 2026-02-03 15:15*
