"use client";

import { create } from "zustand";

interface AuthState {
  token: string | null;
  userId: string | null;
  name: string | null;
  role: string | null;
  isAuthenticated: boolean;

  setAuth: (token: string, userId: string, name: string, role: string) => void;
  logout: () => void;
  hydrate: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  userId: null,
  name: null,
  role: null,
  isAuthenticated: false,

  setAuth: (token, userId, name, role) => {
    localStorage.setItem("token", token);
    localStorage.setItem("userId", userId);
    localStorage.setItem("userName", name);
    localStorage.setItem("userRole", role);
    set({ token, userId, name, role, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("userId");
    localStorage.removeItem("userName");
    localStorage.removeItem("userRole");
    set({ token: null, userId: null, name: null, role: null, isAuthenticated: false });
  },

  hydrate: () => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("token");
    const userId = localStorage.getItem("userId");
    const name = localStorage.getItem("userName");
    const role = localStorage.getItem("userRole");
    if (token && userId) {
      set({ token, userId, name, role, isAuthenticated: true });
    }
  },
}));
