import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Save, RefreshCw, X, Image } from 'lucide-react'
import api from '../api/client'
import Toast from '../components/Toast'

/**
 * Настройки бота — медиа, welcome-картинка, тарифы, реферальная программа,
 * поддержка, каналы. Все изменения без перезагрузки бота.
 */
export default function BotSettings() {
  const qc = useQueryClient()
  const [toast, setToast] = useState(null)
  const [activeTab, setActiveTab] = useState('general')
  const [form, setForm] = useState(null)

  const { data: settings = {}, isLoading } = useQuery({
    queryKey: ['bot-settings'],
    queryFn: () => api.get('/admin/settings').then(r => r.data ?? {}),
    staleTime: 10000,
  })

  // Инициализируем форму когда загрузились настройки
  useEffect(() => {
    if (!isLoading && settings && Object.keys(settings).length >= 0) {
      setForm(prev => prev === null ? { ...settings } : prev)
    }
  }, [settings, isLoading])

  const saveMutation = useMutation({
    mutationFn: (data) => api.put('/admin/settings', data),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['bot-settings'] })
      setToast({ type: 'success', message: 'Настройки сохранены и применены мгновенно!' })
    },
    onError: (err) => {
      const detail = err?.response?.data?.detail || 'Ошибка сохранения'
      setToast({ type: 'error', message: detail })
    },
  })

  // current = объединение загруженных settings + изменений из формы
  const current = { ...settings, ...(form || {}) }

  function set(key, value) {
    setForm(f => ({ ...(f || {}), [key]: value }))
  }

  if (isLoading) return <div className="text-center py-10 text-gray-400">Загрузка...</div>

  const tabs = [
    { id: 'general', label: 'Основные' },
    { id: 'media', label: '🖼️ Медиа' },
        { id: 'notifications', label: '🔔 Уведомления' },
  ]

  return (
    <div className="space-y-4">
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      {/* Tabs */}
      <div className="flex gap-2 overflow-x-auto">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
              activeTab === t.id
                ? 'bg-blue-600 text-white shadow'
                : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >{t.label}</button>
        ))}
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        {activeTab === 'general' && (
          <GeneralTab current={current} set={set} />
        )}
        {activeTab === 'media' && (
          <MediaTab current={current} set={set} />
        )}
        {activeTab === 'notifications' && (
          <NotificationsTab current={current} set={set} />
        )}

        {/* Save */}
        <div className="mt-6 pt-4 border-t border-gray-100 flex items-center justify-between">
          <p className="text-xs text-green-600">
            ✅ Изменения применяются без перезагрузки бота
          </p>
          <button
            onClick={() => saveMutation.mutate(current)}
            disabled={saveMutation.isPending}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
          >
            {saveMutation.isPending ? <RefreshCw size={16} className="animate-spin" /> : <Save size={16} />}
            Сохранить настройки
          </button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, hint, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
      {hint && <p className="text-xs text-gray-400 mt-1">{hint}</p>}
    </div>
  )
}

function Input({ value, onChange, ...props }) {
  return (
    <input
      className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      value={value ?? ''}
      onChange={e => onChange(e.target.value)}
      {...props}
    />
  )
}

