import {
  LayoutDashboard,
  Radar,
  LineChart,
  PlayCircle,
  Bot,
  Boxes,
  Microscope,
  ShieldAlert,
  FileText,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  badge?: string;
}

export const navItems: NavItem[] = [
  { label: "Overview", href: "/dashboard", icon: LayoutDashboard },
  { label: "Signals", href: "/signals", icon: Radar, badge: "8" },
  { label: "Backtests", href: "/backtests", icon: LineChart },
  { label: "Signal Replay", href: "/replay", icon: PlayCircle },
  { label: "Research AI", href: "/research", icon: Bot },
  { label: "Models", href: "/models", icon: Boxes },
  { label: "Validation", href: "/validation", icon: Microscope },
  { label: "Risk", href: "/risk", icon: ShieldAlert, badge: "3" },
  { label: "Docs", href: "/docs", icon: FileText },
];
