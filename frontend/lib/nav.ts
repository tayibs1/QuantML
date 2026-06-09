import {
  LayoutDashboard,
  Radar,
  LineChart,
  Bot,
  Boxes,
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
  { label: "Research AI", href: "/research", icon: Bot },
  { label: "Models", href: "/models", icon: Boxes },
  { label: "Risk", href: "/risk", icon: ShieldAlert, badge: "3" },
  { label: "Docs", href: "/docs", icon: FileText },
];
