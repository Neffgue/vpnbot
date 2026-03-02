import { create } from 'zustand'

export const useAuthStore = create((set) => ({
  isAuthenticated: !!localStorage.getItem('access_token'),
  user: null,

  setUser: (user) =>
    set({
      user,
      isAuthenticated: !!user
    }),

  logout: () =>
    set({
      user: null,
      isAuthenticated: false
    })
}))
