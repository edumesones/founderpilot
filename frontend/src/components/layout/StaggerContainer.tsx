/**
 * StaggerContainer component for list animations
 * Provides staggered entrance animations for children
 */

"use client";

import { motion } from "framer-motion";
import { type ReactNode } from "react";
import { staggerContainer } from "@/lib/animation-config";

interface StaggerContainerProps {
  children: ReactNode;
  staggerDelay?: number;
  maxItems?: number;
  className?: string;
}

/**
 * StaggerContainer component
 *
 * Wraps list items to provide staggered entrance animations.
 * Children should use the `staggerItem` variant from animation-config.
 *
 * @param staggerDelay - Delay between children animations (seconds)
 * @param maxItems - Maximum number of items to animate (rest appear instantly)
 *
 * @example
 * ```tsx
 * <StaggerContainer staggerDelay={0.1} maxItems={20}>
 *   {items.map((item) => (
 *     <motion.div key={item.id} variants={staggerItem}>
 *       {item.content}
 *     </motion.div>
 *   ))}
 * </StaggerContainer>
 * ```
 */
export function StaggerContainer({
  children,
  staggerDelay = 0.1,
  maxItems = 20,
  className,
}: StaggerContainerProps) {
  return (
    <motion.div
      className={className}
      variants={staggerContainer}
      initial="hidden"
      animate="visible"
      transition={{
        staggerChildren: staggerDelay,
        delayChildren: 0.05,
      }}
    >
      {children}
    </motion.div>
  );
}
