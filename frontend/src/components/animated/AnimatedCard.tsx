/**
 * AnimatedCard component with glassmorphism effect
 * Provides a beautiful glass-style card with backdrop blur and animations
 */

"use client";

import { motion, type HTMLMotionProps } from "framer-motion";
import { cn } from "@/lib/utils";
import { hoverScale } from "@/lib/animation-config";
import { type ReactNode } from "react";

interface AnimatedCardProps extends Omit<HTMLMotionProps<"div">, "children"> {
  children: ReactNode;
  variant?: "default" | "glass" | "glass-dark";
  hover?: boolean;
  className?: string;
}

const variants = {
  default: "bg-white dark:bg-gray-900 shadow-lg",
  glass:
    "bg-[var(--glass-bg-solid)] backdrop-blur-[var(--glass-blur)] border border-[var(--glass-border)] shadow-[var(--shadow-glass)]",
  "glass-dark":
    "bg-[var(--glass-bg)] backdrop-blur-[var(--glass-blur)] border border-[var(--glass-border)] shadow-[var(--shadow-glass)]",
};

/**
 * AnimatedCard component
 *
 * @param variant - Visual style: "default" (solid), "glass" (semi-transparent), "glass-dark" (more transparent)
 * @param hover - Enable hover scale animation
 * @param className - Additional CSS classes
 *
 * @example
 * ```tsx
 * <AnimatedCard variant="glass" hover>
 *   <h2>Card Title</h2>
 *   <p>Card content</p>
 * </AnimatedCard>
 * ```
 */
export function AnimatedCard({
  children,
  variant = "glass",
  hover = true,
  className,
  ...props
}: AnimatedCardProps) {
  return (
    <motion.div
      className={cn(
        "rounded-xl p-6",
        variants[variant],
        "transition-shadow duration-300",
        className
      )}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{
        type: "spring",
        stiffness: 300,
        damping: 30,
      }}
      whileHover={hover ? hoverScale : undefined}
      {...props}
    >
      {children}
    </motion.div>
  );
}