function GeneralTab({ current, set }) {
  return (
    <div className="space-y-5">
      <h3 className="font-semibold text-gray-800 mb-4">Основные настройки</h3>
      <div className="grid grid-cols-2 gap-5">
        <Field label="Пользователь поддержки" hint="Например: @support (без @)">
          <Input value={current.support_username} onChange={v => set('support_username', v)} placeholder="support_username" />
        </Field>
        <Field label="Канал" hint="Например: @channel (без @)">
          <Input value={current.channel_username} onChange={v => set('channel_username', v)} placeholder="vpn_channel" />
        </Field>
        <Field label="Имя бота" hint="Отображается в приветствии">
          <Input value={current.bot_name} onChange={v => set('bot_name', v)} placeholder="VPN Bot" />
        </Field>
        <Field label="ID канала подписки" hint="Например: -1001234567890">
          <Input value={current.channel_id} onChange={v => set('channel_id', v)} placeholder="-1001234567890" />
        </Field>
      </div>
      <Field label="Описание бота">
        <textarea
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm h-24 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={current.bot_description ?? ''}
          onChange={e => set('bot_description', e.target.value)}
          placeholder="Описание бота..."
        />
      </Field>
      <div className="grid grid-cols-2 gap-5">
        <Field label="Бесплатный пробный период (часов)" hint="По умолчанию 24">
          <Input type="number" min="1" value={current.trial_hours ?? 24} onChange={v => set('trial_hours', Number(v))} />
        </Field>
        <Field label="Лимит реферальных бонусов (дней)" hint="Максимум бонусных дней">
          <Input type="number" min="0" value={current.referral_bonus_days ?? 30} onChange={v => set('referral_bonus_days', Number(v))} />
        </Field>
      </div>
    </div>
  )
}

