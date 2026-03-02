import React, { useEffect } from 'react'
import { AlertCircle, CheckCircle, Info } from 'lucide-react'
import { uiStore } from '../store/uiStore'

export default function Toast() {
  const { toasts, removeToast } = uiStore()

  return (
    <div className="fixed bottom-4 right-4 space-y-2 z-50">
      {toasts.map((toast) => {
        const icons = {
          success: <CheckCircle size={20} />,
          error: <AlertCircle size={20} />,
          info: <Info size={20} />
        }

        const colors = {
          success: 'bg-green-900 text-green-200 border-green-700',
          error: 'bg-red-900 text-red-200 border-red-700',
          info: 'bg-blue-900 text-blue-200 border-blue-700'
        }

        return (
          <div
            key={toast.id}
            className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${colors[toast.type]} min-w-80 animate-fade-in`}
          >
            <div className="flex-shrink-0">
              {icons[toast.type]}
            </div>
            <p className="flex-1">{toast.message}</p>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-lg leading-none hover:opacity-70"
            >
              ×
            </button>
          </div>
        )
      })}
    </div>
  )
}

// Auto-remove toasts after 4 seconds
Toast.useEffect = () => {
  const timeouts = []
  const handleToastAdded = (toast) => {
    const timeout = setTimeout(() => {
      uiStore.getState().removeToast(toast.id)
    }, 4000)
    timeouts.push(timeout)
  }

  return () => {
    timeouts.forEach(timeout => clearTimeout(timeout))
  }
}
