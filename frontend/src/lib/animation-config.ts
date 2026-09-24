/**
 * Framer Motion animation configurations and presets
 * Provides consistent animation timing and variants across the app
 */

import { Transition, Variants } from "framer-motion";

/**
 * Spring physics configuration for natural motion
 * stiffness: How "tight" the spring is (higher = faster bounce)
 * damping: Friction/resistance (higher = less oscillation)
 */
export const springConfig: Transition = {
  type: "spring",
  stiffness: 300,
  damping: 30,
};

/**
 * Smooth transition without spring physics
 * Used for simpler animations where spring behavior isn't needed
 */
export const smoothConfig: Transition = {
  type: "tween",
  duration: 0.3,
  ease: "easeInOut",
};

/**
 * Page transition configuration
 * Slightly slower for smoother page changes
 */
export const pageTransitionConfig: Transition = {
  type: "tween",
  duration: 0.4,
  ease: "easeInOut",
};

/**
 * Common animation variants
 */

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: smoothConfig,
  },
};

export const slideUp: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: springConfig,
  },
};

export const slideDown: Variants = {
  hidden: { opacity: 0, y: -20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: springConfig,
  },
};

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: springConfig,
  },
};

export const scaleOut: Variants = {
  hidden: { opacity: 1, scale: 1 },
  visible: {
    opacity: 0,
    scale: 0.95,
    transition: smoothConfig,
  },
};

/**
 * Stagger container for list animations
 * Children will animate in sequence with a delay
 */
export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.05,
    },
  },
};

/**
 * Child item for stagger animations
 * Use inside StaggerContainer component
 */
export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: springConfig,
  },
};

/**
 * Modal/Dialog animation variants
 */
export const modalBackdrop: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: 0.2 },
  },
};

export const modalContent: Variants = {
  hidden: { opacity: 0, y: 50, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: springConfig,
  },
  exit: {
    opacity: 0,
    y: 50,
    scale: 0.95,
    transition: smoothConfig,
  },
};

/**
 * Hover animation configuration
 * For buttons, cards, and interactive elements
 */
export const hoverScale = {
  scale: 1.02,
  transition: { duration: 0.2 },
};

export const hoverScaleLarge = {
  scale: 1.05,
  transition: { duration: 0.2 },
};

/**
 * Tap animation (press down effect)
 */
export const tapScale = {
  scale: 0.98,
};

/**
 * Respects user's motion preferences
 * Returns reduced motion config if user prefers reduced motion
 */
export function getMotionConfig(respectsReducedMotion = true) {
  if (respectsReducedMotion && typeof window !== "undefined") {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    if (prefersReducedMotion) {
      return {
        initial: false,
        animate: { opacity: 1 },
        exit: { opacity: 0 },
        transition: { duration: 0 },
      };
    }
  }

  return {};
}
