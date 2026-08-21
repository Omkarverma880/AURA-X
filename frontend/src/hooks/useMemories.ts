import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Album, AlbumDetail, Photo } from "@/types";

function invalidateAll(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: ["memories"] });
  void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  void queryClient.invalidateQueries({ queryKey: ["analytics"] });
}

export function useAlbums(params?: { album_type?: string; search?: string }) {
  return useQuery({
    queryKey: ["memories", "albums", params],
    queryFn: async () => {
      const { data } = await api.get<Album[]>("/memories/albums", { params });
      return data;
    },
  });
}

export function useAlbumDetail(id: string | undefined) {
  return useQuery({
    queryKey: ["memories", "album", id],
    queryFn: async () => {
      const { data } = await api.get<AlbumDetail>(`/memories/albums/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateAlbum() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: Record<string, unknown>) => {
      const { data } = await api.post<AlbumDetail>("/memories/albums", input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useDeleteAlbum() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.delete(`/memories/albums/${id}`);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useUploadPhoto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ albumId, file, caption }: { albumId: string; file: File; caption?: string }) => {
      const form = new FormData();
      form.append("file", file);
      if (caption) form.append("caption", caption);
      const { data } = await api.post<Photo>(`/memories/albums/${albumId}/photos`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useDeletePhoto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.delete(`/memories/photos/${id}`);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useUpdateAlbum() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...input }: { id: string; [key: string]: unknown }) => {
      const { data } = await api.patch<AlbumDetail>(`/memories/albums/${id}`, input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}
