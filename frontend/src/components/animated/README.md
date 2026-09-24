# Animated Components Library

Glassmorphism design system with Framer Motion animations for ExecutivePilot/FounderPilot.

## Overview

This library provides 11 pre-built animated components with glassmorphism effects, dark mode support, and accessibility features.

## Components

### AnimatedCard

Glass-effect card with optional hover animation.

```tsx
import { AnimatedCard } from "@/components/animated";

<AnimatedCard variant="glass" hover>
  <h2>Card Title</h2>
  <p>Card content</p>
</AnimatedCard>
```

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| variant | "default" \| "glass" \| "glass-dark" | "glass" | Visual style |
| hover | boolean | true | Enable hover scale animation |
| className | string | - | Additional CSS classes |

---

### AnimatedButton

Button with CVA variants and loading state.

```tsx
import { AnimatedButton } from "@/components/animated";

<AnimatedButton
  variant="primary"
  size="md"
  loading={isLoading}
  onClick={handleClick}
>
  Click Me
</AnimatedButton>
```

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| variant | "primary" \| "secondary" \| "ghost" \| "outline" | "primary" | Button style |
| size | "sm" \| "md" \| "lg" | "md" | Button size |
| loading | boolean | false | Show loading spinner |
| disabled | boolean | false | Disable interaction |

---

### AnimatedProgress

Progress bar with gradient and animated number counter.

```tsx
import { AnimatedProgress } from "@/components/animated";

<AnimatedProgress
  value={75}
  max={100}
  showPercentage
  variant="gradient"
/>
```

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | number | - | Current progress value |
| max | number | 100 | Maximum value |
| showPercentage | boolean | true | Display percentage text |
| variant | "default" \| "gradient" | "gradient" | Style (gradient recommended) |

**Auto-colors:** Green (<80%), Yellow (80-99%), Red (≥100%)

---

### AnimatedBadge

Status badge with optional pulse animation.

```tsx
import { AnimatedBadge } from "@/components/animated";

<AnimatedBadge variant="success" pulse>
  Active
</AnimatedBadge>
```

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| variant | "success" \| "warning" \| "error" \| "info" | "info" | Badge color |
| pulse | boolean | false | Enable pulse animation |

---

### AnimatedModal

Modal with slide-in animation and backdrop blur.

```tsx
import { AnimatedModal } from "@/components/animated";

const [open, setOpen] = useState(false);

<AnimatedModal
  open={open}
  onClose={() => setOpen(false)}
  title="Modal Title"
>
  <p>Modal content</p>
</AnimatedModal>
```

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| open | boolean | - | Control visibility |
| onClose | () => void | - | Callback when closed |
| title | string | - | Optional modal title |
| children | ReactNode | - | Modal content |

**Features:**
- Slide-in from bottom
- Backdrop blur
- Focus trap
- ESC to close
- Click outside to close

---

### AnimatedInput

Input with focus ring animation and floating label.

```tsx
import { AnimatedInput } from "@/components/animated";

<AnimatedInput
  label="Email"
  type="email"
  value={email}
  onChange={(e) => setEmail(e.target.value)}
  error={emailError}
/>
```

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| label | string | - | Floating label text |
| error | string | - | Error message |
| ...rest | InputHTMLAttributes | - | All standard input props |

---

### AnimatedTable

Table with staggered row animations.

```tsx
import { AnimatedTable } from "@/components/animated";

<AnimatedTable
  headers={["Name", "Email", "Status"]}
  rows={[
    ["John Doe", "john@example.com", "Active"],
    ["Jane Smith", "jane@example.com", "Inactive"]
  ]}
  onRowClick={(index) => console.log('Clicked row:', index)}
  maxStagger={20}
/>
```

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| headers | string[] | - | Column headers |
| rows | any[][] | - | Row data (2D array) |
| onRowClick | (index: number) => void | - | Row click handler |
| maxStagger | number | 20 | Max rows to animate (performance) |

---

### LoadingSkeleton

Shimmer loading animation.

