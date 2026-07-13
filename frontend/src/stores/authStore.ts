import { create } from 'zustand';
import { getMe } from '../api/auth';

interface User {
  id: string;
  phone: string;
  industry: string | null;
  company_name: string | null;
  plan_type: string;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  setUser: (user: User | null) => void;
  fetchUser: () => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: true,
  setUser: (user) => set({ user }),
  fetchUser: async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        set({ loading: false });
        return;
      }
      const { data } = await getMe();
      set({ user: data, loading: false });
    } catch {
      localStorage.removeItem('token');
      set({ user: null, loading: false });
    }
  },
  logout: () => {
    localStorage.removeItem('token');
    set({ user: null });
  },
}));
