/**
 * PageTransition component for route animations
 * Provides smooth transitions between pages
 */

"use client";

import { motion, AnimatePresence } from "framer-motion";
import { usePathname } from "next/navigation";
import { type ReactNode } from "react";
import { pageTransitionConfig } from "@/lib/animation-config";

interface PageTransitionProps {
  children: ReactNode;
}

/**
 * PageTransition component
 *
 * Wraps page content to provide fade/slide transitions on route change.
 * Place in layout.tsx to apply to all pages.
 *
 * @example
 * ```tsx
 * // In layout.tsx
 * <PageTransition>
 *   {children}
 * </PageTransition>
 * ```
 */
export function PageTransition({ children }: PageTransitionProps) {
  const pathname = usePathname();

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={pathname}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={pageTransitionConfig}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
