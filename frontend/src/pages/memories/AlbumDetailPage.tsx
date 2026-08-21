import { useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Upload, Trash2, ImagePlus, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  useAlbumDetail,
  useDeleteAlbum,
  useDeletePhoto,
  useUploadPhoto,
} from "@/hooks/useMemories";
import { useToast } from "@/contexts/ToastContext";
import { isApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";

export function AlbumDetailPage() {
  const { albumId } = useParams<{ albumId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { data: album, isLoading } = useAlbumDetail(albumId);
  const uploadPhoto = useUploadPhoto();
  const deletePhoto = useDeletePhoto();
  const deleteAlbum = useDeleteAlbum();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [uploading, setUploading] = useState(false);
  const [lightbox, setLightbox] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [deletePhotoId, setDeletePhotoId] = useState<string | null>(null);

  if (isLoading || !album) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <SkeletonCard />
      </div>
    );
  }

  const handleFiles = async (files: FileList | null) => {
    if (!files?.length || !albumId) return;
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        await uploadPhoto.mutateAsync({ albumId, file });
      }
      toast({ title: `${files.length} photo(s) uploaded`, variant: "success" });
    } catch (error) {
      toast({ title: "Upload failed", description: isApiError(error) ? error.message : undefined, variant: "error" });
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <Link to="/memories" className="inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
        <ArrowLeft className="h-4 w-4" /> Back to Memories
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">{album.title}</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            {album.location}
            {album.start_date && ` · ${formatDate(album.start_date, "long")}`}
            {album.end_date && ` - ${formatDate(album.end_date, "long")}`}
          </p>
        </div>
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
          <Button onClick={() => fileInputRef.current?.click()} loading={uploading}>
            <Upload className="h-4 w-4" /> Upload photos
          </Button>
          <Button variant="ghost" className="text-[var(--negative)]" onClick={() => setDeleteConfirm(true)}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {album.notes && <p className="text-sm text-[var(--text-secondary)]">{album.notes}</p>}

      {!album.photos.length ? (
        <Card>
          <EmptyState
            icon={ImagePlus}
            title="No photos yet"
            description="Upload the first photo to this album."
            action={<Button onClick={() => fileInputRef.current?.click()}><Upload className="h-4 w-4" /> Upload photos</Button>}
          />
        </Card>
      ) : (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
          {album.photos.map((photo) => (
            <div key={photo.id} className="group relative aspect-square overflow-hidden rounded-xl bg-[var(--bg-inset)]">
              <img
                src={photo.thumbnail_url ?? photo.url ?? undefined}
                alt={photo.caption ?? ""}
                className="h-full w-full cursor-pointer object-cover transition-transform group-hover:scale-105"
                onClick={() => setLightbox(photo.url)}
              />
              <button
                onClick={(e) => { e.stopPropagation(); setDeletePhotoId(photo.id); }}
                className="absolute right-1.5 top-1.5 rounded-lg bg-black/50 p-1.5 text-white opacity-0 transition-opacity group-hover:opacity-100"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {lightbox && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/85 p-4"
          onClick={() => setLightbox(null)}
        >
          <button className="absolute right-4 top-4 rounded-lg p-2 text-white hover:bg-white/10" onClick={() => setLightbox(null)}>
            <X className="h-6 w-6" />
          </button>
          <img src={lightbox} alt="" className="max-h-[90vh] max-w-full rounded-lg object-contain" />
        </div>
      )}

      <ConfirmDialog
        open={!!deletePhotoId}
        onClose={() => setDeletePhotoId(null)}
        title="Delete this photo?"
        variant="danger"
        confirmLabel="Delete"
        onConfirm={async () => {
          if (!deletePhotoId) return;
          try {
            await deletePhoto.mutateAsync(deletePhotoId);
            toast({ title: "Photo deleted", variant: "success" });
          } catch (error) {
            toast({ title: "Could not delete photo", description: isApiError(error) ? error.message : undefined, variant: "error" });
          }
        }}
      />

      <ConfirmDialog
        open={deleteConfirm}
        onClose={() => setDeleteConfirm(false)}
        title="Delete this album?"
        description="All photos in it will be permanently removed."
        variant="danger"
        confirmLabel="Delete"
        onConfirm={async () => {
          try {
            await deleteAlbum.mutateAsync(album.id);
            toast({ title: "Album deleted", variant: "success" });
            navigate("/memories");
          } catch (error) {
            toast({ title: "Could not delete album", description: isApiError(error) ? error.message : undefined, variant: "error" });
          }
        }}
      />
    </div>
  );
}
