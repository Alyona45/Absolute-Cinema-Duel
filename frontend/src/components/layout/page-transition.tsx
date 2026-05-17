"use client";

import { AnimatePresence, MotionConfig, motion } from "framer-motion";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { pageTransitionVariants } from "@/lib/animations";

interface PageTransitionProps {
  children: ReactNode;
}

export function PageTransition({ children }: PageTransitionProps) {
  const pathname = usePathname();

  return (
    <MotionConfig reducedMotion="user">
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={pathname}
          variants={pageTransitionVariants}
          initial="initial"
          animate="animate"
          exit="exit"
          className="relative isolate"
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </MotionConfig>
  );
}
