/**
 * Custom 404 page.
 */

"use client";

import Link from "next/link";
import { AnimatedCard, AnimatedButton } from "@/components/animated";
import { motion } from "framer-motion";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
      <AnimatedCard variant="glass" className="w-full max-w-md p-8 text-center" hover>
        <motion.h1
          className="text-6xl font-bold text-gray-300 dark:text-gray-700 mb-4"
          animate={{
            scale: [1, 1.05, 1],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          404
        </motion.h1>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
          Page not found
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <Link href="/">
          <AnimatedButton variant="primary">
            Go back home
          </AnimatedButton>
        </Link>
      </AnimatedCard>
    </div>
  );
}
