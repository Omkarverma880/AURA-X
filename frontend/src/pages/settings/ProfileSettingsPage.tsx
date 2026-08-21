import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Camera, CheckCircle2, Smartphone, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { FieldHint, Input, Label, Select, Textarea } from "@/components/ui/Input";
import { Avatar } from "@/components/ui/Avatar";
import { PhoneInput } from "@/components/shared/PhoneInput";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/contexts/ToastContext";
import {
  useConfirmPhoneLink,
  useRequestPhoneLinkOtp,
  useUnlinkPhone,
  useUpdateProfile,
  useUploadAvatar,
} from "@/hooks/useProfile";
import { isApiError } from "@/lib/api";

const CURRENCIES = ["INR", "USD", "EUR", "GBP", "AED", "SGD"];

interface ProfileForm {
  full_name: string;
  display_name: string;
  username: string;
  date_of_birth: string;
  currency: string;
  bio: string;
}

export function ProfileSettingsPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const updateProfile = useUpdateProfile();
  const uploadAvatar = useUploadAvatar();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // PhoneInput is a controlled component, so the contact number lives outside
  // react-hook-form - which also means tracking its dirtiness separately.
  const [phone, setPhone] = useState(user?.profile?.phone ?? "");
  const [phoneEdited, setPhoneEdited] = useState(false);

  const { register, handleSubmit, formState: { isSubmitting, isDirty } } = useForm<ProfileForm>({
    defaultValues: {
      full_name: user?.full_name ?? "",
      display_name: user?.profile?.display_name ?? "",
      username: user?.username ?? "",
      date_of_birth: user?.profile?.date_of_birth ?? "",
      currency: user?.profile?.currency ?? "INR",
      bio: user?.profile?.bio ?? "",
    },
  });

  const onSubmit = async (values: ProfileForm) => {
    // Empty strings from untouched date/optional fields must not be sent as
    // "" - the backend's date_of_birth is a real date field and would 422 on
    // an empty string rather than treating it as "not provided".
    const payload: Record<string, unknown> = Object.fromEntries(
      Object.entries(values).filter(([, v]) => v !== ""),
    );
    // Added after the filter above on purpose: an empty phone means "clear my
    // number", which the filter would otherwise drop.
    if (phoneEdited) payload.phone = phone;

    try {
      await updateProfile.mutateAsync(payload);
      setPhoneEdited(false);
      toast({ title: "Profile updated", variant: "success" });
    } catch (error) {
      toast({ title: "Could not update profile", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  const handleAvatarChange = async (file: File | null) => {
    if (!file) return;
    try {
      await uploadAvatar.mutateAsync(file);
      toast({ title: "Photo updated", variant: "success" });
    } catch (error) {
      toast({ title: "Could not upload photo", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <div className="space-y-5">
      <Card>
        <CardHeader>
          <CardTitle>Profile photo</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-4">
          <div className="relative">
            <Avatar name={user?.full_name ?? "?"} src={user?.profile?.avatar_url} size="lg" />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full bg-[var(--brand)] text-white shadow-soft"
              aria-label="Change photo"
            >
              <Camera className="h-3.5 w-3.5" />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(e) => handleAvatarChange(e.target.files?.[0] ?? null)}
            />
          </div>
          <div>
            <p className="text-sm font-medium text-[var(--text-primary)]">{user?.full_name}</p>
            <p className="text-xs text-[var(--text-tertiary)]">{user?.email}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Personal details</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="full_name">Full name</Label>
                <Input id="full_name" {...register("full_name")} />
              </div>
              <div>
                <Label htmlFor="display_name">Display name</Label>
                <Input id="display_name" {...register("display_name")} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="date_of_birth">Date of birth</Label>
                <Input id="date_of_birth" type="date" {...register("date_of_birth")} />
              </div>
              <div>
                <Label htmlFor="currency">Currency</Label>
                <Select id="currency" {...register("currency")}>
                  {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="username">Username</Label>
              <Input id="username" {...register("username")} />
              <FieldHint>
                Lower-case letters, numbers and underscores. You can use this to
                reset your password if you forget which e-mail you signed up with.
              </FieldHint>
            </div>
            <div>
              <Label htmlFor="contact_phone">Phone number</Label>
              <PhoneInput
                id="contact_phone"
                value={phone}
                onChange={(next) => { setPhone(next); setPhoneEdited(true); }}
              />
              <FieldHint>
                Saved to your profile as a contact number. To use it to sign in,
                verify it under Phone sign-in below.
              </FieldHint>
            </div>
            <div>
              <Label htmlFor="bio">Bio</Label>
              <Textarea id="bio" rows={2} {...register("bio")} />
            </div>
            <Button type="submit" loading={isSubmitting} disabled={!isDirty && !phoneEdited}>
              Save changes
            </Button>
          </form>
        </CardContent>
      </Card>

      <PhoneLinkCard />
    </div>
  );
}

function PhoneLinkCard() {
  const { user } = useAuth();
  const { toast } = useToast();
  const requestOtp = useRequestPhoneLinkOtp();
  const confirmLink = useConfirmPhoneLink();
  const unlinkPhone = useUnlinkPhone();

  const [phone, setPhone] = useState("");
  const [step, setStep] = useState<"idle" | "code">("idle");
  const [code, setCode] = useState("");
  const [debugCode, setDebugCode] = useState<string | null>(null);
  const [sentMessage, setSentMessage] = useState<string>("");

  const startLink = async () => {
    try {
      const result = await requestOtp.mutateAsync(phone);
      setDebugCode(result.debug_code);
      setSentMessage(result.message);
      setStep("code");
    } catch (error) {
      toast({ title: "Could not send code", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  const verify = async () => {
    try {
      await confirmLink.mutateAsync(code);
      toast({ title: "Phone number linked", variant: "success" });
      setStep("idle");
      setCode("");
      setPhone("");
    } catch (error) {
      toast({ title: "Could not verify code", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Phone sign-in</CardTitle>
      </CardHeader>
      <CardContent>
        {user?.phone && user.phone_verified ? (
          <div className="flex items-center justify-between rounded-xl bg-[var(--positive-soft)] p-3.5">
            <div className="flex items-center gap-2 text-sm text-[var(--positive-soft-text)]">
              <CheckCircle2 className="h-4 w-4" /> {user.phone} is linked for sign-in
            </div>
            <button
              onClick={() => unlinkPhone.mutate()}
              className="rounded-lg p-1.5 text-[var(--positive-soft-text)] hover:bg-black/5"
              aria-label="Unlink phone"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : step === "idle" ? (
          <div className="space-y-3">
            <PhoneInput value={phone} onChange={setPhone} />
            <Button onClick={startLink} loading={requestOtp.isPending} disabled={!phone}>
              <Smartphone className="h-4 w-4" /> Send code
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex gap-2">
              <Input
                placeholder="000000"
                inputMode="numeric"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              />
              <Button onClick={verify} loading={confirmLink.isPending}>Verify</Button>
            </div>
            {sentMessage && (
              <p className="text-xs text-[var(--text-tertiary)]">{sentMessage}</p>
            )}
            {debugCode && (
              <p className="text-xs text-[var(--text-tertiary)]">
                Development mode - code is <span className="font-mono">{debugCode}</span>
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
