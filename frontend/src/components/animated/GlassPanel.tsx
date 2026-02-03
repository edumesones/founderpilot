/**
 * GlassPanel component - Reusable glass container
 * Provides a glassmorphism container without animations
 */

import { cn } from "@/lib/utils";
import { type ReactNode, type HTMLAttributes } from "react";

interface GlassPanelProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  className?: string;
}

/**
 * GlassPanel component
 *
 * A static glass-effect container (no animations).
 * Use AnimatedCard if you need animations.
 *
 * @example
 * ```tsx
 * <GlassPanel>
 *   <h2>Glass Panel Content</h2>
 * </GlassPanel>
 * ```
 */
export function GlassPanel({
  children,
  className,
  ...props
}: GlassPanelProps) {
  return (
    <div
      className={cn(
        "rounded-xl p-6",
        "bg-[var(--glass-bg-solid)] backdrop-blur-[var(--glass-blur)]",
        "border border-[var(--glass-border)]",
        "shadow-[var(--shadow-glass)]",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
