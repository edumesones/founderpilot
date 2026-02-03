# Animation & Glassmorphism Guide

Complete guide for using animations and glassmorphism design system in ExecutivePilot/FounderPilot.

## Table of Contents

1. [Design Principles](#design-principles)
2. [Glassmorphism Style](#glassmorphism-style)
3. [Animation Guidelines](#animation-guidelines)
4. [Component Usage](#component-usage)
5. [Performance](#performance)
6. [Accessibility](#accessibility)

---

## Design Principles

### Visual Hierarchy
1. **Primary actions:** Gradient buttons with scale hover
2. **Secondary actions:** Ghost/outline buttons with subtle hover
3. **Content cards:** Glass effect with backdrop blur
4. **Modals/Overlays:** Backdrop blur + glass container

### Motion Philosophy
- **Purposeful:** Every animation should have meaning
- **Natural:** Use spring physics for organic feel
- **Fast:** Micro-interactions <200ms, transitions <600ms
- **Respectful:** Always support reduced motion

---

## Glassmorphism Style

### What is Glassmorphism?

A design trend featuring:
- Semi-transparent backgrounds
- Backdrop blur effects
- Subtle borders
- Layered depth

### CSS Variables

Defined in `globals.css`:

```css
:root {
  /* Glass effects */
  --glass-bg: rgba(255, 255, 255, 0.1);
  --glass-bg-solid: rgba(255, 255, 255, 0.7);
  --glass-border: rgba(255, 255, 255, 0.2);
  --glass-blur: 10px;

  /* Gradients */
  --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  --gradient-success: linear-gradient(135deg, #10b981 0%, #059669 100%);
  --gradient-warning: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  --gradient-error: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);

  /* Shadows */
  --shadow-glass: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
  --shadow-glass-hover: 0 12px 48px 0 rgba(31, 38, 135, 0.25);
}

.dark {
  --glass-bg: rgba(0, 0, 0, 0.3);
  --glass-bg-solid: rgba(0, 0, 0, 0.7);
  --glass-border: rgba(255, 255, 255, 0.1);
  --shadow-glass: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
  --shadow-glass-hover: 0 12px 48px 0 rgba(0, 0, 0, 0.5);
}
```

### Using Glass Effects

**Recommended:**
```tsx
<AnimatedCard variant="glass">
  {content}
</AnimatedCard>
```

**Custom:**
```tsx
<div className="
  bg-[var(--glass-bg-solid)]
  backdrop-blur-[var(--glass-blur)]
  border border-[var(--glass-border)]
  shadow-[var(--shadow-glass)]
  rounded-xl
">
  {content}
</div>
```

---

## Animation Guidelines

### Duration & Easing

| Type | Duration | Easing | Use Case |
|------|----------|--------|----------|
| Micro-interactions | 150-250ms | Spring (stiffness: 400) | Hover, tap, focus |
| Transitions | 300-400ms | Spring (stiffness: 300) | Card entrance, button clicks |
| Page changes | 400-600ms | Ease-in-out | Route transitions |
| Modals | 300-500ms | Spring (damping: 30) | Modal open/close |

### Spring Physics

**Fast & Snappy:**
```ts
{ type: "spring", stiffness: 400, damping: 25 }
```

**Smooth & Natural:**
```ts
{ type: "spring", stiffness: 300, damping: 30 }
```

**Slow & Bouncy:**
```ts
{ type: "spring", stiffness: 200, damping: 20 }
```

### Animation Types

**1. Entrance Animations**
```tsx
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ type: "spring", stiffness: 300, damping: 30 }}
>
  Content
</motion.div>
```

**2. Hover Effects**
```tsx
<motion.button
  whileHover={{ scale: 1.05 }}
  whileTap={{ scale: 0.95 }}
>
  Click me
</motion.button>
```

**3. Stagger Lists**
```tsx
<StaggerContainer staggerDelay={0.1}>
  {items.map(item => (
    <motion.div key={item.id} variants={staggerItem}>
      {item.content}
    </motion.div>
  ))}
</StaggerContainer>
```

**4. Number Counters**
```tsx
import { useSpring, useTransform } from "framer-motion";

const spring = useSpring(0, { stiffness: 100, damping: 30 });
const display = useTransform(spring, (current) =>
  Math.round(current).toString()
);

useEffect(() => {
  spring.set(targetValue);
}, [targetValue]);

return <motion.span>{display}</motion.span>;
```

---

## Component Usage

### Page Structure

```tsx
import { PageTransition } from "@/components/layout";
import { AnimatedCard, AnimatedButton } from "@/components/animated";

export default function MyPage() {
  return (
    <PageTransition>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
        {/* Glass header */}
        <header className="
          bg-[var(--glass-bg-solid)]
          backdrop-blur-[var(--glass-blur)]
          border-b border-[var(--glass-border)]
        ">
          <h1>Page Title</h1>
        </header>

        {/* Content */}
        <main className="max-w-7xl mx-auto p-8">
          <AnimatedCard variant="glass" hover>
            <h2>Card Title</h2>
            <p>Card content</p>
            <AnimatedButton variant="primary">
              Take Action
            </AnimatedButton>
          </AnimatedCard>
        </main>
      </div>
    </PageTransition>
  );
}
```

### Modal Pattern

```tsx
const [open, setOpen] = useState(false);

<AnimatedButton onClick={() => setOpen(true)}>
  Open Modal
</AnimatedButton>

<AnimatedModal
  open={open}
  onClose={() => setOpen(false)}
  title="Confirmation"
>
  <p>Are you sure?</p>
  <div className="flex gap-3 mt-6">
    <AnimatedButton variant="primary" onClick={handleConfirm}>
      Confirm
    </AnimatedButton>
    <AnimatedButton variant="ghost" onClick={() => setOpen(false)}>
      Cancel
    </AnimatedButton>
  </div>
</AnimatedModal>
```

### Loading States

```tsx
{loading ? (
  <LoadingSkeleton variant="rect" height={100} count={3} />
) : (
  <AnimatedTable headers={headers} rows={rows} />
)}
```

---

## Performance

### Do's ✅

- Use `maxStagger` to limit animated items
- Use LoadingSkeleton for loading states
- Respect `prefers-reduced-motion`
- Test on low-end devices
- Monitor FPS in Chrome DevTools

### Don'ts ❌

- Don't animate large lists without virtualization
- Don't nest multiple glass effects deeply
- Don't use `will-change` everywhere
- Don't ignore layout shift (CLS)
- Don't animate expensive properties (width, height)

### Performance Budgets

| Metric | Target |
|--------|--------|
| Lighthouse Performance | > 90 |
| First Contentful Paint | < 1.5s |
| Time to Interactive | < 3s |
| Animation FPS | 60fps |
| Bundle size increase | < 60KB |

---

## Accessibility

### Keyboard Navigation

All interactive elements support keyboard:
- `Tab` - Focus next
- `Shift + Tab` - Focus previous
- `Enter/Space` - Activate
- `Esc` - Close modals

### Focus Management

```tsx
<AnimatedModal open={open} onClose={onClose}>
  {/* Focus is automatically trapped inside */}
</AnimatedModal>
```

### Reduced Motion

Automatically handled by all components:

```tsx
import { getMotionConfig } from "@/lib/animation-config";

<motion.div {...getMotionConfig()}>
  {/* Animations disabled if user prefers reduced motion */}
</motion.div>
```

### ARIA Labels

```tsx
<AnimatedButton aria-label="Close modal">
  <CloseIcon />
</AnimatedButton>
```

### Color Contrast

All components meet WCAG AA:
- Normal text: 4.5:1
- Large text: 3:1
- Interactive elements: 3:1

---

## Examples

### Dashboard Card

```tsx
<AnimatedCard variant="glass" hover className="p-6">
  <div className="flex items-center justify-between mb-4">
    <h3 className="text-lg font-semibold">Usage This Month</h3>
    <AnimatedButton variant="ghost" size="sm">
      Refresh
    </AnimatedButton>
  </div>

  <AnimatedProgress
    value={75}
    max={100}
    showPercentage
    variant="gradient"
  />

  <div className="mt-4 flex gap-2">
    <AnimatedBadge variant="success" pulse>
      Active
    </AnimatedBadge>
    <AnimatedBadge variant="warning">
      80% used
    </AnimatedBadge>
  </div>
</AnimatedCard>
```

### Form with Validation

```tsx
<form className="space-y-4">
  <AnimatedInput
    label="Email"
    type="email"
    value={email}
    onChange={(e) => setEmail(e.target.value)}
    error={errors.email}
  />

  <AnimatedInput
    label="Password"
    type="password"
    value={password}
    onChange={(e) => setPassword(e.target.value)}
    error={errors.password}
  />

  <AnimatedButton
    type="submit"
    variant="primary"
    loading={submitting}
    className="w-full"
  >
    Sign In
  </AnimatedButton>
</form>
```

---

## Browser Support

| Browser | Version | Glass Effects | Animations |
|---------|---------|---------------|------------|
| Chrome | 76+ | ✅ | ✅ |
| Firefox | 103+ | ✅ | ✅ |
| Safari | 9+ | ✅ (with -webkit-) | ✅ |
| Edge | 79+ | ✅ | ✅ |

**Fallback:** Semi-transparent background without blur on unsupported browsers.

---

*Last updated: 2026-02-03*
