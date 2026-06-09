import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-mono font-medium tracking-wide transition-colors",
  {
    variants: {
      variant: {
        default: "border-white/10 bg-white/[0.04] text-slate-300",
        brand: "border-brand-400/30 bg-brand-500/10 text-brand-200",
        violet: "border-violet/30 bg-violet/10 text-violet-200",
        bull: "border-bull/30 bg-bull/10 text-bull-soft",
        bear: "border-bear/30 bg-bear/10 text-bear-soft",
        hold: "border-hold/30 bg-hold/10 text-hold-soft",
        outline: "border-white/15 text-slate-400",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
