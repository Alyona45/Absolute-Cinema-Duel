import { cn } from "@/lib/utils";
import { forwardRef, type ReactNode } from "react";
import { motion, HTMLMotionProps } from "framer-motion";
import { interactiveLiftVariants } from "@/lib/animations";

export interface ButtonProps extends Omit<HTMLMotionProps<"button">, "variant"> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  children?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      loading = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const base =
      "relative overflow-hidden rounded-full font-semibold tracking-[0.01em] transition-all duration-300 ease-out flex items-center justify-center gap-2.5 select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/25";

    const variants = {
      primary:
        "bg-red-600 text-white shadow-[0_10px_35px_rgba(220,38,38,0.28)] hover:bg-red-700 hover:shadow-[0_12px_42px_rgba(220,38,38,0.34)]",
      secondary:
        "bg-white text-neutral-900 shadow-[0_10px_30px_rgba(0,0,0,0.18)] hover:bg-neutral-100",
      ghost:
        "bg-transparent text-white border border-neutral-600 hover:bg-white/7",
      danger:
        "bg-red-900 text-white hover:bg-red-800",
    };

    const sizes = {
      sm: "h-10 px-4.5 text-sm",
      md: "h-12.5 px-6 text-base",
      lg: "h-14 px-8 text-base",
    };

    return (
      <motion.button
        ref={ref}
        initial="rest"
        animate="rest"
        whileHover="hover"
        whileTap="tap"
        variants={interactiveLiftVariants}
        className={cn(
          base,
          variants[variant],
          sizes[size],
          (disabled || loading) && "opacity-50 pointer-events-none",
          className
        )}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <svg
            className="animate-spin h-5 w-5 shrink-0"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        )}
        {children}
      </motion.button>
    );
  }
);

Button.displayName = "Button";
