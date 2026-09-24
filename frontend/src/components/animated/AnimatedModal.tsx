/**
 * AnimatedModal component with backdrop blur
 * Provides modal with slide-in animation and focus trap
 */

"use client";

import { motion, AnimatePresence } from "framer-motion";
import * as Dialog from "@radix-ui/react-dialog";
import { cn } from "@/lib/utils";
import { modalBackdrop, modalContent } from "@/lib/animation-config";
import { type ReactNode } from "react";

interface AnimatedModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  className?: string;
}

/**
 * AnimatedModal component
 *
 * @param open - Control modal visibility
 * @param onClose - Callback when modal closes
 * @param title - Optional modal title
 * @param children - Modal content
 *
 * @example
 * ```tsx
 * const [open, setOpen] = useState(false);
 *
 * <AnimatedModal open={open} onClose={() => setOpen(false)} title="Modal Title">
 *   <p>Modal content goes here</p>
 * </AnimatedModal>
 * ```
 */
export function AnimatedModal({
  open,
  onClose,
  title,
  children,
  className,
}: AnimatedModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            {/* Backdrop */}
            <Dialog.Overlay asChild>
              <motion.div
                className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
                variants={modalBackdrop}
                initial="hidden"
                animate="visible"
                exit="hidden"
              />
            </Dialog.Overlay>

            {/* Modal Content */}
            <Dialog.Content asChild>
              <motion.div
                className={cn(
                  "fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2",
                  "rounded-xl bg-white dark:bg-gray-900 p-6 shadow-2xl",
                  "max-h-[85vh] overflow-y-auto",
                  className
                )}
                variants={modalContent}
                initial="hidden"
                animate="visible"
                exit="exit"
              >
                {/* Header */}
                {title && (
                  <Dialog.Title className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                    {title}
                  </Dialog.Title>
                )}

                {/* Close button */}
                <Dialog.Close
                  className="absolute right-4 top-4 rounded-full p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                  aria-label="Close"
                >
                  <svg
                    className="h-5 w-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </Dialog.Close>

                {/* Content */}
                <div className="mt-2">{children}</div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
