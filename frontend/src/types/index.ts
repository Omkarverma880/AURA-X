/**
 * Types mirroring the backend Pydantic schemas (app/schemas/*.py).
 * Money fields are numbers on the wire (see backend Money serializer).
 */

// ── Auth ──────────────────────────────────────────────────────────────

export interface Profile {
  display_name: string | null;
  avatar_url: string | null;
  phone: string | null;
  date_of_birth: string | null;
  currency: string;
  timezone: string;
  locale: string;
  theme: "light" | "dark" | "system";
  privacy_mode_default: boolean;
  dashboard_layout: Record<string, unknown> | null;
  bio: string | null;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_verified: boolean;
  created_at: string;
  last_login_at: string | null;
  profile: Profile | null;
  has_password: boolean;
  google_linked: boolean;
  phone: string | null;
  phone_verified: boolean;
  username: string | null;
}

export interface FinancialStatus {
  pin_configured: boolean;
  unlocked: boolean;
  seconds_remaining: number;
  unlock_minutes: number;
  attempts_remaining: number;
  locked_out: boolean;
  locked_until: string | null;
  mask_ledger_amounts: boolean;
}

export interface AuthResponse {
  user: User;
  csrf_token: string;
  financial: FinancialStatus;
}

export interface SessionInfo {
  id: string;
  user_agent: string | null;
  ip_address: string | null;
  created_at: string;
  last_used_at: string | null;
  expires_at: string;
  is_current: boolean;
}

// ── Common ────────────────────────────────────────────────────────────

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface MessageResponse {
  message: string;
  ok: boolean;
}

// ── Bahi Khata ────────────────────────────────────────────────────────

export type LedgerDirection = "given" | "borrowed";
export type LedgerTxnType = "principal" | "repayment" | "interest" | "write_off";
export type LedgerStatus = "active" | "partial" | "settled" | "overdue";
export type PaymentMethod = "cash" | "upi" | "bank_transfer" | "card" | "cheque" | "other";

export interface Person {
  id: string;
  name: string;
  phone: string | null;
  email: string | null;
  relation: string | null;
  notes: string | null;
  color: string | null;
  is_archived: boolean;
  created_at: string;
  total_given: number;
  total_received: number;
  total_borrowed: number;
  total_repaid: number;
  outstanding_receivable: number;
  outstanding_payable: number;
  net_balance: number;
  entry_count: number;
  active_count: number;
  last_activity: string | null;
}

export interface LedgerTransaction {
  id: string;
  entry_id: string;
  person_id: string;
  txn_type: LedgerTxnType;
  amount: number;
  signed_amount: number;
  txn_date: string;
  method: PaymentMethod | null;
  description: string | null;
  is_voided: boolean;
  void_reason: string | null;
  created_at: string;
  balance_after: number | null;
  person_name: string | null;
  purpose: string | null;
}

export interface LedgerEntry {
  id: string;
  person_id: string;
  person_name: string | null;
  direction: LedgerDirection;
  purpose: string;
  entry_date: string;
  due_date: string | null;
  reminder_on: string | null;
  notes: string | null;
  currency: string;
  is_closed: boolean;
  created_at: string;
  principal_amount: number;
  settled_amount: number;
  outstanding: number;
  progress_percent: number;
  status: LedgerStatus;
  is_overdue: boolean;
  days_overdue: number;
  transaction_count: number;
}

export interface LedgerEntryDetail extends LedgerEntry {
  transactions: LedgerTransaction[];
}

export interface PersonDetail extends Person {
  entries: LedgerEntry[];
  ledger: LedgerTransaction[];
}

export interface LedgerSummary {
  total_given: number;
  total_received: number;
  outstanding_receivable: number;
  total_borrowed: number;
  total_repaid: number;
  outstanding_payable: number;
  net_position: number;
  settlement_rate: number;
  people_count: number;
  active_entries: number;
  settled_entries: number;
  overdue_entries: number;
  overdue_amount: number;
  largest_outstanding: Record<string, unknown> | null;
  oldest_outstanding: Record<string, unknown> | null;
}

export interface LedgerAnalytics {
  summary: LedgerSummary;
  monthly_trend: Array<{ month: string; given: number; received: number; borrowed: number; repaid: number }>;
  outstanding_by_person: Array<{ person_id: string; name: string; receivable: number; payable: number; total: number }>;
  status_breakdown: Array<{ status: string; count: number }>;
  direction_split: Array<{ direction: string; amount: number }>;
}

// ── Expenses / income / budgets ──────────────────────────────────────

export interface Category {
  id: string;
  name: string;
  kind: "expense" | "income";
  parent_id: string | null;
  icon: string | null;
  color: string | null;
  is_default: boolean;
  is_archived: boolean;
  sort_order: number;
  children: Category[];
  spent: number | null;
  transaction_count: number | null;
}

