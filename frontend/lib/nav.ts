import {
  LayoutDashboard,
  Radar,
  LineChart,
  PlayCircle,
  Workflow,
  Bot,
  Boxes,
  Microscope,
  ShieldAlert,
  FileText,
  type LucideIcon,
} from "lucide-react";
import signalsSnapshot from "@/lib/snapshot/signals.json";
import riskSnapshot from "@/lib/snapshot/risk.json";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  badge?: string;
}

// Badge counts come from the pipeline snapshot.
const signalCount = (signalsSnapshot as unknown[]).length;
const riskFlagCount = ((riskSnapshot as { flags?: unknown[] }).flags ?? []).length;

export const navItems: NavItem[] = [
  { label: "Overview", href: "/dashboard", icon: LayoutDashboard },
  {
    label: "Signals",
    href: "/signals",
    icon: Radar,
    badge: signalCount ? String(signalCount) : undefined,
  },
  { label: "Backtests", href: "/backtests", icon: LineChart },
  { label: "Signal Replay", href: "/replay", icon: PlayCircle },
  { label: "Pipeline", href: "/pipeline", icon: Workflow },
  { label: "Research AI", href: "/research", icon: Bot },
  { label: "Models", href: "/models", icon: Boxes },
  { label: "Validation", href: "/validation", icon: Microscope },
  {
    label: "Risk",
    href: "/risk",
    icon: ShieldAlert,
    badge: riskFlagCount ? String(riskFlagCount) : undefined,
  },
  { label: "Docs", href: "/docs", icon: FileText },
];
