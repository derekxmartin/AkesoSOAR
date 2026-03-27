import { useMutation, useQuery } from "@tanstack/react-query";
import api from "../lib/api";

export function useApiGet<T>(key: string[], url: string, params?: Record<string, any>) {
  return useQuery<T>({
    queryKey: [...key, params],
    queryFn: async () => {
      const { data } = await api.get(url, { params });
      return data;
    },
  });
}

export function useApiPost<T>(url: string, options?: { onSuccess?: () => void }) {
  return useMutation<T, Error, any>({
    mutationFn: async (body) => {
      const { data } = await api.post(url, body);
      return data;
    },
    onSuccess: () => {
      options?.onSuccess?.();
    },
  });
}

export function useApiPatch<T>(url: string, options?: { onSuccess?: () => void }) {
  return useMutation<T, Error, any>({
    mutationFn: async (body) => {
      const { data } = await api.patch(url, body);
      return data;
    },
    onSuccess: () => {
      options?.onSuccess?.();
    },
  });
}

export function useApiDelete(url: string, options?: { onSuccess?: () => void }) {
  return useMutation<void, Error, void>({
    mutationFn: async () => {
      await api.delete(url);
    },
    onSuccess: () => {
      options?.onSuccess?.();
    },
  });
}
