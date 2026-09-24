/**
 * AnimatedInput component with focus effects
 * Provides input with animated label and error state
 */

"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { useState, type InputHTMLAttributes, forwardRef } from "react";

interface AnimatedInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "onAnimationStart" | "onDragStart" | "onDragEnd" | "onDrag"> {
  label?: string;
  error?: string;
}

/**
 * AnimatedInput component
 *
 * @param label - Optional floating label
 * @param error - Error message to display
 *
 * @example
 * ```tsx
 * <AnimatedInput
 *   label="Email"
 *   type="email"
 *   value={email}
 *   onChange={(e) => setEmail(e.target.value)}
 *   error={emailError}
 * />
 * ```
 */
export function AnimatedInput({
  label,
  error,
  className,
  ...props
}: AnimatedInputProps) {
  const [isFocused, setIsFocused] = useState(false);
  const hasValue = props.value !== undefined && props.value !== "";

  return (
    <div className="relative w-full">
      {/* Input */}
      <motion.input
        className={cn(
          "w-full rounded-lg border px-4 py-3 text-base transition-all duration-200",
          "bg-white dark:bg-gray-800",
          "focus:outline-none focus:ring-2",
          error
            ? "border-red-500 focus:ring-red-500"
            : "border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500",
          label && "pt-6",
          className
        )}
        onFocus={(e) => {
          setIsFocused(true);
          props.onFocus?.(e);
        }}
        onBlur={(e) => {
          setIsFocused(false);
          props.onBlur?.(e);
        }}
        animate={{
          scale: isFocused ? 1.01 : 1,
        }}
        transition={{ duration: 0.2 }}
        {...props}
      />

      {/* Floating label */}
      {label && (
        <motion.label
          className={cn(
            "absolute left-4 pointer-events-none transition-all duration-200",
            error ? "text-red-500" : "text-gray-500 dark:text-gray-400"
          )}
          animate={{
            top: isFocused || hasValue ? "0.5rem" : "50%",
            translateY: isFocused || hasValue ? "0" : "-50%",
            fontSize: isFocused || hasValue ? "0.75rem" : "1rem",
          }}
          transition={{ duration: 0.2 }}
        >
          {label}
        </motion.label>
      )}

      {/* Error message */}
      {error && (
        <motion.p
          className="mt-1 text-sm text-red-500"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          {error}
        </motion.p>
      )}
    </div>
  );
}
