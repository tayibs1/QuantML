import * as React from "react";
import { cn } from "@/lib/utils";

interface GlassPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Stronger, more opaque surface for primary panels. */
  strong?: boolean;
  /** Adds an animated gradient border on hover. */
  glow?: boolean;
  /** Inner padding preset. */
  inset?: boolean;
}

export function GlassPanel({
  className,
  strong,
  glow,
  inset,
  children,
  ...props
}: GlassPanelProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl",
        strong ? "glass-strong" : "glass",
        glow && "animated-border",
        inset && "p-5 sm:p-6",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
