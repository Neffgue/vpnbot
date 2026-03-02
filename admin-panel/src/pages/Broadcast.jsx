import { useState, useRef } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Send, RefreshCw, CheckCircle, Image, X } from 'lucide-react'
import api from '../api/client'
import Toast from '../components/Toast'

/**
 * Страница рассылки — отправка сообщений всем или выбранным пользователям.
 * Поддерживает текст (HTML) и опциональное изображение.
 */
export default function Broadcast() {
  const [message, setMessage] = useState('')
  const [target, setTarget] = useState('all') // all | active | trial | expired
  const [preview, setPreview] = useState(false)
  const [toast, setToast] = useState(null)
  const [result, setResult] = useState(null)
  const [image, setImage] = useState(null)       // File объект
  const [imagePreview, setImagePreview] = useState(null) // base64 для предпросмотра
  const fileRef = useRef(null)

  const broadcastMutation = useMutation({
    mutationFn: async () => {
      if (image) {
        // Отправляем как multipart/form-data с картинкой на отдельный endpoint
        const fd = new FormData()
        if (message) fd.append('message', message)
        fd.append('target', target)
        fd.append('image', image)
        return api.post('/admin/broadcast-image', fd, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
      }
      return api.post('/admin/broadcasts', { message, target })
    },
    onSuccess: (res) => {
      setResult(res.data)
      setToast({ type: 'success', message: `Рассылка запущена! Получателей: ${res.data?.sent_count ?? 0}` })
      setMessage('')
      setImage(null)
      setImagePreview(null)
    },
    onError: (err) => {
      const detail = err?.response?.data?.detail || 'Ошибка при отправке рассылки'
      setToast({ type: 'error', message: detail })
    },
  })

  function handleImageChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setToast({ type: 'error', message: 'Выберите файл изображения (jpg, png, gif, webp)' })
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      setToast({ type: 'error', message: 'Файл слишком большой. Максимум 10 МБ.' })
      return
    }
    setImage(file)
    const reader = new FileReader()
    reader.onload = () => setImagePreview(reader.result)
    reader.readAsDataURL(file)
  }

  function removeImage() {
    setImage(null)
    setImagePreview(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  function renderHtml(text) {
    return (text || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/&lt;b&gt;(.*?)&lt;\/b&gt;/g, '<b>$1</b>')
      .replace(/&lt;i&gt;(.*?)&lt;\/i&gt;/g, '<i>$1</i>')
      .replace(/&lt;code&gt;(.*?)&lt;\/code&gt;/g, '<code class="bg-gray-100 px-1 rounded text-sm">$1</code>')
      .replace(/&lt;a href="(.*?)"&gt;(.*?)&lt;\/a&gt;/g, '<a href="$1" class="text-blue-600 underline">$2</a>')
      .replace(/\n/g, '<br/>')
  }

  return (
    <div className="max-w-3xl space-y-6">
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      {/* Форма рассылки */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center">
            <Send size={20} className="text-blue-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-800">Рассылка</h2>
            <p className="text-sm text-gray-500">Отправка сообщений пользователям Telegram</p>
          </div>
        </div>

        {/* Аудитория */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-gray-700 mb-2">Аудитория</label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {[
              { value: 'all', label: '👥 Все пользователи' },
              { value: 'active', label: '✅ Активная подписка' },
              { value: 'trial', label: '🎁 Пробный период' },
              { value: 'expired', label: '⏰ Истекшая подписка' },
            ].map(opt => (
              <label
                key={opt.value}
                className={`flex items-center gap-2 cursor-pointer border rounded-lg px-3 py-2 text-sm transition-colors ${
                  target === opt.value
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 text-gray-700 hover:bg-gray-50'
                }`}
              >
                <input
                  type="radio"
                  name="target"
                  value={opt.value}
                  checked={target === opt.value}
                  onChange={() => setTarget(opt.value)}
                  className="accent-blue-600 hidden"
                />
                {opt.label}
              </label>
            ))}
          </div>
        </div>

        {/* Загрузка изображения */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Изображение <span className="text-gray-400 font-normal">(опционально)</span>
          </label>
          {imagePreview ? (
            <div className="relative inline-block">
              <img
                src={imagePreview}
                alt="preview"
                className="max-h-48 rounded-lg border border-gray-200 object-contain"
              />
              <button
                onClick={removeImage}
                className="absolute top-1 right-1 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
              >
                <X size={12} />
              </button>
              <div className="text-xs text-gray-400 mt-1">{image?.name} ({(image?.size / 1024).toFixed(0)} КБ)</div>
            </div>
          ) : (
            <div
              onClick={() => fileRef.current?.click()}
              className="border-2 border-dashed border-gray-200 rounded-lg p-6 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors"
            >
              <Image size={24} className="mx-auto text-gray-300 mb-2" />
              <p className="text-sm text-gray-500">Нажмите чтобы выбрать изображение</p>
              <p className="text-xs text-gray-400 mt-1">JPG, PNG, GIF, WebP — до 10 МБ</p>
            </div>
          )}
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleImageChange}
          />
        </div>

        {/* Текст сообщения */}
        <div className="mb-5">
          <div className="flex justify-between items-center mb-2">
            <label className="block text-sm font-medium text-gray-700">Текст сообщения</label>
            <button
              onClick={() => setPreview(p => !p)}
              className="text-xs text-blue-600 hover:underline"
            >{preview ? '✏️ Редактор' : '👁 Превью'}</button>
          </div>

          {preview ? (
            /* Превью в стиле Telegram */
            <div style={{ background: '#17212b' }} className="min-h-40 rounded-xl p-4">
              <div className="text-xs text-gray-500 mb-3 font-medium uppercase tracking-wide">Превью — как видит пользователь в Telegram</div>
              <div className="flex justify-start">
                <div style={{ background: '#182533', maxWidth: '85%' }} className="rounded-2xl rounded-tl-sm px-4 py-2.5 shadow-md">
                  {imagePreview && (
                    <img src={imagePreview} alt="preview" className="max-h-48 rounded-lg mb-2 object-contain w-full" />
                  )}
                  <div
                    style={{ color: '#e8e8e8', fontSize: '14px', lineHeight: '1.5' }}
                    dangerouslySetInnerHTML={{ __html: renderHtml(message) }}
                  />
                  <div style={{ color: '#7b8e9e', fontSize: '11px' }} className="text-right mt-1">
                    {new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })} ✓✓
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <textarea
              className="w-full h-40 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 font-mono resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Текст сообщения...&#10;&#10;HTML-теги Telegram: <b>жирный</b>, <i>курсив</i>, <code>код</code>"
              value={message}
              onChange={e => setMessage(e.target.value)}
            />
          )}
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>Теги: &lt;b&gt; &lt;i&gt; &lt;code&gt; &lt;a href=""&gt;</span>
            <span>{message.length} символов</span>
          </div>
        </div>

        <button
          onClick={() => broadcastMutation.mutate()}
          disabled={(!message.trim() && !image) || broadcastMutation.isPending}
          className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium transition-colors"
        >
          {broadcastMutation.isPending ? (
            <><RefreshCw size={16} className="animate-spin" /> Отправка...</>
          ) : (
            <><Send size={16} /> Отправить рассылку</>
          )}
        </button>
      </div>

      {/* Результат */}
      {result && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <CheckCircle size={20} className="text-green-600" />
            <h3 className="font-semibold text-green-800">Рассылка выполнена</h3>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white rounded-lg p-3 text-center border border-green-100">
              <div className="text-2xl font-bold text-green-600">{result.sent_count ?? 0}</div>
              <div className="text-xs text-gray-500 mt-1">Отправлено</div>
            </div>
            <div className="bg-white rounded-lg p-3 text-center border border-green-100">
              <div className="text-2xl font-bold text-blue-600">{result.success_count ?? result.sent_count ?? 0}</div>
              <div className="text-xs text-gray-500 mt-1">Успешно</div>
            </div>
            <div className="bg-white rounded-lg p-3 text-center border border-green-100">
              <div className="text-2xl font-bold text-red-500">{result.failed_count ?? 0}</div>
              <div className="text-xs text-gray-500 mt-1">Ошибок</div>
            </div>
          </div>
        </div>
      )}

      {/* Подсказка */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
        <h4 className="font-medium text-amber-800 mb-2">⚠️ Важно</h4>
        <ul className="text-sm text-amber-700 space-y-1">
          <li>• Проверьте текст через «Превью» перед отправкой</li>
          <li>• Рассылка идёт через Telegram — может занять несколько минут</li>
          <li>• Пользователи, заблокировавшие бота, не получат сообщение</li>
          <li>• При отправке с картинкой текст будет подписью к фото</li>
        </ul>
      </div>
    </div>
  )
}
