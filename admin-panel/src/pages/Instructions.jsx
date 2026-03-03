import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Save, RefreshCw, Plus, Trash2, Image, Link } from 'lucide-react'
import api from '../api/client'
import Toast from '../components/Toast'

export default function Instructions() {
  const qc = useQueryClient()
  const [toast, setToast] = useState(null)
  const [activeDevice, setActiveDevice] = useState('android')
  const [steps, setSteps] = useState([{ step: 1, text: '', image_url: '', buttons: [] }])
  const [uploading, setUploading] = useState(null)

  const devices = ['android', 'ios', 'windows', 'macos', 'linux', 'android_tv']
  const deviceLabels = {
    android: '🤖 Android', ios: '🍎 iOS', windows: '🪟 Windows',
    macos: '🍎 macOS', linux: '🐧 Linux', android_tv: '📺 Android TV',
  }

  const { data: botTexts = {}, isLoading } = useQuery({
    queryKey: ['bot-texts'],
    queryFn: () => api.get('/admin/bot-texts').then(r => r.data ?? {}),
    staleTime: 10000,
  })

  useEffect(() => {
    const key = `instructions_${activeDevice}_steps`
    const raw = botTexts[key]
    if (raw) {
      try { setSteps(JSON.parse(raw)) } catch { setSteps([{ step: 1, text: '', image_url: '', buttons: [] }]) }
    } else {
      // Try legacy text format
      const legacyKey = `instructions_${activeDevice}`
      const legacy = botTexts[legacyKey]
      if (legacy) setSteps([{ step: 1, text: legacy, image_url: '', buttons: [] }])
      else setSteps([{ step: 1, text: '', image_url: '', buttons: [] }])
    }
  }, [activeDevice, botTexts])

  const saveMutation = useMutation({
    mutationFn: (stepsData) => api.put(`/admin/bot-texts/instructions_${activeDevice}_steps`, { value: JSON.stringify(stepsData) }),
    onSuccess: () => { qc.invalidateQueries(['bot-texts']); setToast({ type: 'success', message: 'Инструкция сохранена!' }) },
    onError: () => setToast({ type: 'error', message: 'Ошибка сохранения' }),
  })

  async function uploadImage(file, stepIdx) {
    setUploading(stepIdx)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await api.post('/admin/upload-image', fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      // Используем полный URL если вернулся, иначе строим из VITE_API_URL
      let imageUrl = res.data.url
      if (imageUrl && imageUrl.startsWith('/')) {
        const apiBase = import.meta.env.VITE_API_URL || ''
        const origin = apiBase.replace('/api/v1', '').replace('/api', '')
        imageUrl = origin + imageUrl
      }
      setSteps(s => s.map((st, i) => i === stepIdx ? { ...st, image_url: imageUrl } : st))
      setToast({ type: 'success', message: 'Изображение загружено!' })
    } catch (e) {
      console.error('Upload error:', e)
      setToast({ type: 'error', message: 'Ошибка загрузки изображения. Проверьте формат файла (JPG, PNG, GIF, WebP до 5МБ).' })
    } finally { setUploading(null) }
  }

  function addStep() {
    setSteps(s => [...s, { step: s.length + 1, text: '', image_url: '', buttons: [] }])
  }

  function removeStep(idx) {
    setSteps(s => s.filter((_, i) => i !== idx).map((st, i) => ({ ...st, step: i + 1 })))
  }

  function updateStep(idx, key, val) {
    setSteps(s => s.map((st, i) => i === idx ? { ...st, [key]: val } : st))
  }

  function addButton(stepIdx) {
    setSteps(s => s.map((st, i) => i === stepIdx
      ? { ...st, buttons: [...(st.buttons || []), { text: '', url: '' }] }
      : st
    ))
  }

  function updateButton(stepIdx, btnIdx, key, val) {
    setSteps(s => s.map((st, i) => i === stepIdx
      ? { ...st, buttons: (st.buttons || []).map((b, j) => j === btnIdx ? { ...b, [key]: val } : b) }
      : st
    ))
  }

  function removeButton(stepIdx, btnIdx) {
    setSteps(s => s.map((st, i) => i === stepIdx
      ? { ...st, buttons: (st.buttons || []).filter((_, j) => j !== btnIdx) }
      : st
    ))
  }

  if (isLoading) return <div className="text-center py-10 text-gray-400">Загрузка...</div>

  return (
    <div className="space-y-4">
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
      <div>
        <h1 className="text-3xl font-bold text-gray-800 mb-1">Инструкции для пользователей</h1>
        <p className="text-gray-500">Пошаговые инструкции с изображениями для каждого устройства</p>
      </div>

      <div className="flex gap-2 overflow-x-auto flex-wrap">
        {devices.map(device => (
          <button key={device} onClick={() => setActiveDevice(device)}
            className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
              activeDevice === device ? 'bg-blue-600 text-white shadow' : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}>{deviceLabels[device]}</button>
        ))}
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Шаги для {deviceLabels[activeDevice]}</h2>
          <button onClick={addStep} className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
            <Plus size={14} /> Добавить шаг
          </button>
        </div>

        {steps.map((step, idx) => (
          <div key={idx} className="border border-gray-200 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-medium text-gray-700">Шаг {step.step}</span>
              {steps.length > 1 && (
                <button onClick={() => removeStep(idx)} className="text-red-400 hover:text-red-600 p-1"><Trash2 size={14} /></button>
              )}
            </div>
            <textarea
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm h-24 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder={`Текст шага ${step.step}...`}
              value={step.text}
              onChange={e => updateStep(idx, 'text', e.target.value)}
            />
            {step.image_url ? (
              <div className="relative inline-block">
                <img src={step.image_url} alt="" className="max-h-32 rounded-lg border object-contain" />
                <button onClick={() => updateStep(idx, 'image_url', '')} className="absolute top-1 right-1 bg-red-500 text-white rounded-full p-0.5 text-xs">✕</button>
              </div>
            ) : (
              <label className="flex items-center gap-2 cursor-pointer text-sm text-blue-600 hover:text-blue-800">
                <Image size={16} /> Добавить изображение к шагу
                <input type="file" accept="image/*" className="hidden"
                  onChange={e => e.target.files?.[0] && uploadImage(e.target.files[0], idx)}
                  disabled={uploading === idx} />
              </label>
            )}
            {uploading === idx && <div className="text-sm text-blue-600 flex items-center gap-2"><RefreshCw size={12} className="animate-spin" /> Загрузка...</div>}

            {/* Кнопки-ссылки для шага */}
            <div className="border-t border-gray-100 pt-3 mt-1">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">🔗 Кнопки-ссылки</span>
                <button
                  onClick={() => addButton(idx)}
                  className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 border border-blue-200 rounded px-2 py-0.5"
                >
                  <Plus size={11} /> Добавить кнопку
                </button>
              </div>
              {(step.buttons || []).length === 0 && (
                <p className="text-xs text-gray-400 italic">Нет кнопок. Нажмите «Добавить кнопку».</p>
              )}
              {(step.buttons || []).map((btn, btnIdx) => (
                <div key={btnIdx} className="flex gap-2 mb-2 items-center">
                  <input
                    className="flex-1 border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                    placeholder="Текст кнопки (напр. Скачать для Android)"
                    value={btn.text}
                    onChange={e => updateButton(idx, btnIdx, 'text', e.target.value)}
                  />
                  <input
                    className="flex-1 border border-gray-200 rounded px-2 py-1 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-blue-400"
                    placeholder="URL (https://...)"
                    value={btn.url}
                    onChange={e => updateButton(idx, btnIdx, 'url', e.target.value)}
                  />
                  <button
                    onClick={() => removeButton(idx, btnIdx)}
                    className="text-red-400 hover:text-red-600 p-1 flex-shrink-0"
                    title="Удалить кнопку"
                  ><Trash2 size={13} /></button>
                </div>
              ))}
            </div>
          </div>
        ))}

        <div className="pt-4 border-t border-gray-100 flex justify-end">
          <button onClick={() => saveMutation.mutate(steps)} disabled={saveMutation.isPending}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium">
            {saveMutation.isPending ? <RefreshCw size={16} className="animate-spin" /> : <Save size={16} />}
            Сохранить инструкцию
          </button>
        </div>
      </div>
    </div>
  )
}
