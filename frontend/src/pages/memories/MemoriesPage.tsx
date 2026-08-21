import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Images, MapPin, Heart } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { AddAlbumDialog } from "@/components/memories/AddAlbumDialog";
import { useAlbums } from "@/hooks/useMemories";
import { formatDate } from "@/lib/format";

export function MemoriesPage() {
  const [addOpen, setAddOpen] = useState(false);
  const { data: albums, isLoading } = useAlbums();

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Memories</h1>
          <p className="text-sm text-[var(--text-secondary)]">Trips, treks and moments worth keeping.</p>
        </div>
        <Button onClick={() => setAddOpen(true)}><Plus className="h-4 w-4" /> New album</Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : !albums?.length ? (
        <Card>
          <EmptyState
            icon={Images}
            title="No memories yet"
            description="Create your first album for a trip, trek or family moment."
            action={<Button onClick={() => setAddOpen(true)}><Plus className="h-4 w-4" /> New album</Button>}
          />
        </Card>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {albums.map((album) => (
            <Link key={album.id} to={`/memories/${album.id}`}>
              <Card className="group overflow-hidden transition-transform hover:-translate-y-0.5 hover:shadow-elevated">
                <div className="relative aspect-square bg-[var(--bg-inset)]">
                  {album.cover_photo_url ? (
                    <img src={album.cover_photo_url} alt={album.title} className="h-full w-full object-cover" />
                  ) : (
                    <div className="flex h-full items-center justify-center">
                      <Images className="h-8 w-8 text-[var(--text-tertiary)]" />
                    </div>
                  )}
                  {album.is_favourite && (
                    <Heart className="absolute right-2 top-2 h-4 w-4 fill-[var(--negative)] text-[var(--negative)]" />
                  )}
                </div>
                <div className="p-3">
                  <p className="truncate text-sm font-semibold text-[var(--text-primary)]">{album.title}</p>
                  <div className="mt-0.5 flex items-center gap-2 text-xs text-[var(--text-tertiary)]">
                    {album.location && (
                      <span className="flex items-center gap-0.5 truncate"><MapPin className="h-3 w-3 shrink-0" /> {album.location}</span>
                    )}
                    <span className="ml-auto shrink-0">{album.photo_count} photos</span>
                  </div>
                  {album.start_date && <p className="mt-0.5 text-[10px] text-[var(--text-tertiary)]">{formatDate(album.start_date, "short")}</p>}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}

      <AddAlbumDialog open={addOpen} onClose={() => setAddOpen(false)} />
    </div>
  );
}
