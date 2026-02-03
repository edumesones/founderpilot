/**
 * LoadingSkeleton component with shimmer animation
 * Provides skeleton loading states for content
 */

"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface LoadingSkeletonProps {
  variant?: "text" | "circle" | "rect";
  width?: string | number;
  height?: string | number;
  count?: number;
  className?: string;
}

/**
 * LoadingSkeleton component
 *
 * @param variant - Skeleton shape: "text", "circle", "rect"
 * @param width - Custom width
 * @param height - Custom height
 * @param count - Number of skeletons to render
 *
 * @example
 * ```tsx
 * <LoadingSkeleton variant="text" count={3} />
 * <LoadingSkeleton variant="circle" width={48} height={48} />
 * ```
 */
export function LoadingSkeleton({
  variant = "text",
  width,
  height,
  count = 1,
  className,
}: LoadingSkeletonProps) {
  const getVariantStyles = () => {
    switch (variant) {
      case "circle":
        return "rounded-full aspect-square";
      case "rect":
        return "rounded-lg";
      case "text":
      default:
        return "rounded-md h-4";
    }
  };

  const getWidth = () => {
    if (width) return typeof width === "number" ? `${width}px` : width;
    if (variant === "circle") return "48px";
    return "100%";
  };

  const getHeight = () => {
    if (height) return typeof height === "number" ? `${height}px` : height;
    if (variant === "circle") return "48px";
    if (variant === "rect") return "100px";
    return "1rem";
  };

  const Skeleton = () => (
    <motion.div
      className={cn(
        "relative overflow-hidden bg-gray-200 dark:bg-gray-700",
        getVariantStyles(),
        className
      )}
      style={{
        width: getWidth(),
        height: getHeight(),
      }}
    >
      {/* Shimmer effect */}
      <motion.div
        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 dark:via-white/10 to-transparent"
        animate={{
          x: ["-100%", "100%"],
        }}
        transition={{
          duration: 1.5,
          repeat: Infinity,
          ease: "linear",
        }}
      />
    </motion.div>
  );

  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, index) => (
        <Skeleton key={index} />
      ))}
    </div>
  );
}
