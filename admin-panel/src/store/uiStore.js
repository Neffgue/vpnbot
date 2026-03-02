import { create } from 'zustand'

let toastId = 0

export const uiStore = create((set) => ({
  toasts: [],

  addToast: (message, type = 'info') => {
    const id = toastId++
    set((state) => ({
      toasts: [...state.toasts, { id, message, type }]
    }))
    setTimeout(() => {
      set((state) => ({
        toasts: state.toasts.filter(t => t.id !== id)
      }))
    }, 4000)
    return id
  },

  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter(t => t.id !== id)
    })),

  clearToasts: () =>
    set({ toasts: [] })
}))

// Helper functions
export const showSuccess = (message) => uiStore.getState().addToast(message, 'success')
export const showError = (message) => uiStore.getState().addToast(message, 'error')
export const showInfo = (message) => uiStore.getState().addToast(message, 'info')
