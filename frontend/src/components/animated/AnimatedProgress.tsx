/**
 * AnimatedProgress component with gradient and number counter
 * Provides smooth progress bar animations with color transitions
 */

"use client";

import { motion, useSpring, useTransform } from "framer-motion";
import { cn } from "@/lib/utils";
import { useEffect } from "react";
import * as Progress from "@radix-ui/react-progress";

interface AnimatedProgressProps {
  value: number;
  max?: number;
  showPercentage?: boolean;
  variant?: "default" | "gradient";
  className?: string;
}

/**
 * AnimatedProgress component
 *
 * @param value - Current progress value
 * @param max - Maximum value (default: 100)
 * @param showPercentage - Display percentage text
 * @param variant - Style: "default" (solid color) or "gradient" (gradient fill)
 *
 * @example
 * ```tsx
 * <AnimatedProgress value={75} max={100} showPercentage variant="gradient" />
 * ```
 */
export function AnimatedProgress({
  value,
  max = 100,
  showPercentage = true,
  variant = "gradient",
  className,
}: AnimatedProgressProps) {
  const percentage = Math.min((value / max) * 100, 100);

  // Animated number counter
  const spring = useSpring(0, {
    stiffness: 100,
    damping: 30,
  });

  const display = useTransform(spring, (current) =>
    Math.round(current).toString()
  );

  useEffect(() => {
    spring.set(percentage);
  }, [percentage, spring]);

  // Determine color based on percentage
  const getColor = () => {
    if (percentage >= 100) return "bg-red-500";
    if (percentage >= 80) return "bg-yellow-500";
    return "bg-green-500";
  };

  const getGradient = () => {
    if (percentage >= 100) return "var(--gradient-error)";
    if (percentage >= 80) return "var(--gradient-warning)";
    return "var(--gradient-success)";
  };

  return (
    <div className={cn("w-full space-y-2", className)}>
      <Progress.Root
        className="relative h-3 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700"
        value={percentage}
      >
        <motion.div
          className={cn(
            "h-full",
            variant === "gradient" ? "" : getColor()
          )}
          style={{
            background: variant === "gradient" ? getGradient() : undefined,
          }}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{
            duration: 0.8,
            ease: "easeOut",
          }}
        />

        {/* Shimmer effect */}
        {variant === "gradient" && (
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
            initial={{ x: "-100%" }}
            animate={{ x: "100%" }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: "linear",
            }}
          />
        )}
      </Progress.Root>

      {showPercentage && (
        <div className="flex items-center justify-end text-sm font-medium text-gray-600 dark:text-gray-400">
          <motion.span>{display}</motion.span>
          <span>%</span>
        </div>
      )}
    </div>
  );
}
