import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input, Label, FieldError, Select, Textarea } from "@/components/ui/Input";
import { useCreateAlbum } from "@/hooks/useMemories";
import { useToast } from "@/contexts/ToastContext";
import { isApiError } from "@/lib/api";

const schema = z.object({
  title: z.string().min(1, "Name this album."),
  album_type: z.string(),
  location: z.string().optional(),
  start_date: z.string().optional(),
  end_date: z.string().optional(),
  notes: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export function AddAlbumDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { toast } = useToast();
  const createAlbum = useCreateAlbum();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { album_type: "general" } });

  const handleClose = () => {
    reset();
    onClose();
  };

  const onSubmit = async (values: FormValues) => {
    try {
      await createAlbum.mutateAsync(values);
      toast({ title: "Album created", variant: "success" });
      handleClose();
    } catch (error) {
      toast({ title: "Could not create album", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} title="New album">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <Label htmlFor="title">Album name</Label>
          <Input id="title" placeholder="e.g. Uttarakhand 4 Dham - 2026" {...register("title")} error={!!errors.title} />
          <FieldError>{errors.title?.message}</FieldError>
        </div>

        <div>
          <Label htmlFor="album_type">Type</Label>
          <Select id="album_type" {...register("album_type")}>
            <option value="general">General</option>
            <option value="trip">Trip</option>
            <option value="trek">Trek</option>
            <option value="family">Family</option>
            <option value="event">Event</option>
          </Select>
        </div>

        <div>
          <Label htmlFor="location">Location (optional)</Label>
          <Input id="location" {...register("location")} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="start_date">Start date</Label>
            <Input id="start_date" type="date" {...register("start_date")} />
          </div>
          <div>
            <Label htmlFor="end_date">End date</Label>
            <Input id="end_date" type="date" {...register("end_date")} />
          </div>
        </div>

        <div>
          <Label htmlFor="notes">Notes (optional)</Label>
          <Textarea id="notes" rows={2} {...register("notes")} />
        </div>

        <Button type="submit" className="w-full" loading={isSubmitting}>
          Create album
        </Button>
      </form>
    </Dialog>
  );
}
