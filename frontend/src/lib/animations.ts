export const springTransition = {
  type: "spring",
  stiffness: 260,
  damping: 24,
  mass: 0.9,
};

export const springSmooth = {
  type: "spring",
  stiffness: 190,
  damping: 22,
  mass: 0.95,
};

export const easeOutQuart = [0.16, 1, 0.3, 1] as const;

export const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.06,
    },
  },
};

export const staggerItem = {
  hidden: { opacity: 0, y: 18, scale: 0.98, filter: "blur(6px)" },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    filter: "blur(0px)",
    transition: springSmooth,
  },
};

export const fadeUp = {
  hidden: { opacity: 0, y: 28, scale: 0.985, filter: "blur(8px)" },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    filter: "blur(0px)",
    transition: springSmooth,
  },
};

export const scaleUp = {
  hidden: { opacity: 0, scale: 0.92, filter: "blur(6px)" },
  visible: {
    opacity: 1,
    scale: 1,
    filter: "blur(0px)",
    transition: springSmooth,
  },
};

export const pageTransitionVariants = {
  initial: { opacity: 0, y: 18, scale: 0.985, filter: "blur(10px)" },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    filter: "blur(0px)",
    transition: {
      ...springSmooth,
      delayChildren: 0.05,
      staggerChildren: 0.08,
    },
  },
  exit: {
    opacity: 0,
    y: -12,
    scale: 0.99,
    filter: "blur(8px)",
    transition: { duration: 0.22, ease: easeOutQuart },
  },
};

export const pageChromeVariants = {
  initial: { opacity: 0, y: 10 },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.6,
      ease: easeOutQuart,
    },
  },
};

export const modalBackdropVariants = {
  hidden: { opacity: 0, backdropFilter: "blur(0px)" },
  visible: {
    opacity: 1,
    backdropFilter: "blur(16px)" as const,
    transition: { duration: 0.22, ease: easeOutQuart },
  },
  exit: {
    opacity: 0,
    backdropFilter: "blur(0px)" as const,
    transition: { duration: 0.18, ease: easeOutQuart },
  },
};

export const modalPanelVariants = {
  hidden: { opacity: 0, y: 24, scale: 0.96, filter: "blur(8px)" },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    filter: "blur(0px)",
    transition: springSmooth,
  },
  exit: {
    opacity: 0,
    y: 16,
    scale: 0.98,
    filter: "blur(8px)",
    transition: { duration: 0.18, ease: easeOutQuart },
  },
};

export const toastVariants = {
  hidden: { opacity: 0, x: 24, y: -12, scale: 0.96, filter: "blur(8px)" },
  visible: {
    opacity: 1,
    x: 0,
    y: 0,
    scale: 1,
    filter: "blur(0px)",
    transition: springSmooth,
  },
  exit: {
    opacity: 0,
    x: 20,
    y: -12,
    scale: 0.96,
    filter: "blur(8px)",
    transition: { duration: 0.16, ease: easeOutQuart },
  },
};

export const interactiveLiftVariants = {
  rest: { y: 0, scale: 1 },
  hover: {
    y: -2,
    scale: 1.01,
    transition: springTransition,
  },
  tap: {
    y: 0,
    scale: 0.985,
    transition: { duration: 0.12, ease: easeOutQuart },
  },
};

export const ambientBlobVariants = {
  animate: {
    scale: [1, 1.04, 1],
    opacity: [0.45, 0.7, 0.45],
    transition: {
      duration: 10,
      repeat: Infinity,
      ease: "easeInOut",
    },
  },
};
