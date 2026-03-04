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
  const { data: rawPlans = [], isLoading } = useQuery({
    queryKey: ['plan-prices'],
    queryFn: () => api.get('/admin/plans').then(r => Array.isArray(r.data) ? r.data : []),
    staleTime: 10000,
  })

  // Локальное состояние для редактирования
  const [rows, setRows] = useState([])
  const [newRow, setNewRow] = useState({ plan_name: 'Solo', period_days: 30, price_rub: 299, name: '', device_limit: 1 })
  const [showAdd, setShowAdd] = useState(false)

  useEffect(() => {
    if (rawPlans.length > 0) {
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
    }
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
    onError: () => setToast({ type: 'error', message: 'Ошибка сохранения' }),
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
    onError: () => setToast({ type: 'error', message: 'Ошибка сохранения' }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => api.delete(`/admin/plans/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['plan-prices'] })
      setToast({ type: 'success', message: 'Цена удалена' })
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
      setNewRow({ plan_name: 'Solo', period_days: 30, price_rub: 299 })
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
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Период</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Цена (₽)</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Действия</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {planRows.sort((a, b) => a.period_days - b.period_days).map((row) => {
                    const idx = rows.findIndex(r => r === row)
                    return (
                      <tr key={row.id || `${row.plan_name}-${row.period_days}`} className={row._dirty ? 'bg-yellow-50' : 'hover:bg-gray-50'}>
                        <td className="px-6 py-3 text-sm text-gray-700">
                          {PERIOD_LABELS[row.period_days] || `${row.period_days} дней`}
                        </td>
                        <td className="px-6 py-3">
                          <div className="flex items-center gap-2">
                            <span className="text-gray-400 text-sm">₽</span>
                            <input
                              type="number"
                              min="0"
                              step="1"
                              value={row.price_rub}
                              onChange={e => updateRow(idx, 'price_rub', parseFloat(e.target.value) || 0)}
                              className="w-28 border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                          </div>
                        </td>
                        <td className="px-6 py-3 text-right">
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
                                onClick={() => deleteMutation.mutate(row.id)}
                                className="p-1.5 text-red-400 hover:bg-red-50 rounded"
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
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Тариф</label>
              <select
                value={newRow.plan_name}
                onChange={e => setNewRow(r => ({ ...r, plan_name: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option>Solo</option>
                <option>Family</option>
                <option value="custom">Другой...</option>
              </select>
              {newRow.plan_name === 'custom' && (
                <input
                  className="mt-2 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Название тарифа"
                  onChange={e => setNewRow(r => ({ ...r, plan_name: e.target.value }))}
                />
              )}
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