```tsx
import { LoadingSkeleton } from "@/components/animated";

<LoadingSkeleton variant="text" count={3} />
<LoadingSkeleton variant="circle" width={48} height={48} />
<LoadingSkeleton variant="rect" height={100} />
```

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| variant | "text" \| "circle" \| "rect" | "text" | Shape |
| width | string \| number | auto | Custom width |
| height | string \| number | auto | Custom height |
| count | number | 1 | Number of skeletons |

---

### GlassPanel

Static glass container (no animations).

```tsx
import { GlassPanel } from "@/components/animated";

<GlassPanel>
  <h2>Glass Panel Content</h2>
</GlassPanel>
```

Use AnimatedCard if you need animations.

---

## Layout Components

### PageTransition

Route transition wrapper.

```tsx
// In layout.tsx or page.tsx
import { PageTransition } from "@/components/layout";

<PageTransition>
  {children}
</PageTransition>
```

**Features:**
- Fade + slide on route change
- 400ms duration
- Automatic with Next.js App Router

---

### StaggerContainer

List animation wrapper.

```tsx
import { StaggerContainer } from "@/components/layout";
import { motion } from "framer-motion";
import { staggerItem } from "@/lib/animation-config";

<StaggerContainer staggerDelay={0.1} maxItems={20}>
  {items.map((item) => (
    <motion.div key={item.id} variants={staggerItem}>
      {item.content}
    </motion.div>
  ))}
</StaggerContainer>
```

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| staggerDelay | number | 0.1 | Delay between items (seconds) |
| maxItems | number | 20 | Max items to animate (performance) |

---

## Animation Configuration

Import preset animations from `@/lib/animation-config`:

```tsx
import {
  fadeIn,
  slideUp,
  scaleIn,
  staggerContainer,
  staggerItem,
  hoverScale,
  tapScale,
  springConfig,
  smoothConfig,
} from "@/lib/animation-config";
```

### Presets

**Spring Physics:**
```ts
springConfig = {
  type: "spring",
  stiffness: 300,
  damping: 30,
}
```

**Variants:**
- `fadeIn` - Fade in (opacity 0→1)
- `slideUp` - Fade + slide from bottom
- `scaleIn` - Fade + scale from 95%
- `staggerContainer` - Parent for staggered lists
- `staggerItem` - Child item for staggered lists

**Hover/Tap:**
- `hoverScale` - Scale to 1.02 on hover
- `tapScale` - Scale to 0.98 on tap

---

## Performance Best Practices

### 1. Limit Stagger Animations
```tsx
<AnimatedTable maxStagger={20} /> // Cap at 20 rows
<StaggerContainer maxItems={20}> // Cap at 20 items
```

### 2. Use Dynamic Imports for Modals
```tsx
const AnimatedModal = dynamic(() =>
  import("@/components/animated").then(mod => ({ default: mod.AnimatedModal }))
);
```

### 3. Respect Reduced Motion
All components automatically respect `prefers-reduced-motion`.

### 4. Avoid Excessive Blur
Glass effects use GPU. Don't nest too many glass elements.

---

## Accessibility

All components include:
- ✅ Keyboard navigation
- ✅ Focus indicators
- ✅ ARIA labels
- ✅ Color contrast (WCAG AA)
- ✅ Reduced motion support

---

## Dark Mode

All components support dark mode via Tailwind's `dark:` prefix:

```tsx
<div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
  Content
</div>
```

Glass effects automatically adjust:
- Light mode: `rgba(255, 255, 255, 0.7)`
- Dark mode: `rgba(0, 0, 0, 0.7)`

---

## Troubleshooting

**Animations not working?**
- Ensure parent has `overflow-hidden` if needed
- Check `initial={false}` for SSR hydration issues

**Performance issues?**
- Reduce `maxStagger` on lists
- Use `will-change` sparingly
- Check FPS in Chrome DevTools

**Glass effects not showing?**
- Ensure parent has a background
- Check backdrop-filter browser support
- Verify CSS variables are loaded

---

*Last updated: 2026-02-03*
