import React, { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Save, RefreshCw, Plus, Trash2 } from 'lucide-react'
import api from '../api/client'
import Toast from '../components/Toast'

const PERIOD_LABELS = {
  7: '7 дней',
  30: '30 дней',
  90: '90 дней',
  180: '180 дней',
  365: '365 дней',
}

export default function PlanPrices() {
  const qc = useQueryClient()
  const [toast, setToast] = useState(null)

  // Загружаем список планов из бэкенда (GET /admin/plans → [{id, plan_name, period_days, price_rub}])
  const { data: rawPlans = [], isLoading, refetch } = useQuery({
    queryKey: ['plan-prices'],
    queryFn: () => api.get('/admin/plans').then(r => Array.isArray(r.data) ? r.data : []),
    staleTime: 0,
    refetchOnWindowFocus: true,
  })

  // Локальное состояние для редактирования
  const [rows, setRows] = useState([])
  const [newRow, setNewRow] = useState({ plan_name: 'Solo', period_days: 30, price_rub: 299, name: '', device_limit: 1 })
  const [showAdd, setShowAdd] = useState(false)

  useEffect(() => {
    // Всегда синхронизируем rows с сервером (даже если список пустой — очищаем таблицу)
    setRows(rawPlans.map(p => ({
      id: p.id,
      plan_name: p.plan_name,
      period_days: p.period_days,
      price_rub: parseFloat(p.price_rub),
      name: p.name || '',
      device_limit: p.device_limit || 1,
      description: p.description || '',
      is_active: p.is_active !== false,
      _dirty: false,
    })))
  }, [rawPlans])

  const saveMutation = useMutation({
    mutationFn: async (row) => {
      if (row.id) {
        return api.put(`/admin/plans/${row.id}`, {
          plan_name: row.plan_name,
          period_days: row.period_days,
          price_rub: row.price_rub,
          name: row.name || null,
          device_limit: row.device_limit || 1,
          description: row.description || null,
          is_active: row.is_active !== false,
        })
      } else {
        return api.post('/admin/plans', {
          plan_name: row.plan_name,
          period_days: row.period_days,
          price_rub: row.price_rub,
          name: row.name || null,
          device_limit: row.device_limit || 1,
          description: row.description || null,
          is_active: row.is_active !== false,
        })
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['plan-prices'] })
      setToast({ type: 'success', message: 'Цена сохранена!' })
    },
    onError: (err) => {
      const status = err?.response?.status
      const msg = err?.response?.data?.detail || 'Ошибка сохранения'
      if (status === 404) {
        // ID устарел — обновляем список и сбрасываем dirty флаги
        refetch()
        setRows(r => r.map(row => ({ ...row, _dirty: false })))
        setToast({ type: 'error', message: 'Тариф не найден в БД. Список обновлён — попробуйте снова.' })
      } else {
        setToast({ type: 'error', message: `Ошибка ${status || ''}: ${msg}` })
      }
    },
  })

  const saveAllMutation = useMutation({
    mutationFn: async () => {
      const dirty = rows.filter(r => r._dirty)
      for (const row of dirty) {
        if (row.id) {
          await api.put(`/admin/plans/${row.id}`, {
            plan_name: row.plan_name,
            period_days: row.period_days,
            price_rub: row.price_rub,
            name: row.name || null,
            device_limit: row.device_limit || 1,
            description: row.description || null,
            is_active: row.is_active !== false,
          })
        }
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['plan-prices'] })
      setToast({ type: 'success', message: 'Все цены сохранены!' })
      setRows(r => r.map(row => ({ ...row, _dirty: false })))
    },
    onError: (err) => {
      const status = err?.response?.status
      const msg = err?.response?.data?.detail || 'Ошибка сохранения'
      if (status === 404) {
        refetch()
        setRows(r => r.map(row => ({ ...row, _dirty: false })))
        setToast({ type: 'error', message: 'Некоторые тарифы не найдены в БД. Список обновлён — попробуйте снова.' })
      } else {
        setToast({ type: 'error', message: `Ошибка ${status || ''}: ${msg}` })
      }
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => api.delete(`/admin/plans/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['plan-prices'] })
      setToast({ type: 'success', message: 'Тариф удалён' })
    },
    onError: (err) => {
      const status = err?.response?.status
      if (status === 404) {
        // Запись уже удалена или список устарел
        qc.invalidateQueries({ queryKey: ['plan-prices'] })
        setToast({ type: 'error', message: 'Тариф уже удалён или не найден. Список обновлён.' })
      } else {
        const msg = err?.response?.data?.detail || 'Ошибка удаления'
        setToast({ type: 'error', message: `Ошибка ${status || ''}: ${msg}` })
      }
    },
  })

  const addMutation = useMutation({
    mutationFn: () => api.post('/admin/plans', {
      ...newRow,
      name: newRow.name || null,
      device_limit: newRow.device_limit || 1,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['plan-prices'] })
      setToast({ type: 'success', message: 'Цена добавлена!' })
      setShowAdd(false)
      setNewRow({ plan_name: 'solo', period_days: 30, price_rub: 299, name: '', device_limit: 1, description: '', is_active: true })
    },
    onError: () => setToast({ type: 'error', message: 'Ошибка добавления' }),
  })

  function updateRow(idx, field, val) {
    setRows(prev => prev.map((r, i) => i === idx ? { ...r, [field]: val, _dirty: true } : r))
  }

  // Группируем по план-имени для отображения в таблице
  const planNames = [...new Set(rows.map(r => r.plan_name))]

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Цены тарифов</h1>
          <p className="text-gray-500 text-sm mt-1">Управляйте ценами планов подписки</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm"
          >
            <Plus size={16} /> Добавить
          </button>
          <button
            onClick={() => saveAllMutation.mutate()}
            disabled={saveAllMutation.isPending || !rows.some(r => r._dirty)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm disabled:opacity-50"
          >
            {saveAllMutation.isPending ? <RefreshCw size={16} className="animate-spin" /> : <Save size={16} />}
            Сохранить все
          </button>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-10 text-center">
          <p className="text-gray-400 mb-4">Планов нет. Добавьте первый тариф.</p>
          <button
            onClick={() => setShowAdd(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm"
          >Добавить тариф</button>
        </div>
      ) : (
        planNames.map(planName => {
          const planRows = rows.filter(r => r.plan_name === planName)
          return (
            <div key={planName} className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
                <h3 className="font-semibold text-gray-800">📦 {planName}</h3>
              </div>
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Период</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Название</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Цена (₽)</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Устройств</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Активен</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Действия</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {planRows.sort((a, b) => a.period_days - b.period_days).map((row) => {
                    const idx = rows.findIndex(r => r === row)
                    return (
                      <tr key={row.id || `${row.plan_name}-${row.period_days}`} className={row._dirty ? 'bg-yellow-50' : 'hover:bg-gray-50'}>
                        <td className="px-4 py-3 text-sm text-gray-700 font-medium whitespace-nowrap">
                          {PERIOD_LABELS[row.period_days] || `${row.period_days} дней`}
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="text"
                            placeholder="Отображаемое имя"
                            value={row.name || ''}
                            onChange={e => updateRow(idx, 'name', e.target.value)}
                            className="w-36 border border-gray-200 rounded-lg px-2 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1">
                            <span className="text-gray-400 text-sm">₽</span>
                            <input
                              type="number"
                              min="0"
                              step="1"
                              value={row.price_rub}
                              onChange={e => updateRow(idx, 'price_rub', parseFloat(e.target.value) || 0)}
                              className="w-24 border border-gray-200 rounded-lg px-2 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="number"
                            min="1"
                            max="10"
                            step="1"
                            title="Лимит устройств"
                            value={row.device_limit || 1}
                            onChange={e => updateRow(idx, 'device_limit', parseInt(e.target.value) || 1)}
                            className="w-16 border border-gray-200 rounded-lg px-2 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={row.is_active !== false}
                            onChange={e => updateRow(idx, 'is_active', e.target.checked)}
                            className="w-4 h-4 text-blue-600 rounded"
                          />
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {row._dirty && (
                              <button
                                onClick={() => saveMutation.mutate(row)}
                                disabled={saveMutation.isPending}
                                className="text-xs px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
                              >
                                Сохранить
                              </button>
                            )}
                            {row.id && (
                              <button
                                onClick={() => {
                                  if (window.confirm(`Удалить тариф "${PERIOD_LABELS[row.period_days] || row.period_days + ' дней'}"?`)) {
                                    deleteMutation.mutate(row.id)
                                  }
                                }}
                                className="p-1.5 text-red-400 hover:bg-red-50 rounded"
                                title="Удалить"
                              >
                                <Trash2 size={14} />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )
        })
      )}

      {/* Форма добавления */}
      {showAdd && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
          <h3 className="font-semibold text-gray-800 mb-4">Добавить цену</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Тариф (ключ)</label>
              <select
                value={newRow.plan_name}
                onChange={e => setNewRow(r => ({ ...r, plan_name: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="solo">Solo</option>
                <option value="family">Family</option>
                <option value="custom">Другой...</option>
              </select>
              {newRow.plan_name === 'custom' && (
                <input
                  className="mt-2 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Ключ тарифа (solo, vip...)"
                  onChange={e => setNewRow(r => ({ ...r, plan_name: e.target.value }))}
                />
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Название (отображаемое)</label>
              <input
                type="text"
                placeholder="Соло (1 устр.)"
                value={newRow.name || ''}
                onChange={e => setNewRow(r => ({ ...r, name: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Период (дней)</label>
              <select
                value={newRow.period_days}
                onChange={e => setNewRow(r => ({ ...r, period_days: parseInt(e.target.value) }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={7}>7 дней</option>
                <option value={30}>30 дней</option>
                <option value={90}>90 дней</option>
                <option value={180}>180 дней</option>
                <option value={365}>365 дней</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Цена (₽)</label>
              <input
                type="number"
                min="0"
                value={newRow.price_rub}
                onChange={e => setNewRow(r => ({ ...r, price_rub: parseFloat(e.target.value) || 0 }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Лимит устройств</label>
              <input
                type="number"
                min="1"
                max="10"
                value={newRow.device_limit || 1}
                onChange={e => setNewRow(r => ({ ...r, device_limit: parseInt(e.target.value) || 1 }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
              <input
                type="text"
                placeholder="Для одного устройства"
                value={newRow.description || ''}
                onChange={e => setNewRow(r => ({ ...r, description: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button
              onClick={() => addMutation.mutate()}
              disabled={addMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {addMutation.isPending ? <RefreshCw size={14} className="animate-spin" /> : <Plus size={14} />}
              Добавить
            </button>
            <button onClick={() => setShowAdd(false)} className="px-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-600">
              Отмена
            </button>
          </div>
        </div>
      )}

      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-700">
        <p className="font-medium mb-1">ℹ️ Информация</p>
        <p>Изменения применяются к новым подпискам сразу после сохранения. Цены указаны в рублях (₽).</p>
      </div>
    </div>
  )
}