function MediaTab({ current, set }) {
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState(null)

  async function uploadImage(file, field) {
    setUploading(true)
    setUploadError(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await api.post('/admin/upload-image', fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      if (res.data.url) {
        set(field, res.data.url)
      } else {
        setUploadError('Не удалось получить URL изображения')
      }
    } catch (e) {
      console.error('Ошибка загрузки', e)
      setUploadError('Ошибка загрузки: ' + (e?.response?.data?.detail || e.message))
    } finally {
      setUploading(false)
    }
  }

  const mediaFields = [
    { key: 'welcome_image', label: 'Картинка приветствия' },
    { key: 'free_trial_image', label: 'Картинка пробного доступа' },
    { key: 'payment_image', label: 'Картинка оплаты' },
    { key: 'cabinet_image', label: 'Картинка кабинета' },
  ]

  return (
    <div className="space-y-5">
      <h3 className="font-semibold text-gray-800 mb-4">Изображения</h3>
      <p className="text-sm text-gray-500">
        Добавьте изображения для отображения в боте. JPG, PNG, GIF (макс 5MB).
      </p>
      <div className="grid grid-cols-2 gap-5">
        {mediaFields.map(({ key, label }) => (
          <div key={key} className="border border-gray-200 rounded-xl p-4">
            <div className="text-sm font-medium text-gray-700 mb-3">{label}</div>
            {current[key] ? (
              <div className="relative">
                <img src={current[key]} alt={label} className="w-full h-36 object-cover rounded-lg" />
                <button
                  onClick={() => set(key, '')}
                  className="absolute top-2 right-2 bg-white rounded-full p-1 shadow hover:bg-red-50"
                ><X size={14} className="text-red-500" /></button>
              </div>
            ) : (
              <label className="flex flex-col items-center justify-center h-36 border-2 border-dashed border-gray-200 rounded-lg cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors">
                <Image size={24} className="text-gray-300 mb-2" />
                <span className="text-xs text-gray-400">Кликните для загрузки</span>
                <input
                  type="file" accept="image/*" className="hidden"
                  onChange={e => e.target.files?.[0] && uploadImage(e.target.files[0], key)}
                />
              </label>
            )}
            <div className="mt-2">
              <Input
                value={current[key] ?? ''}
                onChange={v => set(key, v)}
                placeholder="Или вставьте URL изображения"
              />
            </div>
          </div>
        ))}
      </div>
      {uploading && (
        <div className="text-sm text-blue-600 flex items-center gap-2">
          <RefreshCw size={14} className="animate-spin" /> Загрузка...
        </div>
      )}
      {uploadError && (
        <div className="text-sm text-red-600 flex items-center gap-2">
          ⚠️ {uploadError}
        </div>
      )}
    </div>
  )
}

function PlansTab({ current, set }) {
  const plans = current.plans ?? [
    { id: 'Solo', name: 'Соло', device_limit: 1, description: '1 устройство, 100 ГБ трафика' },
    { id: 'Family', name: 'Семейный', device_limit: 5, description: '5 устройств, 500 ГБ трафика' },
  ]

  function updatePlan(idx, key, val) {
    const newPlans = plans.map((p, i) => i === idx ? { ...p, [key]: val } : p)
    set('plans', newPlans)
  }

  return (
    <div className="space-y-5">
      <h3 className="font-semibold text-gray-800 mb-4">Планы</h3>
      {plans.map((plan, idx) => (
        <div key={plan.id} className="border border-gray-200 rounded-xl p-4">
          <div className="text-sm font-semibold text-gray-700 mb-3">📦 {plan.name}</div>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Имя">
              <Input value={plan.name} onChange={v => updatePlan(idx, 'name', v)} />
            </Field>
            <Field label="Устройств">
              <Input type="number" min="1" value={plan.device_limit} onChange={v => updatePlan(idx, 'device_limit', Number(v))} />
            </Field>
            <Field label="Трафик (ГБ)">
              <Input type="number" min="1" value={plan.traffic_gb ?? 100} onChange={v => updatePlan(idx, 'traffic_gb', Number(v))} />
            </Field>
            <Field label="Описание" className="col-span-3">
              <Input value={plan.description} onChange={v => updatePlan(idx, 'description', v)} />
            </Field>
          </div>
        </div>
      ))}
    </div>
  )
}

function ReferralTab({ current, set }) {
  return (
    <div className="space-y-5">
      <h3 className="font-semibold text-gray-800 mb-4">Партнёрская программа</h3>
      <div className="grid grid-cols-2 gap-5">
        <Field label="Бонус партнёру (дней)" hint="Дней партнёру">
          <Input type="number" min="0" value={current.referral_bonus_days ?? 7} onChange={v => set('referral_bonus_days', Number(v))} />
        </Field>
        <Field label="Бонус приглашённому (дней)" hint="Дней приглашённому">
          <Input type="number" min="0" value={current.invited_bonus_days ?? 0} onChange={v => set('invited_bonus_days', Number(v))} />
        </Field>
        <Field label="Минимум вывода (₽)" hint="Минимум для вывода средств">
          <Input type="number" min="0" value={current.min_withdrawal ?? 500} onChange={v => set('min_withdrawal', Number(v))} />
        </Field>
        <Field label="% партнёра" hint="% от платежей">
          <Input type="number" min="0" max="100" value={current.partner_percent ?? 20} onChange={v => set('partner_percent', Number(v))} />
        </Field>
      </div>
      <Field label="Текст программы">
        <textarea
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm h-28 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={current.referral_text ?? ''}
          onChange={e => set('referral_text', e.target.value)}
          placeholder="Описание для пользователей..."
        />
      </Field>
    </div>
  )
}

function NotificationsTab({ current, set }) {
  return (
    <div className="space-y-5">
      <h3 className="font-semibold text-gray-800 mb-4">Уведомления</h3>
      <div className="grid grid-cols-2 gap-5">
        <Field label="За X часов (1)" hint="По умолчанию 24">
          <Input type="number" min="1" value={current.notify_hours_before_1 ?? 24} onChange={v => set('notify_hours_before_1', Number(v))} />
        </Field>
        <Field label="За X часов (2)" hint="По умолчанию 1">
          <Input type="number" min="1" value={current.notify_hours_before_2 ?? 1} onChange={v => set('notify_hours_before_2', Number(v))} />
        </Field>
      </div>
      <div className="space-y-3">
        {[
          { key: 'notify_enable_24h', label: 'За 24 часа' },
          { key: 'notify_enable_1h', label: 'За 1 час' },
          { key: 'notify_enable_expired', label: 'Истечение подписки' },
          { key: 'notify_enable_welcome', label: 'При регистрации' },
        ].map(({ key, label }) => (
          <label key={key} className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={current[key] ?? true}
              onChange={e => set(key, e.target.checked)}
              className="w-4 h-4 accent-blue-600"
            />
            <span className="text-sm text-gray-700">{label}</span>
          </label>
        ))}
      </div>
    </div>
  )
}


