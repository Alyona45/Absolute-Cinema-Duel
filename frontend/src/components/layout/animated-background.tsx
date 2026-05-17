"use client";

import { motion, useReducedMotion } from "framer-motion";
import { ambientBlobVariants } from "@/lib/animations";

const layerBase: React.CSSProperties = {
  transform: "translateZ(0)",
  willChange: "transform, opacity",
};

export function AnimatedBackground() {
  const reduced = useReducedMotion();
  const animateProp = reduced ? undefined : "animate";

  return (
    <div aria-hidden className="animated-bg-layer pointer-events-none fixed inset-0 overflow-hidden">
      <motion.div
        className="absolute -left-24 top-[-4rem] h-72 w-72 rounded-full bg-red-500/18 blur-3xl"
        style={layerBase}
        variants={ambientBlobVariants}
        animate={animateProp}
      />
      <motion.div
        className="absolute right-[-5rem] top-[18vh] h-64 w-64 rounded-full bg-white/8 blur-3xl"
        style={layerBase}
        variants={ambientBlobVariants}
        animate={animateProp}
      />
      <motion.div
        className="absolute bottom-[-7rem] left-1/2 h-80 w-80 -translate-x-1/2 rounded-full bg-red-600/12 blur-3xl"
        style={layerBase}
        variants={ambientBlobVariants}
        animate={animateProp}
      />
    </div>
  );
}