export interface Expense {
  id: string;
  spent_on: string;
  amount: number;
  category_id: string | null;
  category_name: string | null;
  category_icon: string | null;
  category_color: string | null;
  subcategory_id: string | null;
  subcategory_name: string | null;
  merchant: string | null;
  payment_method: PaymentMethod | null;
  description: string | null;
  notes: string | null;
  is_recurring: boolean;
  recurrence: string;
  tags: string[] | null;
  created_at: string;
}

export interface IncomeSource {
  id: string;
  name: string;
  income_type: string;
  employer: string | null;
  is_active: boolean;
  notes: string | null;
  total_received: number;
}

export interface IncomeRecord {
  id: string;
  source_id: string | null;
  source_name: string | null;
  income_type: string | null;
  received_on: string;
  period_month: string;
  gross_amount: number;
  net_amount: number;
  deductions: number;
  description: string | null;
  notes: string | null;
  created_at: string;
}

export interface Budget {
  id: string | null;
  category_id: string;
  category_name: string | null;
  category_icon: string | null;
  category_color: string | null;
  period_month: string;
  amount: number;
  spent: number;
  remaining: number;
  utilisation: number;
  status: "on_track" | "warning" | "exceeded";
  notes: string | null;
}

export interface CategorySpend {
  category_id: string | null;
  name: string;
  icon: string | null;
  color: string | null;
  amount: number;
  share: number;
  count: number;
}

export interface MonthlySummary {
  period_month: string;
  income: number;
  gross_income: number;
  expenses: number;
  savings: number;
  savings_rate: number;
  investments: number;
  money_given: number;
  money_received: number;
  expense_count: number;
  daily_average: number;
  budget_total: number;
  budget_used: number;
  by_category: CategorySpend[];
  top_expenses: Expense[];
  recurring: Expense[];
  previous_expenses: number;
  change_percent: number;
}

export interface TrendPoint {
  month: string;
  income: number;
  expenses: number;
  savings: number;
  savings_rate: number;
}

// ── Investments ──────────────────────────────────────────────────────

export type AssetType =
  | "stock" | "mutual_fund" | "etf" | "fixed_deposit" | "gold" | "nps"
  | "ppf" | "epf" | "bond" | "real_estate" | "crypto" | "cash" | "other";

export type InvestmentTxnType = "buy" | "sell" | "dividend" | "interest" | "fee" | "bonus";

export interface InvestmentAccount {
  id: string;
  name: string;
  broker: string | null;
  account_number: string | null;
  notes: string | null;
  is_active: boolean;
  holding_count: number;
  current_value: number;
}

export interface Holding {
  id: string;
  name: string;
  symbol: string | null;
  asset_type: AssetType;
  account_id: string | null;
  account_name: string | null;
  currency: string;
  current_price: number | null;
  price_updated_at: string | null;
  manual_value: number | null;
  maturity_date: string | null;
  interest_rate: number | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  units_held: number;
  avg_price: number;
  invested_amount: number;
  current_value: number;
  unrealised_pnl: number;
  realised_pnl: number;
  total_dividends: number;
  return_percent: number;
  xirr_percent: number | null;
}

export interface InvestmentTxn {
  id: string;
  holding_id: string;
  txn_type: InvestmentTxnType;
  txn_date: string;
  units: number;
  price_per_unit: number;
  amount: number;
  fees: number;
  notes: string | null;
  created_at: string;
}

export interface HoldingDetail extends Holding {
  transactions: InvestmentTxn[];
}

export interface PortfolioSummary {
  total_invested: number;
  current_value: number;
  unrealised_pnl: number;
  realised_pnl: number;
  total_dividends: number;
  total_return: number;
  return_percent: number;
  xirr_percent: number | null;
  holding_count: number;
  by_asset_type: Array<{ asset_type: string; invested: number; current_value: number; share: number }>;
  top_gainers: Holding[];
  top_losers: Holding[];
  monthly_investment: Array<{ month: string; amount: number }>;
  value_history: Array<Record<string, unknown>>;
}

export interface InvestmentGoal {
  id: string;
  name: string;
  category: string | null;
  description: string | null;
  target_amount: number;
  target_date: string | null;
  current_age: number | null;
  target_age: number | null;
  current_corpus: number | null;
  use_portfolio_value: boolean;
  expected_return: number;
  monthly_investment: number;
  step_up_percent: number;
  inflation_rate: number;
  priority: "low" | "medium" | "high";
  status: string;
  created_at: string;
  years_remaining: number;
  effective_corpus: number;
  projected_value: number;
  required_monthly_sip: number;
  shortfall: number;
  surplus: number;
  on_track: boolean;
  projection_chart: Array<{ year: number; corpus: number }>;
}

// ── Life goals / checklists ──────────────────────────────────────────

