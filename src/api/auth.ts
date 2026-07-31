import { apiClient } from './client';
import { tokenStorage } from '../lib/storage';

export async function login(username: string, password: string) {
  const { data } = await apiClient.post('/api/auth/login/', { username, password });
  await tokenStorage.setTokens(data.access, data.refresh);
  return data;
}

export async function register(payload: { username: string; email: string; password: string }) {
  const { data } = await apiClient.post('/api/auth/register/', payload);
  return data;
}

export async function logout() {
  const refresh = await tokenStorage.getRefreshToken();
  if (refresh) {
    try {
      await apiClient.post('/api/auth/logout/', { refresh });
    } catch {
      // procedi comunque a pulire i token locali
    }
  }
  await tokenStorage.clearTokens();
}
