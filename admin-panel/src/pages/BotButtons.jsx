import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, Save, RefreshCw, Image, X } from 'lucide-react'
import api from '../api/client'
import Toast from '../components/Toast'

async function uploadImageFile(file) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await api.post('/admin/upload-image', fd, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  let imageUrl = res.data.url
  if (imageUrl && imageUrl.startsWith('/')) {
    const apiBase = import.meta.env.VITE_API_URL || ''
    const origin = apiBase.replace('/api/v1', '').replace('/api', '')
    imageUrl = origin + imageUrl
  }
  return imageUrl
}

/**
 * Редактор кнопок главного меню бота.
 * Позволяет добавлять, удалять, переименовывать кнопки без перезагрузки бота.
 */
export default function BotButtons() {
  const qc = useQueryClient()
  const [toast, setToast] = useState(null)
  const [newBtn, setNewBtn] = useState({ text: '', callback_data: '', url: '', row: 0, image_url: '' })
  const [showAdd, setShowAdd] = useState(false)
  const [uploadingNew, setUploadingNew] = useState(false)

  async function handleNewBtnImage(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadingNew(true)
    try {
      const url = await uploadImageFile(file)
      setNewBtn(b => ({ ...b, image_url: url }))
      setToast({ type: 'success', message: 'Изображение загружено!' })
    } catch {
      setToast({ type: 'error', message: 'Ошибка загрузки изображения' })
    } finally { setUploadingNew(false) }
  }

  const { data: buttons = [], isLoading } = useQuery({
    queryKey: ['bot-buttons'],
    queryFn: () => api.get('/admin/bot-buttons').then(r => r.data?.buttons || []),
    staleTime: 5000,
  })

  const saveMutation = useMutation({
    mutationFn: (btn) => api.put(`/admin/bot-buttons/${btn.id}`, btn),
    onSuccess: () => { qc.invalidateQueries(['bot-buttons']); setToast({ type: 'success', message: 'Кнопка обновлена!' }) },
    onError: () => setToast({ type: 'error', message: 'Ошибка сохранения' }),
  })

  const addMutation = useMutation({
    mutationFn: (btn) => api.post('/admin/bot-buttons', btn),
    onSuccess: () => {
      qc.invalidateQueries(['bot-buttons'])
      setToast({ type: 'success', message: 'Кнопка добавлена!' })
      setShowAdd(false)
      setNewBtn({ text: '', callback_data: '', url: '', row: 0 })
    },
    onError: () => setToast({ type: 'error', message: 'Ошибка при добавлении' }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => api.delete(`/admin/bot-buttons/${id}`),
    onSuccess: () => { qc.invalidateQueries(['bot-buttons']); setToast({ type: 'success', message: 'Кнопка удалена' }) },
  })

  const reorderMutation = useMutation({
    mutationFn: (ids) => api.post('/admin/bot-buttons/reorder', { ids }),
    onSuccess: () => qc.invalidateQueries(['bot-buttons']),
  })

  // Сгруппировать кнопки по рядам
  const rows = buttons.reduce((acc, btn) => {
    const r = btn.row ?? 0
    if (!acc[r]) acc[r] = []
    acc[r].push(btn)
    return acc
  }, {})

  const maxRow = Math.max(0, ...buttons.map(b => b.row ?? 0))

  return (
    <div className="space-y-6">
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-800">Кнопки главного меню бота</h2>
            <p className="text-sm text-gray-500 mt-1">
              Изменения применяются мгновенно — бот получает кнопки из БД.
            </p>
          </div>
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
          >
            <Plus size={16} /> Добавить кнопку
          </button>
        </div>

        {/* Превью меню — как в Telegram */}
        <div style={{ backgroundColor: '#17212b' }} className="rounded-xl p-4">
          <div className="text-xs text-gray-400 font-medium mb-3 uppercase tracking-wide">Превью (как в Telegram)</div>
          {/* Имитация сообщения бота */}
          <div className="flex mb-3">
            <div style={{ backgroundColor: '#2b5278' }} className="text-white text-sm rounded-2xl rounded-tl-sm px-3 py-2 max-w-xs">
              Выберите действие:
            </div>
          </div>
          {/* Кнопки */}
          <div className="space-y-1.5">
            {Object.entries(rows).sort(([a], [b]) => Number(a) - Number(b)).map(([row, btns]) => (
              <div key={row} className="flex gap-1.5">
                {btns.map(btn => (
                  <button
                    key={btn.id}
                    style={{ backgroundColor: '#2b5278' }}
                    className="flex-1 text-white text-sm rounded-lg px-3 py-2 text-center transition-colors hover:opacity-90"
                  >
                    {btn.text}
                  </button>
                ))}
              </div>
            ))}
          </div>
          {buttons.length === 0 && (
            <p className="text-gray-500 text-sm text-center py-2">Нет кнопок</p>
          )}
        </div>
      </div>

      {/* Список кнопок */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-4 border-b border-gray-100">
          <h3 className="font-semibold text-gray-700">Все кнопки ({buttons.length})</h3>
        </div>
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Загрузка...</div>
        ) : buttons.length === 0 ? (
          <div className="p-8 text-center text-gray-400">Кнопок нет. Нажмите «Добавить кнопку»</div>
        ) : (
          <div className="divide-y divide-gray-50">
            {buttons.map((btn, idx) => (
              <ButtonRow
                key={btn.id}
                btn={btn}
                maxRow={maxRow}
                onSave={saveMutation.mutate}
                onDelete={() => deleteMutation.mutate(btn.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Форма добавления */}
      {showAdd && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h3 className="font-semibold text-gray-800 mb-4">Добавить кнопку</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Текст кнопки *</label>
              <input
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="🎁 Бесплатный доступ"
                value={newBtn.text}
                onChange={e => setNewBtn(b => ({ ...b, text: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Callback data</label>
              <input
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="free_trial"
                value={newBtn.callback_data}
                onChange={e => setNewBtn(b => ({ ...b, callback_data: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">URL (если кнопка-ссылка)</label>
              <input
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="https://..."
                value={newBtn.url}
                onChange={e => setNewBtn(b => ({ ...b, url: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Ряд (0 = первый)</label>
              <input
                type="number"
                min="0"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={newBtn.row}
                onChange={e => setNewBtn(b => ({ ...b, row: Number(e.target.value) }))}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm text-gray-600 mb-1">Изображение кнопки <span className="text-gray-400">(опционально — отправляется при нажатии)</span></label>
              {newBtn.image_url ? (
                <div className="flex items-center gap-3">
                  <img src={newBtn.image_url} alt="" className="h-16 w-16 object-cover rounded-lg border" />
                  <button onClick={() => setNewBtn(b => ({ ...b, image_url: '' }))} className="text-red-400 hover:text-red-600 flex items-center gap-1 text-sm">
                    <X size={14} /> Удалить
                  </button>
                </div>
              ) : (
                <label className={`flex items-center gap-2 cursor-pointer text-sm border-2 border-dashed border-gray-200 rounded-lg p-3 hover:border-blue-400 hover:bg-blue-50 transition-colors ${uploadingNew ? 'opacity-50 pointer-events-none' : ''}`}>
                  {uploadingNew ? <RefreshCw size={16} className="animate-spin text-blue-500" /> : <Image size={16} className="text-gray-400" />}
                  <span className="text-gray-500">{uploadingNew ? 'Загрузка...' : 'Нажмите чтобы загрузить изображение (JPG, PNG до 5МБ)'}</span>
                  <input type="file" accept="image/*" className="hidden" onChange={handleNewBtnImage} disabled={uploadingNew} />
                </label>
              )}
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button
              onClick={() => addMutation.mutate(newBtn)}
              disabled={!newBtn.text || addMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm disabled:opacity-50"
            >
              {addMutation.isPending ? <RefreshCw size={14} className="animate-spin" /> : <Plus size={14} />}
              Добавить
            </button>
            <button onClick={() => setShowAdd(false)} className="px-4 py-2 border rounded-lg text-sm">Отмена</button>
          </div>
        </div>
      )}
    </div>
  )
}

function ButtonRow({ btn, maxRow, onSave, onDelete }) {
  const [editing, setEditing] = useState(false)
  const [local, setLocal] = useState(btn)
  const [uploadingImg, setUploadingImg] = useState(false)
  const [imgError, setImgError] = useState(null)

  const handleSave = () => {
    onSave({ ...local, id: btn.id })
    setEditing(false)
  }

  async function handleImageUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadingImg(true)
    setImgError(null)
    try {
      const url = await uploadImageFile(file)
      setLocal(l => ({ ...l, image_url: url }))
    } catch {
      setImgError('Ошибка загрузки изображения')
    } finally { setUploadingImg(false) }
  }

  return (
    <div className="p-4 hover:bg-gray-50 transition-colors">
      {editing ? (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Текст</label>
            <input
              className="w-full border rounded px-2 py-1 text-sm"
              value={local.text}
              onChange={e => setLocal(l => ({ ...l, text: e.target.value }))}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Callback / URL</label>
            <input
              className="w-full border rounded px-2 py-1 text-sm font-mono"
              value={local.callback_data || local.url || ''}
              onChange={e => setLocal(l => ({ ...l, callback_data: e.target.value }))}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Ряд</label>
            <input
              type="number" min="0"
              className="w-24 border rounded px-2 py-1 text-sm"
              value={local.row ?? 0}
              onChange={e => setLocal(l => ({ ...l, row: Number(e.target.value) }))}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Изображение</label>
            {local.image_url ? (
              <div className="flex items-center gap-2">
                <img src={local.image_url} alt="" className="h-10 w-10 object-cover rounded border" />
                <button onClick={() => setLocal(l => ({ ...l, image_url: '' }))} className="text-red-400 text-xs flex items-center gap-1">
                  <X size={12} /> Удалить
                </button>
              </div>
            ) : (
              <label className={`flex items-center gap-1 cursor-pointer text-xs border border-dashed border-gray-300 rounded px-2 py-1.5 hover:border-blue-400 ${uploadingImg ? 'opacity-50' : ''}`}>
                {uploadingImg ? <RefreshCw size={12} className="animate-spin" /> : <Image size={12} />}
                <span>{uploadingImg ? 'Загрузка...' : 'Загрузить'}</span>
                <input type="file" accept="image/*" className="hidden" onChange={handleImageUpload} disabled={uploadingImg} />
              </label>
            )}
            {imgError && <p className="text-red-500 text-xs mt-1">{imgError}</p>}
          </div>
          <div className="col-span-2 flex items-center gap-2">
            <button onClick={handleSave} className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white rounded text-sm">
              <Save size={13} /> Сохранить
            </button>
            <button onClick={() => setEditing(false)} className="px-3 py-1.5 border rounded text-sm">Отмена</button>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {btn.image_url && (
              <img src={btn.image_url} alt="" className="h-8 w-8 object-cover rounded border flex-shrink-0" />
            )}
            <span className="bg-gray-100 text-gray-500 text-xs px-2 py-0.5 rounded font-mono">
              ряд {btn.row ?? 0}
            </span>
            <span className="font-medium text-gray-800">{btn.text}</span>
            <span className="text-xs text-gray-400 font-mono">{btn.callback_data || btn.url}</span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setEditing(true)} className="text-xs px-2 py-1 border rounded hover:bg-gray-50">
              Изменить
            </button>
            <button onClick={onDelete} className="p-1.5 text-red-400 hover:bg-red-50 rounded">
              <Trash2 size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
