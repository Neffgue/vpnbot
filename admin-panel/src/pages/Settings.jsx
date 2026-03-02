import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Save, RefreshCw, Eye, EyeOff } from 'lucide-react'
import client from '../api/client'

export default function Settings() {
  const qc = useQueryClient()
  const [showToken, setShowToken] = useState(false)
  const [toast, setToast] = useState(null)

  const { data: settings, isLoading } = useQuery({
    queryKey: ['system-settings'],
    queryFn: () => client.get('/admin/system-settings').then(r => r.data),
    staleTime: 15000,
  })

  const [formData, setFormData] = useState(null)
  const current = formData ?? settings ?? {}

  React.useEffect(() => {
    if (settings && !formData) {
      setFormData({
        bot_token: settings.bot_token || '',
        webhook_url: settings.webhook_url || '',
        admin_username: settings.admin_username || 'admin',
        admin_password: '',
        min_withdrawal: settings.min_withdrawal ?? 10,
        max_daily_withdrawal: settings.max_daily_withdrawal ?? 1000,
        referral_percent: settings.referral_percent ?? 10,
      })
    }
  }, [settings])

  const updateMutation = useMutation({
    mutationFn: (data) => {
      // Don't send empty password (means unchanged)
      const payload = { ...data }
      if (!payload.admin_password) delete payload.admin_password
      return client.put('/admin/system-settings', payload)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['system-settings'] })
      setToast({ type: 'success', message: '✅ Настройки сохранены!' })
      setTimeout(() => setToast(null), 3000)
    },
    onError: (err) => {
      setToast({ type: 'error', message: '❌ Ошибка сохранения: ' + (err?.response?.data?.detail || err.message) })
      setTimeout(() => setToast(null), 5000)
    },
  })

  function set(key, value) {
    setFormData(f => ({ ...(f ?? settings ?? {}), [key]: value }))
  }

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="text-gray-400 mt-4">Загрузка...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-5 py-3 rounded-lg shadow-lg text-white font-medium ${toast.type === 'success' ? 'bg-green-600' : 'bg-red-600'}`}>
          {toast.message}
        </div>
      )}

      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Настройки системы</h1>
        <p className="text-gray-400">Токен бота, вебхук и системные параметры</p>
      </div>

      <div className="bg-dark-800 rounded-lg p-6 border border-dark-700 max-w-2xl space-y-6">

        {/* Bot Token section */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-4 border-b border-dark-700 pb-2">🤖 Telegram Bot</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1" htmlFor="bot_token">
                Токен бота <span className="text-xs text-gray-500">(получить у @BotFather)</span>
              </label>
              <div className="relative">
                <input
                  id="bot_token"
                  type={showToken ? 'text' : 'password'}
                  value={current.bot_token || ''}
                  onChange={(e) => set('bot_token', e.target.value)}
                  placeholder="1234567890:AAXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
                  className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2.5 pr-10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="button"
                  onClick={() => setShowToken(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                >
                  {showToken ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {current.bot_token && (
                <p className="text-xs text-green-400 mt-1">✅ Токен задан</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1" htmlFor="webhook_url">
                URL вебхука <span className="text-xs text-gray-500">(оставьте пустым для polling)</span>
              </label>
              <input
                id="webhook_url"
                type="text"
                value={current.webhook_url || ''}
                onChange={(e) => set('webhook_url', e.target.value)}
                placeholder="https://yourdomain.com/webhook"
                className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Admin credentials */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-4 border-b border-dark-700 pb-2">🔐 Доступ к панели</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1" htmlFor="admin_username">Логин</label>
              <input
                id="admin_username"
                type="text"
                value={current.admin_username || ''}
                onChange={(e) => set('admin_username', e.target.value)}
                placeholder="admin"
                className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1" htmlFor="admin_password">
                Пароль <span className="text-xs text-gray-500">(оставьте пустым — без изменений)</span>
              </label>
              <input
                id="admin_password"
                type="password"
                value={current.admin_password || ''}
                onChange={(e) => set('admin_password', e.target.value)}
                placeholder="Новый пароль..."
                className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Financial settings */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-4 border-b border-dark-700 pb-2">💰 Финансы</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1" htmlFor="min_withdrawal">
                Минимальный вывод (₽)
              </label>
              <input
                id="min_withdrawal"
                type="number"
                value={current.min_withdrawal ?? 10}
                onChange={(e) => set('min_withdrawal', parseFloat(e.target.value))}
                min="0"
                step="1"
                className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1" htmlFor="max_daily_withdrawal">
                Макс. дневной вывод (₽)
              </label>
              <input
                id="max_daily_withdrawal"
                type="number"
                value={current.max_daily_withdrawal ?? 1000}
                onChange={(e) => set('max_daily_withdrawal', parseFloat(e.target.value))}
                min="0"
                step="1"
                className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1" htmlFor="referral_percent">
                Реферальный бонус (%)
              </label>
              <input
                id="referral_percent"
                type="number"
                value={current.referral_percent ?? 10}
                onChange={(e) => set('referral_percent', parseFloat(e.target.value))}
                min="0"
                max="100"
                step="0.1"
                className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        <button
          onClick={() => updateMutation.mutate(current)}
          disabled={updateMutation.isPending}
          className="flex items-center gap-2 w-full justify-center px-4 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium text-white disabled:opacity-50 transition-colors"
        >
          {updateMutation.isPending
            ? <><RefreshCw size={16} className="animate-spin" /> Сохранение...</>
            : <><Save size={16} /> Сохранить настройки</>
          }
        </button>
      </div>
    </div>
  )
}
