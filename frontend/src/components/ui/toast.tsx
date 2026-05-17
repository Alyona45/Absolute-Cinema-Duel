"use client";

import { useToastStore } from "@/stores/toast-store";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { toastVariants } from "@/lib/animations";

const typeStyles = {
  success: "bg-green-600/90",
  error: "bg-red-600/90",
  info: "bg-neutral-700/90",
};

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  return (
    <div className="fixed top-4 right-4 left-4 md:left-auto md:w-96 z-[100] flex flex-col gap-2">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            variants={toastVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className={cn(
              "rounded-2xl px-4 py-3 text-white text-sm backdrop-blur-sm flex items-center justify-between gap-3 shadow-[0_12px_40px_rgba(0,0,0,0.25)] border border-white/10",
              typeStyles[toast.type]
            )}
          >
            <span>{toast.message}</span>
            <button
              onClick={() => removeToast(toast.id)}
              className="shrink-0 hover:opacity-70"
            >
              <X size={16} />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
