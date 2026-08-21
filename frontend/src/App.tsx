import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { ProtectedRoute, GuestRoute } from "@/components/auth/ProtectedRoute";
import { AppShell } from "@/components/layout/AppShell";

import { LoginPage } from "@/pages/auth/Login";
import { RegisterPage } from "@/pages/auth/Register";
import { ForgotPasswordPage } from "@/pages/auth/ForgotPassword";
import { ResetPasswordPage } from "@/pages/auth/ResetPassword";
import { VerifyEmailPage } from "@/pages/auth/VerifyEmail";
import { NotFoundPage } from "@/pages/NotFound";
import { DashboardPage } from "@/pages/Dashboard";

// The landing page pulls in three.js/react-three-fiber for its 3D hero - kept
// out of every other bundle so a signed-in user opening /dashboard never pays
// for a scene they will never see (GuestRoute redirects them past it).
const LandingPage = lazy(() => import("@/pages/Landing").then((m) => ({ default: m.LandingPage })));

// Every other module is loaded on demand: a first-time visitor pays for the
// login screen and the dashboard, not for Investments' recharts bundle or
// the photo-upload code in Memories before they have ever opened those tabs.
const BahiKhataPage = lazy(() => import("@/pages/bahi-khata/BahiKhataPage").then((m) => ({ default: m.BahiKhataPage })));
const PersonDetailPage = lazy(() => import("@/pages/bahi-khata/PersonDetailPage").then((m) => ({ default: m.PersonDetailPage })));
const EntryDetailPage = lazy(() => import("@/pages/bahi-khata/EntryDetailPage").then((m) => ({ default: m.EntryDetailPage })));
const ExpensesPage = lazy(() => import("@/pages/expenses/ExpensesPage").then((m) => ({ default: m.ExpensesPage })));
const BudgetsPage = lazy(() => import("@/pages/expenses/BudgetsPage").then((m) => ({ default: m.BudgetsPage })));
const IncomePage = lazy(() => import("@/pages/expenses/IncomePage").then((m) => ({ default: m.IncomePage })));
const InvestmentsPage = lazy(() => import("@/pages/investments/InvestmentsPage").then((m) => ({ default: m.InvestmentsPage })));
const HoldingDetailPage = lazy(() => import("@/pages/investments/HoldingDetailPage").then((m) => ({ default: m.HoldingDetailPage })));
const InvestmentGoalsPage = lazy(() => import("@/pages/investments/InvestmentGoalsPage").then((m) => ({ default: m.InvestmentGoalsPage })));
const GoalsPage = lazy(() => import("@/pages/goals/GoalsPage").then((m) => ({ default: m.GoalsPage })));
const GoalDetailPage = lazy(() => import("@/pages/goals/GoalDetailPage").then((m) => ({ default: m.GoalDetailPage })));
const ChecklistsPage = lazy(() => import("@/pages/goals/ChecklistsPage").then((m) => ({ default: m.ChecklistsPage })));
const ChecklistDetailPage = lazy(() => import("@/pages/goals/ChecklistDetailPage").then((m) => ({ default: m.ChecklistDetailPage })));
const MemoriesPage = lazy(() => import("@/pages/memories/MemoriesPage").then((m) => ({ default: m.MemoriesPage })));
const AlbumDetailPage = lazy(() => import("@/pages/memories/AlbumDetailPage").then((m) => ({ default: m.AlbumDetailPage })));
const AnalyticsPage = lazy(() => import("@/pages/analytics/AnalyticsPage").then((m) => ({ default: m.AnalyticsPage })));
const SettingsLayout = lazy(() => import("@/pages/settings/SettingsLayout").then((m) => ({ default: m.SettingsLayout })));
const ProfileSettingsPage = lazy(() => import("@/pages/settings/ProfileSettingsPage").then((m) => ({ default: m.ProfileSettingsPage })));
const SecuritySettingsPage = lazy(() => import("@/pages/settings/SecuritySettingsPage").then((m) => ({ default: m.SecuritySettingsPage })));
const AppearanceSettingsPage = lazy(() => import("@/pages/settings/AppearanceSettingsPage").then((m) => ({ default: m.AppearanceSettingsPage })));
const CategoriesSettingsPage = lazy(() => import("@/pages/settings/CategoriesSettingsPage").then((m) => ({ default: m.CategoriesSettingsPage })));
const NotificationsSettingsPage = lazy(() => import("@/pages/settings/NotificationsSettingsPage").then((m) => ({ default: m.NotificationsSettingsPage })));
const DataSettingsPage = lazy(() => import("@/pages/settings/DataSettingsPage").then((m) => ({ default: m.DataSettingsPage })));

function RouteFallback() {
  return (
    <div className="flex justify-center py-24">
      <Loader2 className="h-6 w-6 animate-spin text-[var(--brand)]" />
    </div>
  );
}

export function App() {
  return (
    <Routes>
      <Route element={<GuestRoute />}>
        <Route
          path="/"
          element={
            <Suspense fallback={<div className="min-h-dvh bg-[#050507]" />}>
              <LandingPage />
            </Suspense>
          }
        />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      </Route>

      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<DashboardPage />} />

          <Route
            path="/*"
            element={
              <Suspense fallback={<RouteFallback />}>
                <Routes>
                  <Route path="bahi-khata" element={<BahiKhataPage />} />
                  <Route path="bahi-khata/people/:personId" element={<PersonDetailPage />} />
                  <Route path="bahi-khata/entries/:entryId" element={<EntryDetailPage />} />

                  <Route path="expenses" element={<ExpensesPage />} />
                  <Route path="expenses/budgets" element={<BudgetsPage />} />
                  <Route path="expenses/income" element={<IncomePage />} />

                  <Route path="investments" element={<InvestmentsPage />} />
                  <Route path="investments/goals" element={<InvestmentGoalsPage />} />
                  <Route path="investments/:holdingId" element={<HoldingDetailPage />} />

                  <Route path="goals" element={<GoalsPage />} />
                  <Route path="goals/checklists" element={<ChecklistsPage />} />
                  <Route path="goals/checklists/:checklistId" element={<ChecklistDetailPage />} />
                  <Route path="goals/:goalId" element={<GoalDetailPage />} />

                  <Route path="memories" element={<MemoriesPage />} />
                  <Route path="memories/:albumId" element={<AlbumDetailPage />} />

                  <Route path="analytics" element={<AnalyticsPage />} />

                  <Route path="settings" element={<SettingsLayout />}>
                    <Route index element={<Navigate to="profile" replace />} />
                    <Route path="profile" element={<ProfileSettingsPage />} />
                    <Route path="security" element={<SecuritySettingsPage />} />
                    <Route path="appearance" element={<AppearanceSettingsPage />} />
                    <Route path="categories" element={<CategoriesSettingsPage />} />
                    <Route path="notifications" element={<NotificationsSettingsPage />} />
                    <Route path="data" element={<DataSettingsPage />} />
                  </Route>

                  <Route path="*" element={<NotFoundPage />} />
                </Routes>
              </Suspense>
            }
          />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
