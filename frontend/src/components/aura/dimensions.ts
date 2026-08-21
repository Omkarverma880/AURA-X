import {
  BookOpenText,
  Receipt,
  TrendingUp,
  Target,
  Mountain,
  Images,
  type LucideIcon,
} from "lucide-react";

/**
 * The six dimensions of Aura X, shared by the landing constellation and the
 * signed-in Home so both describe the universe identically.
 *
 * `route` points at a page that actually exists. Journeys has no page of its
 * own - trips and treks live inside Memories ("Trips, treks and moments worth
 * keeping"), so it routes there rather than to a link that would 404.
 */
export interface Dimension {
  id: string;
  index: string;
  label: string;
  tagline: string;
  description: string;
  icon: LucideIcon;
  route: string;
  /** Maps to the `module` key returned by GET /dashboard, where one exists. */
  moduleKey?: string;
}

export const DIMENSIONS: Dimension[] = [
  {
    id: "bahi-khata",
    index: "01",
    label: "Bahi Khata",
    tagline: "Give. Take. Balance.",
    description: "Who owes what, and what came back.",
    icon: BookOpenText,
    route: "/bahi-khata",
    moduleKey: "bahi_khata",
  },
  {
    id: "spend",
    index: "02",
    label: "Spend",
    tagline: "Every rupee has a story.",
    description: "Income and expenses, month on month.",
    icon: Receipt,
    route: "/expenses",
    moduleKey: "expenses",
  },
  {
    id: "wealth",
    index: "03",
    label: "Wealth",
    tagline: "Build today. Grow tomorrow.",
    description: "Investments, assets and returns.",
    icon: TrendingUp,
    route: "/investments",
    moduleKey: "investments",
  },
  {
    id: "goals",
    index: "04",
    label: "Goals",
    tagline: "Plan. Achieve. Repeat.",
    description: "Ambitions with a number and a date.",
    icon: Target,
    route: "/goals",
    moduleKey: "goals",
  },
  {
    id: "journeys",
    index: "05",
    label: "Journeys",
    tagline: "Explore more. Live more.",
    description: "Places, treks and experiences.",
    icon: Mountain,
    route: "/memories",
  },
  {
    id: "memories",
    index: "06",
    label: "Memories",
    tagline: "Capture. Cherish. Relive.",
    description: "The moments worth keeping.",
    icon: Images,
    route: "/memories",
    moduleKey: "life",
  },
];
