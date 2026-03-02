import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Save, RefreshCw, Eye, EyeOff, Plus, Trash2 } from 'lucide-react'
import api from '../api/client'
import Toast from '../components/Toast'

const DEFAULT_KEYS = [
  { key: 'welcome', label: 'Приветствие (/start)' },
  { key: 'free_trial_success', label: 'Успешный пробный доступ' },
  { key: 'free_trial_used', label: 'Пробный период уже использован' },
  { key: 'subscription_required', label: 'Требуется подписка' },
  { key: 'referral_header', label: 'Заголовок реферальной программы' },
  { key: 'cabinet_header', label: 'Заголовок личного кабинета' },
  { key: 'support_text', label: 'Текст поддержки' },
  { key: 'channel_text', label: 'Текст канала' },
  { key: 'payment_success', label: 'Успешная оплата' },
  { key: 'payment_failed', label: 'Ошибка оплаты' },
  { key: 'subscription_expiring_24h', label: 'Уведомление за 24 часа до конца' },
  { key: 'subscription_expiring_12h', label: 'Уведомление за 12 часов до конца' },
  { key: 'subscription_expiring_1h', label: 'Уведомление за 1 час до конца' },
  { key: 'subscription_expired', label: 'Подписка истекла' },
  { key: 'subscription_expired_3h', label: 'Истекла 3 часа назад' },
]

export default function BotTexts() {
  const qc = useQueryClient()
  const [selected, setSelected] = useState(DEFAULT_KEYS[0].key)
  const [editValue, setEditValue] = useState('')
  const [preview, setPreview] = useState(false)
  const [toast, setToast] = useState(null)
  const [newKey, setNewKey] = useState('')
  const [showNewKey, setShowNewKey] = useState(false)

  const { data: texts = {}, isLoading } = useQuery({
    queryKey: ['bot-texts'],
    queryFn: () => api.get('/admin/bot-texts').then(r => r.data),
    staleTime: 10000,
  })

  const saveMutation = useMutation({
    mutationFn: ({ key, value }) => api.put(`/admin/bot-texts/${key}`, { value }),
    onSuccess: () => {
      qc.invalidateQueries(['bot-texts'])
      setToast({ type: 'success', message: 'Текст сохранён и применён без перезагрузки бота!' })
    },
    onError: () => setToast({ type: 'error', message: 'Ошибка при сохранении' }),
  })

  const deleteMutation = useMutation({
    mutationFn: (key) => api.delete(`/admin/bot-texts/${key}`),
    onSuccess: () => {
      qc.invalidateQueries(['bot-texts'])
      setToast({ type: 'success', message: 'Текст удалён' })
    },
  })

  useEffect(() => {
    if (texts[selected] !== undefined) {
      setEditValue(texts[selected])
    }
  }, [selected, texts])

  const allKeys = [
    ...DEFAULT_KEYS,
    ...Object.keys(texts)
      .filter(k => !DEFAULT_KEYS.find(d => d.key === k))
      .map(k => ({ key: k, label: k })),
  ]

  function renderHtml(text) {
    return text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
      .replace(/<b>(.*?)<\/b>/g, '<b>$1</b>')
      .replace(/<i>(.*?)<\/i>/g, '<i>$1</i>')
      .replace(/<code>(.*?)<\/code>/g, '<code class="bg-gray-100 px-1 rounded">$1</code>')
      .replace(/\n/g, '<br/>')
  }

  return (
    <div className="flex h-full gap-4">
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      {/* Sidebar */}
      <div className="w-72 flex-shrink-0 bg-white rounded-xl shadow-sm border border-gray-100 overflow-y-auto">
        <div className="p-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="font-semibold text-gray-800">Тексты бота</h3>
          <button
            onClick={() => setShowNewKey(true)}
            className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-600"
            title="Добавить текст"
          ><Plus size={16} /></button>
        </div>

        {showNewKey && (
          <div className="p-3 border-b border-gray-100 bg-blue-50">
            <input
              className="w-full border rounded px-2 py-1 text-sm mb-2"
              placeholder="Ключ (напр. my_text)"
              value={newKey}
              onChange={e => setNewKey(e.target.value)}
            />
            <div className="flex gap-2">
              <button
                onClick={() => { if (newKey) { setSelected(newKey); setEditValue(''); setShowNewKey(false); setNewKey('') } }}
                className="flex-1 bg-blue-600 text-white text-xs py-1 rounded"
              >Создать</button>
              <button onClick={() => setShowNewKey(false)} className="flex-1 border text-xs py-1 rounded">Отмена</button>
            </div>
          </div>
        )}

        <div className="divide-y divide-gray-50">
          {allKeys.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setSelected(key)}
              className={`w-full text-left px-4 py-3 text-sm hover:bg-gray-50 transition-colors ${
                selected === key ? 'bg-blue-50 text-blue-700 font-medium border-r-2 border-blue-600' : 'text-gray-700'
              }`}
            >
              <div className="font-medium">{label}</div>
              <div className="text-xs text-gray-400 font-mono">{key}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col">
        <div className="p-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-800">
              {allKeys.find(k => k.key === selected)?.label || selected}
            </h3>
            <code className="text-xs text-gray-400">{selected}</code>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setPreview(p => !p)}
              className="flex items-center gap-2 px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50"
            >
              {preview ? <EyeOff size={14} /> : <Eye size={14} />}
              {preview ? 'Редактор' : 'Превью'}
            </button>
            <button
              onClick={() => saveMutation.mutate({ key: selected, value: editValue })}
              disabled={saveMutation.isPending}
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saveMutation.isPending ? <RefreshCw size={14} className="animate-spin" /> : <Save size={14} />}
              Сохранить
            </button>
            <button
              onClick={() => deleteMutation.mutate(selected)}
              className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg"
              title="Удалить"
            ><Trash2 size={16} /></button>
          </div>
        </div>

        <div className="flex-1 p-4">
          {preview ? (
            <div className="h-full bg-gray-50 rounded-lg p-4 overflow-y-auto">
              <div className="text-xs text-gray-400 mb-3 font-medium uppercase tracking-wide">Превью (Telegram HTML)</div>
              <div
                className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap"
                dangerouslySetInnerHTML={{ __html: renderHtml(editValue) }}
              />
            </div>
          ) : (
            <div className="h-full flex flex-col gap-2">
              <div className="text-xs text-gray-400">
                Поддерживаются HTML-теги: &lt;b&gt;жирный&lt;/b&gt;, &lt;i&gt;курсив&lt;/i&gt;, &lt;code&gt;код&lt;/code&gt;, \n — перенос строки
              </div>
              <textarea
                className="flex-1 border border-gray-200 rounded-lg p-3 text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={editValue}
                onChange={e => setEditValue(e.target.value)}
                placeholder="Введите текст..."
              />
            </div>
          )}
        </div>

        <div className="p-3 border-t border-gray-100 bg-green-50 rounded-b-xl">
          <p className="text-xs text-green-700">
            ✅ Изменения применяются <strong>мгновенно</strong> без перезагрузки бота — бот читает тексты из БД при каждом ответе.
          </p>
        </div>
      </div>
    </div>
  )
}
