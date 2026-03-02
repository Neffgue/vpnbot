import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { DollarSign, Search, RefreshCw, CheckCircle } from 'lucide-react'
import api from '../api/client'
import Toast from '../components/Toast'

export default function AddBalance() {
  const [userId, setUserId] = useState('')
  const [amount, setAmount] = useState('')
  const [reason, setReason] = useState('')
  const [days, setDays] = useState('')
  const [mode, setMode] = useState('balance') // balance | days
  const [toast, setToast] = useState(null)
  const [success, setSuccess] = useState(null)

  const balanceMutation = useMutation({
    mutationFn: () => api.post(`/admin/users/${userId}/balance`, {
      user_id: userId, amount: Number(amount), reason
    }),
    onSuccess: (res) => {
      setSuccess({ type: 'balance', amount, userId })
      setToast({ type: 'success', message: `Баланс пополнен на ${amount}₽` })
      setAmount(''); setReason('')
    },
    onError: () => setToast({ type: 'error', message: 'Ошибка при начислении баланса' }),
  })

  const daysMutation = useMutation({
    mutationFn: () => api.post(`/admin/users/${userId}/add-days`, {
      user_id: userId, days: Number(days), reason
    }),
    onSuccess: (res) => {
      setSuccess({ type: 'days', days, userId })
      setToast({ type: 'success', message: `Добавлено ${days} дней подписки` })
      setDays(''); setReason('')
    },
    onError: () => setToast({ type: 'error', message: 'Ошибка при добавлении дней' }),
  })

  const isPending = balanceMutation.isPending || daysMutation.isPending

  return (
    <div className="max-w-2xl space-y-6">
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-green-100 rounded-xl flex items-center justify-center">
            <DollarSign size={20} className="text-green-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-800">Начислить баланс / дни</h2>
            <p className="text-sm text-gray-500">Пополнение баланса или добавление дней подписки</p>
          </div>
        </div>

        {/* Режим */}
        <div className="flex gap-2 mb-5 p-1 bg-gray-100 rounded-lg w-fit">
          <button
            onClick={() => setMode('balance')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
              mode === 'balance' ? 'bg-white shadow text-gray-800' : 'text-gray-500'
            }`}
          >💰 Баланс (₽)</button>
          <button
            onClick={() => setMode('days')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
              mode === 'days' ? 'bg-white shadow text-gray-800' : 'text-gray-500'
            }`}
          >📅 Дни подписки</button>
        </div>

        {/* Форма */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Telegram ID или UUID пользователя *
            </label>
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                className="w-full border border-gray-200 rounded-lg pl-9 pr-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="123456789"
                value={userId}
                onChange={e => setUserId(e.target.value)}
              />
            </div>
          </div>

          {mode === 'balance' ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Сумма (₽) *</label>
              <div className="flex gap-2">
                <input
                  type="number" min="0"
                  className="flex-1 border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="100"
                  value={amount}
                  onChange={e => setAmount(e.target.value)}
                />
                {[100, 299, 499, 999].map(v => (
                  <button
                    key={v}
                    onClick={() => setAmount(String(v))}
                    className="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50"
                  >+{v}₽</button>
                ))}
              </div>
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Количество дней *</label>
              <div className="flex gap-2">
                <input
                  type="number" min="1"
                  className="flex-1 border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="30"
                  value={days}
                  onChange={e => setDays(e.target.value)}
                />
                {[7, 30, 90, 365].map(v => (
                  <button
                    key={v}
                    onClick={() => setDays(String(v))}
                    className="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50"
                  >+{v}д</button>
                ))}
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Причина (необязательно)</label>
            <input
              className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Например: компенсация, акция, бонус"
              value={reason}
              onChange={e => setReason(e.target.value)}
            />
          </div>

          <button
            onClick={() => mode === 'balance' ? balanceMutation.mutate() : daysMutation.mutate()}
            disabled={!userId || (mode === 'balance' ? !amount : !days) || isPending}
            className="flex items-center gap-2 px-5 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium"
          >
            {isPending ? (
              <><RefreshCw size={16} className="animate-spin" /> Начисляем...</>
            ) : (
              <><span className="font-bold">₽</span> {mode === 'balance' ? 'Начислить баланс' : 'Добавить дни'}</>
            )}
          </button>
        </div>
      </div>

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center gap-3">
          <CheckCircle size={20} className="text-green-600" />
          <div>
            <p className="font-medium text-green-800">
              {success.type === 'balance'
                ? `✅ Начислено ${success.amount}₽ пользователю ${success.userId}`
                : `✅ Добавлено ${success.days} дней пользователю ${success.userId}`}
            </p>
            <p className="text-sm text-green-600">Пользователь получил уведомление в боте.</p>
          </div>
        </div>
      )}
    </div>
  )
}
