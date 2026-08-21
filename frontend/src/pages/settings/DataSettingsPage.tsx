import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileJson, FileArchive, Trash2, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Label } from "@/components/ui/Input";
import { Dialog } from "@/components/ui/Dialog";
import { FinancialLock } from "@/components/shared/FinancialLock";
import { api, isApiError } from "@/lib/api";
import { useFinancial } from "@/contexts/FinancialContext";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/contexts/ToastContext";
import { useDeleteAccount } from "@/hooks/useProfile";

async function downloadFile(url: string, filename: string) {
  const response = await api.get(url, { responseType: "blob" });
  const blobUrl = window.URL.createObjectURL(response.data as Blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

export function DataSettingsPage() {
  const { isUnlocked, isPinConfigured, promptUnlock } = useFinancial();
  const { toast } = useToast();
  const [exporting, setExporting] = useState<"json" | "csv" | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const locked = isPinConfigured && !isUnlocked;

  const handleExport = async (format: "json" | "csv") => {
    if (locked) {
      promptUnlock(() => void handleExport(format));
      return;
    }
    setExporting(format);
    try {
      const date = new Date().toISOString().slice(0, 10);
      if (format === "json") {
        await downloadFile("/export/json", `bahi-khata-export-${date}.json`);
      } else {
        await downloadFile("/export/csv", `bahi-khata-export-${date}.zip`);
      }
      toast({ title: "Export ready", variant: "success" });
    } catch (error) {
      toast({ title: "Export failed", description: isApiError(error) ? error.message : undefined, variant: "error" });
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="space-y-5">
      <Card>
        <CardHeader>
          <CardTitle>Export your data</CardTitle>
          <CardDescription>Download everything you have stored in Aura X.</CardDescription>
        </CardHeader>
        <CardContent>
          {locked ? (
            <FinancialLock title="Export is confidential" description="Enter your Green PIN to export your data." />
          ) : (
            <div className="flex flex-wrap gap-3">
              <Button variant="secondary" onClick={() => handleExport("json")} loading={exporting === "json"}>
                <FileJson className="h-4 w-4" /> Export as JSON
              </Button>
              <Button variant="secondary" onClick={() => handleExport("csv")} loading={exporting === "csv"}>
                <FileArchive className="h-4 w-4" /> Export as CSV (.zip)
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border-[var(--negative)]/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-[var(--negative)]"><AlertTriangle className="h-4 w-4" /> Danger zone</CardTitle>
          <CardDescription>Permanently delete your account and everything in it.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="danger" onClick={() => setDeleteOpen(true)}>
            <Trash2 className="h-4 w-4" /> Delete account
          </Button>
        </CardContent>
      </Card>

      <DeleteAccountDialog open={deleteOpen} onClose={() => setDeleteOpen(false)} />
    </div>
  );
}

function DeleteAccountDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [confirmText, setConfirmText] = useState("");
  const { logout } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const deleteAccount = useDeleteAccount();

  const handleDelete = async () => {
    try {
      await deleteAccount.mutateAsync(confirmText);
      toast({ title: "Account deleted", variant: "success" });
      await logout();
      navigate("/login");
    } catch (error) {
      toast({ title: "Could not delete account", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title="Delete your account" mobileSheet={false}>
      <div className="space-y-4">
        <p className="text-sm text-[var(--text-secondary)]">
          This permanently deletes your Bahi Khata, expenses, investments, goals and memories. This
          cannot be undone.
        </p>
        <div>
          <Label htmlFor="confirm">Type <span className="font-mono font-semibold">DELETE</span> to confirm</Label>
          <Input id="confirm" value={confirmText} onChange={(e) => setConfirmText(e.target.value)} />
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="danger" disabled={confirmText !== "DELETE"} loading={deleteAccount.isPending} onClick={handleDelete}>
            Delete permanently
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
