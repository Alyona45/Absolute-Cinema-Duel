"use client";

import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <motion.div
      className="flex flex-col items-center justify-center min-h-[calc(100dvh-5rem)] px-6 gap-6 text-center"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="relative h-16 w-16">
        <div className="absolute inset-0 rounded-full bg-red-500/15 blur-xl" />
        <div className="absolute inset-0 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm" />
        <div className="absolute inset-3 rounded-full border-2 border-red-500/70 border-t-transparent animate-spin" />
      </div>
      <h2 className="text-xl font-bold text-white">ошибка сети</h2>
      <p className="text-white/55 text-sm max-w-xs">
        Скоро вернём вас обратно
      </p>
      <Button variant="primary" onClick={reset}>
        Попробовать снова
      </Button>
    </motion.div>
  );
}
