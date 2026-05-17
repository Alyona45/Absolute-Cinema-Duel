import { cn, getInitials } from "@/lib/utils";

interface AvatarProps {
  src?: string | null;
  name: string;
  size?: "sm" | "md" | "lg" | "xl";
  borderColor?: "red" | "gray" | "none";
  className?: string;
}

const sizeMap = {
  sm: 36,
  md: 56,
  lg: 96,
  xl: 128,
};

const borderMap = {
  red: "#E82323",
  gray: "#737373",
  none: "transparent",
};

export function Avatar({
  src,
  name,
  size = "md",
  borderColor = "red",
  className,
}: AvatarProps) {
  const outer = sizeMap[size];
  const innerPad = size === "sm" ? 3 : 4;
  const inner = outer - innerPad * 2;

  return (
    <div
      className={cn("relative shrink-0", className)}
      style={{ width: outer, height: outer }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: outer,
          height: outer,
          borderRadius: 9999,
          border: `2px solid ${borderMap[borderColor]}`,
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: innerPad,
          left: innerPad,
          width: inner,
          height: inner,
          borderRadius: 9999,
          overflow: "hidden",
          background: "#525252",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {src ? (
          <img
            src={src}
            alt={name}
            width={inner}
            height={inner}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              display: "block",
            }}
            loading="lazy"
            decoding="async"
          />
        ) : (
          <span
            className="text-white font-bold select-none"
            style={{ fontSize: Math.max(12, Math.floor(inner * 0.36)) }}
          >
            {getInitials(name)}
          </span>
        )}
      </div>
    </div>
  );
}