export type GoalStatus = "not_started" | "in_progress" | "completed" | "on_hold" | "abandoned";
export type TrackerType =
  | "generic" | "temple" | "trek" | "trip" | "country" | "book" | "course" | "fitness" | "achievement";

export interface LifeCategory {
  id: string;
  name: string;
  icon: string | null;
  color: string | null;
  sort_order: number;
}

export interface Milestone {
  id: string;
  goal_id: string;
  title: string;
  description: string | null;
  due_date: string | null;
  is_completed: boolean;
  completed_on: string | null;
  position: number;
}

export interface LifeGoal {
  id: string;
  title: string;
  category_id: string | null;
  category_name: string | null;
  description: string | null;
  target_date: string | null;
  started_on: string | null;
  completed_on: string | null;
  target_amount: number | null;
  current_amount: number | null;
  status: GoalStatus;
  priority: "low" | "medium" | "high";
  notes: string | null;
  created_at: string;
  progress_percent: number;
  milestone_total: number;
  milestone_done: number;
  is_overdue: boolean;
}

export interface LifeGoalDetail extends LifeGoal {
  milestones: Milestone[];
}

export interface ChecklistItem {
  id: string;
  checklist_id: string;
  name: string;
  description: string | null;
  location: string | null;
  position: number;
  is_completed: boolean;
  completed_on: string | null;
  rating: number | null;
  notes: string | null;
  details: Record<string, unknown> | null;
  album_id: string | null;
}

export interface Checklist {
  id: string;
  title: string;
  description: string | null;
  tracker_type: TrackerType;
  icon: string | null;
  color: string | null;
  target_count: number | null;
  is_archived: boolean;
  goal_id: string | null;
  created_at: string;
  item_count: number;
  completed_count: number;
  progress_percent: number;
}

export interface ChecklistDetail extends Checklist {
  items: ChecklistItem[];
}

// ── Memories ─────────────────────────────────────────────────────────

export type AlbumType = "trip" | "trek" | "family" | "event" | "general";

export interface Photo {
  id: string;
  album_id: string;
  url: string | null;
  thumbnail_url: string | null;
  original_filename: string | null;
  mime_type: string;
  width: number | null;
  height: number | null;
  caption: string | null;
  taken_at: string | null;
  position: number;
  created_at: string;
}

export interface Album {
  id: string;
  title: string;
  description: string | null;
  album_type: AlbumType;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  cover_photo_id: string | null;
  cover_photo_url: string | null;
  tags: string[] | null;
  is_favourite: boolean;
  notes: string | null;
  created_at: string;
  photo_count: number;
}

export interface AlbumDetail extends Album {
  photos: Photo[];
}

// ── Dashboard / analytics ────────────────────────────────────────────

export interface GreetingBlock {
  name: string;
  greeting: string;
  date: string;
  privacy_mode: boolean;
}

export interface FinancialSnapshot {
  money_given: number;
  to_receive: number;
  money_borrowed: number;
  to_pay: number;
  net_position: number;
  monthly_income: number | null;
  monthly_expenses: number | null;
  net_savings: number | null;
  savings_rate: number | null;
  financial_locked: boolean;
}

export interface ModuleCard {
  module: string;
  headline: string;
  subtext: string;
  trend: "up" | "down" | "flat" | null;
  locked: boolean;
}

export interface Reminder {
  type: string;
  title: string;
  detail: string | null;
  due_date: string;
  entity_id: string;
}

export interface ActivityItem {
  action: string;
  summary: string | null;
  entity_type: string | null;
  created_at: string;
}

export interface DashboardData {
  greeting: GreetingBlock;
  snapshot: FinancialSnapshot;
  cards: ModuleCard[];
  upcoming_reminders: Reminder[];
  recent_activity: ActivityItem[];
  unread_notifications: number;
}

export interface LifeAnalytics {
  goals_completed: number;
  goals_in_progress: number;
  goals_overdue: number;
  trackers: Array<{ id: string; title: string; tracker_type: string; completed: number; total: number; progress_percent: number }>;
  trips_completed: number;
  memory_count: number;
}

export interface AnalyticsOverview {
  financial: MonthlySummary | null;
  bahi_khata: LedgerSummary;
  investments: PortfolioSummary | null;
  life: LifeAnalytics;
  financial_locked: boolean;
}

// ── Notifications ────────────────────────────────────────────────────

export interface Notification {
  id: string;
  notification_type: string;
  severity: "info" | "success" | "warning" | "danger";
  title: string;
  body: string | null;
  entity_type: string | null;
  entity_id: string | null;
  action_url: string | null;
  due_at: string | null;
  is_read: boolean;
  is_dismissed: boolean;
  created_at: string;
}

// ── Search ───────────────────────────────────────────────────────────

export interface SearchResult {
  type: string;
  id: string;
  title: string;
  subtitle: string | null;
}
