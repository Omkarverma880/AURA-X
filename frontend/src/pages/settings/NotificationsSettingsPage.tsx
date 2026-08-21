import { Bell, RefreshCw, CheckCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Badge } from "@/components/ui/Badge";
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
  useRefreshReminders,
} from "@/hooks/useNotifications";
import { formatRelativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";

const SEVERITY_VARIANT = { info: "info", success: "positive", warning: "warning", danger: "negative" } as const;

export function NotificationsSettingsPage() {
  const { data: notifications, isLoading } = useNotifications();
  const refresh = useRefreshReminders();
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle className="flex items-center gap-2"><Bell className="h-4 w-4" /> Notifications</CardTitle>
          <CardDescription>Reminders for due Bahi Khata entries, budgets and goal deadlines.</CardDescription>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" onClick={() => refresh.mutate()} loading={refresh.isPending}>
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </Button>
          <Button size="sm" variant="ghost" onClick={() => markAllRead.mutate()}>
            <CheckCheck className="h-3.5 w-3.5" /> Mark all read
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? null : !notifications?.length ? (
          <EmptyState icon={Bell} title="You're all caught up" description="New reminders will show up here." />
        ) : (
          <div className="divide-y divide-[var(--border-subtle)] -mx-5">
            {notifications.map((n) => (
              <button
                key={n.id}
                onClick={() => !n.is_read && markRead.mutate(n.id)}
                className={cn("flex w-full items-start gap-3 px-5 py-3.5 text-left hover:bg-[var(--bg-surface-hover)]", !n.is_read && "bg-[var(--brand-soft)]/30")}
              >
                <Badge variant={SEVERITY_VARIANT[n.severity]} className="mt-0.5 shrink-0">{n.severity}</Badge>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-[var(--text-primary)]">{n.title}</p>
                  {n.body && <p className="text-xs text-[var(--text-tertiary)]">{n.body}</p>}
                  <p className="mt-0.5 text-[10px] text-[var(--text-tertiary)]">{formatRelativeTime(n.created_at)}</p>
                </div>
              </button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
