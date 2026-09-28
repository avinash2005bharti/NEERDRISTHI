import { apiRequest, setStoredToken } from '../api/client';
import { AuthResponse, User } from '../../types';

export interface RegisterPayload {
  email: string;
  password: string;
  name: string;
  role?: string;
  vesselClass?: string;
  preferredLanguage?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export const authService = {
  async register(payload: RegisterPayload): Promise<AuthResponse> {
    const res = await apiRequest<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (res.data?.token) {
      setStoredToken(res.data.token);
    }
    return res;
  },

  async login(payload: LoginPayload): Promise<AuthResponse> {
    const res = await apiRequest<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (res.data?.token) {
      setStoredToken(res.data.token);
    }
    return res;
  },

  async logout(): Promise<void> {
    try {
      await apiRequest<{ success: boolean }>('/auth/logout', { method: 'POST' });
    } finally {
      setStoredToken(null);
    }
  },

  async getMe(): Promise<User | null> {
    try {
      const res = await apiRequest<{ success: boolean; data: User }>('/auth/me');
      return res.data;
    } catch {
      return null;
    }
  },

  async updateProfile(profile: Partial<User>): Promise<User> {
    const res = await apiRequest<{ success: boolean; data: User }>('/users/profile', {
      method: 'PUT',
      body: JSON.stringify(profile),
    });
    return res.data;
  },
};
