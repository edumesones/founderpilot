/**
 * AnimatedTable component with row animations
 * Provides table with staggered row entrance and hover effects
 */

"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { staggerItem } from "@/lib/animation-config";

interface AnimatedTableProps {
  headers: string[];
  rows: any[][];
  onRowClick?: (index: number) => void;
  maxStagger?: number;
  className?: string;
}

/**
 * AnimatedTable component
 *
 * @param headers - Table column headers
 * @param rows - Table row data (2D array)
 * @param onRowClick - Callback when row is clicked
 * @param maxStagger - Maximum number of rows to animate (default: 20)
 *
 * @example
 * ```tsx
 * <AnimatedTable
 *   headers={["Name", "Email", "Status"]}
 *   rows={[
 *     ["John Doe", "john@example.com", "Active"],
 *     ["Jane Smith", "jane@example.com", "Inactive"]
 *   ]}
 *   onRowClick={(index) => console.log('Row clicked:', index)}
 * />
 * ```
 */
export function AnimatedTable({
  headers,
  rows,
  onRowClick,
  maxStagger = 20,
  className,
}: AnimatedTableProps) {
  return (
    <div className={cn("w-full overflow-x-auto", className)}>
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-700">
            {headers.map((header, index) => (
              <th
                key={index}
                className="px-4 py-3 text-left text-sm font-semibold text-gray-900 dark:text-white"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <motion.tr
              key={rowIndex}
              className={cn(
                "border-b border-gray-100 dark:border-gray-800 transition-colors",
                onRowClick && "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-900/50"
              )}
              variants={rowIndex < maxStagger ? staggerItem : undefined}
              initial={rowIndex < maxStagger ? "hidden" : undefined}
              animate={rowIndex < maxStagger ? "visible" : undefined}
              whileHover={
                onRowClick
                  ? {
                      backgroundColor: "rgba(0, 0, 0, 0.02)",
                      transition: { duration: 0.2 },
                    }
                  : undefined
              }
              onClick={() => onRowClick?.(rowIndex)}
            >
              {row.map((cell, cellIndex) => (
                <td
                  key={cellIndex}
                  className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300"
                >
                  {cell}
                </td>
              ))}
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
