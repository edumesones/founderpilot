/**
 * AnimatedBadge component for status indicators
 * Provides badge with optional pulse animation and glow effect
 */

"use client";

import { motion } from "framer-motion";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { type ReactNode } from "react";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-all duration-200",
  {
    variants: {
      variant: {
        success:
          "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800",
        warning:
          "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 border border-yellow-200 dark:border-yellow-800",
        error:
          "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800",
        info: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800",
      },
    },
    defaultVariants: {
      variant: "info",
    },
  }
);

interface AnimatedBadgeProps extends VariantProps<typeof badgeVariants> {
  children: ReactNode;
  pulse?: boolean;
  className?: string;
}

/**
 * AnimatedBadge component
 *
 * @param variant - Badge style: "success", "warning", "error", "info"
 * @param pulse - Enable pulse animation
 *
 * @example
 * ```tsx
 * <AnimatedBadge variant="success" pulse>
 *   Active
 * </AnimatedBadge>
 * ```
 */
export function AnimatedBadge({
  children,
  variant,
  pulse = false,
  className,
}: AnimatedBadgeProps) {
  return (
    <motion.span
      className={cn(badgeVariants({ variant }), className)}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{
        type: "spring",
        stiffness: 300,
        damping: 25,
      }}
      whileHover={{
        scale: 1.05,
        boxShadow: "0 0 12px rgba(0, 0, 0, 0.15)",
        transition: { duration: 0.2 },
      }}
    >
      {pulse && (
        <motion.span
          className={cn(
            "h-2 w-2 rounded-full",
            variant === "success" && "bg-green-500",
            variant === "warning" && "bg-yellow-500",
            variant === "error" && "bg-red-500",
            variant === "info" && "bg-blue-500"
          )}
          animate={{
            scale: [1, 1.2, 1],
            opacity: [1, 0.7, 1],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      )}
      {children}
    </motion.span>
  );
}
