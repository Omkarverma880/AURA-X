import {
  LayoutDashboard,
  BookOpenText,
  Receipt,
  TrendingUp,
  Target,
  Images,
  BarChart3,
  Settings,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Shown in the compact bottom nav; a subset of the full sidebar list. */
  mobile?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, mobile: true },
  { to: "/bahi-khata", label: "Bahi Khata", icon: BookOpenText, mobile: true },
  { to: "/expenses", label: "Expenses", icon: Receipt, mobile: true },
  { to: "/investments", label: "Investments", icon: TrendingUp, mobile: true },
  { to: "/goals", label: "Goals", icon: Target },
  { to: "/memories", label: "Memories", icon: Images },
  { to: "/analytics", label: "Analytics", icon: BarChart3, mobile: true },
  { to: "/settings", label: "Settings", icon: Settings },
];
