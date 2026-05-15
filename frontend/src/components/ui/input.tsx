import { cn } from "@/lib/utils";
import { type InputHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, icon, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-2.5 w-full">
        {label && (
          <label className="text-white text-lg font-bold leading-tight">{label}</label>
        )}
        <div className="relative flex justify-center w-full">
          <input
            ref={ref}
            style={{ paddingInline: 15, paddingBlock: 15 }}
            className={cn(
              "w-full max-w-[400px] h-[54px] rounded-[18px] text-white text-lg placeholder:text-white/35 outline-none transition-all duration-300 border border-white/8 bg-white/6 backdrop-blur-sm shadow-[0_10px_40px_rgba(0,0,0,0.18)]",
              "focus:border-white/24 focus:bg-white/8 focus:shadow-[0_14px_50px_rgba(0,0,0,0.28)]",
              error && "border-red-600 border-2",
              icon && "!pr-12",
              className
            )}
            {...props}
          />
          {icon && (
            <div className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-500">
              {icon}
            </div>
          )}
        </div>
        {error && <p className="text-red-500 text-sm leading-5">{error}</p>}
      </div>
    );
  }
);

Input.displayName = "Input";
