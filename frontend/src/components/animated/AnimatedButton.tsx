/**
 * AnimatedButton component with variants and animations
 * Provides consistent button styling with hover/tap effects
 */

"use client";

import { motion, type HTMLMotionProps } from "framer-motion";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { hoverScaleLarge, tapScale } from "@/lib/animation-config";
import { type ReactNode } from "react";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
  {
    variants: {
      variant: {
        primary:
          "bg-gradient-to-br from-[#667eea] to-[#764ba2] text-white shadow-md hover:shadow-lg",
        secondary:
          "bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 shadow-sm hover:shadow-md",
        ghost:
          "bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300",
        outline:
          "bg-transparent border-2 border-[#667eea] text-[#667eea] hover:bg-[#667eea] hover:text-white",
      },
      size: {
        sm: "px-3 py-1.5 text-sm",
        md: "px-4 py-2 text-base",
        lg: "px-6 py-3 text-lg",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

interface AnimatedButtonProps
  extends Omit<HTMLMotionProps<"button">, "children">,
    VariantProps<typeof buttonVariants> {
  children: ReactNode;
  loading?: boolean;
  disabled?: boolean;
}

/**
 * AnimatedButton component
 *
 * @param variant - Button style: "primary", "secondary", "ghost", "outline"
 * @param size - Button size: "sm", "md", "lg"
 * @param loading - Show loading spinner
 * @param disabled - Disable button interaction
 *
 * @example
 * ```tsx
 * <AnimatedButton variant="primary" size="md" onClick={() => console.log('clicked')}>
 *   Click Me
 * </AnimatedButton>
 * ```
 */
export function AnimatedButton({
  children,
  variant,
  size,
  loading = false,
  disabled = false,
  className,
  ...props
}: AnimatedButtonProps) {
  return (
    <motion.button
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      whileHover={!disabled && !loading ? hoverScaleLarge : undefined}
      whileTap={!disabled && !loading ? tapScale : undefined}
      transition={{
        type: "spring",
        stiffness: 400,
        damping: 25,
      }}
      {...props}
    >
      {loading && (
        <motion.div
          className="h-4 w-4 rounded-full border-2 border-current border-t-transparent"
          animate={{ rotate: 360 }}
          transition={{
            duration: 1,
            repeat: Infinity,
            ease: "linear",
          }}
        />
      )}
      {children}
    </motion.button>
  );
}
