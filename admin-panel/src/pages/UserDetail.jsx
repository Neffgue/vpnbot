import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { usersApi } from '../api/users'
import { showError, showSuccess } from '../store/uiStore'

export default function UserDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [addBalanceAmount, setAddBalanceAmount] = useState('')

  const { data: user, isLoading, refetch } = useQuery({
    queryKey: ['user', id],
    queryFn: () => usersApi.getUser(id)
  })

  const { data: subscriptions } = useQuery({
    queryKey: ['userSubscriptions', id],
    queryFn: () => usersApi.getUserSubscriptions(id),
    enabled: !!user
  })

  const { data: payments } = useQuery({
    queryKey: ['userPayments', id],
    queryFn: () => usersApi.getUserPayments(id),
    enabled: !!user
  })

  const { data: referrals } = useQuery({
    queryKey: ['userReferrals', id],
    queryFn: () => usersApi.getUserReferrals(id),
    enabled: !!user
  })

  const banMutation = useMutation({
    mutationFn: () => user.is_active ? usersApi.banUser(id) : usersApi.unbanUser(id),
    onSuccess: () => {
      refetch()
      showSuccess(user.is_active ? 'Пользователь заблокирован' : 'Пользователь разблокирован')
    },
    onError: () => showError('Не удалось изменить статус пользователя')
  })

  const balanceMutation = useMutation({
    mutationFn: () => usersApi.addBalance(id, parseFloat(addBalanceAmount)),
    onSuccess: () => {
      refetch()
      setAddBalanceAmount('')
      showSuccess('Баланс пополнен успешно')
    },
    onError: () => showError('Не удалось пополнить баланс')
  })

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!user) {
    return <div className="text-center py-8 text-gray-500">Пользователь не найден</div>
  }

  const isActive = user.is_active === true || user.is_active === 'true' || user.is_active === 1
  const isBanned = user.is_banned === true || user.is_banned === 'true' || user.is_banned === 1

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate('/users')}
        className="flex items-center gap-2 text-blue-600 hover:text-blue-800 mb-4"
      >
        <ArrowLeft size={20} />
        Назад к пользователям
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">Информация о пользователе</h2>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-gray-500 text-sm">Email</p>
                  <p className="text-gray-800 font-medium">{user.email || '—'}</p>
                </div>
                <div>
                  <p className="text-gray-500 text-sm">Telegram</p>
                  <p className="text-gray-800 font-medium">{user.telegram_username ? `@${user.telegram_username}` : (user.username ? `@${user.username}` : '—')}</p>
                </div>
                <div>
                  <p className="text-gray-500 text-sm">Баланс</p>
                  <p className="text-gray-800 font-medium text-lg">₽{parseFloat(user.balance || 0).toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-gray-500 text-sm">Статус</p>
                  {isBanned ? (
                    <span className="inline-flex px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">Заблокирован</span>
                  ) : (
                    <span className="inline-flex px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">Активен</span>
                  )}
                </div>
                <div>
                  <p className="text-gray-500 text-sm">Дата регистрации</p>
                  <p className="text-gray-800 font-medium">{user.created_at ? new Date(user.created_at).toLocaleDateString('ru-RU') : '—'}</p>
                </div>
                <div>
                  <p className="text-gray-500 text-sm">Последняя активность</p>
                  <p className="text-gray-800 font-medium">{user.last_active_at ? new Date(user.last_active_at).toLocaleDateString('ru-RU') : '—'}</p>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-200">
                <div className="flex gap-2">
                  <button
                    onClick={() => banMutation.mutate()}
                    disabled={banMutation.isPending}
                    className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors text-white ${
                      isBanned
                        ? 'bg-green-600 hover:bg-green-700'
                        : 'bg-red-600 hover:bg-red-700'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    {isBanned ? 'Разблокировать' : 'Заблокировать'}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm mt-6">
            <h3 className="text-xl font-bold text-gray-800 mb-4">Пополнить баланс</h3>
            <div className="flex gap-2">
              <input
                type="number"
                placeholder="Сумма в рублях"
                value={addBalanceAmount}
                onChange={(e) => setAddBalanceAmount(e.target.value)}
                step="1"
                min="0"
                className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={() => balanceMutation.mutate()}
                disabled={!addBalanceAmount || balanceMutation.isPending}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Пополнить
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
            <h3 className="text-lg font-bold text-gray-800 mb-4">Подписки</h3>
            <div className="space-y-2">
              {!subscriptions || subscriptions?.length === 0 ? (
                <p className="text-gray-500 text-sm">Нет подписок</p>
              ) : (
                subscriptions?.map((sub) => (
                  <div key={sub.id} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <p className="text-gray-800 font-medium">{sub.plan_name}</p>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${sub.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {sub.is_active ? 'Активна' : 'Истекла'}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
            <h3 className="text-lg font-bold text-gray-800 mb-4">Рефералы</h3>
            <div className="text-2xl font-bold text-blue-600">
              {referrals?.count || 0}
            </div>
            <p className="text-gray-500 text-sm">приглашённых пользователей</p>
            {referrals?.earned && (
              <p className="text-gray-800 mt-2 font-medium">
                Заработано: ₽{parseFloat(referrals.earned).toFixed(2)}
              </p>
            )}
          </div>

          <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
            <h3 className="text-lg font-bold text-gray-800 mb-4">Последние платежи</h3>
            <div className="space-y-2">
              {payments?.slice(0, 3).map((payment) => (
                <div key={payment.id} className="text-sm border-b border-gray-100 pb-2 last:border-b-0">
                  <p className="text-gray-800 font-medium">₽{parseFloat(payment.amount || 0).toFixed(2)}</p>
                  <p className="text-gray-500 text-xs">{new Date(payment.created_at).toLocaleDateString('ru-RU')}</p>
                </div>
              ))}
              {(!payments || payments.length === 0) && (
                <p className="text-gray-500 text-sm">Нет платежей</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
