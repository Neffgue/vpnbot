import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Users, Zap, DollarSign, Server } from 'lucide-react'
import StatCard from '../components/StatCard'
import { statsApi } from '../api/stats'

export default function Dashboard() {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['dashboardStats'],
    queryFn: statsApi.getDashboardStats,
    refetchInterval: 60000,
    retry: 1,
    staleTime: 30000,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })

  // Safe stats object with null checks
  const safeStats = stats || {}

  const statCards = [
    {
      title: 'Всего пользователей',
      value: safeStats.total_users ?? 0,
      icon: Users,
      trend: safeStats.user_trend,
      color: 'blue'
    },
    {
      title: 'Активных подписок',
      value: safeStats.active_subscriptions ?? 0,
      icon: Zap,
      trend: safeStats.subscription_trend,
      color: 'green'
    },
    {
      title: 'Доход сегодня',
      value: `₽${(safeStats.revenue_today ?? 0).toFixed(2)}`,
      icon: DollarSign,
      trend: safeStats.daily_revenue_trend,
      color: 'purple'
    },
    {
      title: 'Доход за месяц',
      value: `₽${(safeStats.revenue_month ?? 0).toFixed(2)}`,
      icon: DollarSign,
      color: 'purple'
    },
    {
      title: 'Активных серверов',
      value: safeStats.active_servers ?? 0,
      icon: Server,
      color: 'green'
    },
    {
      title: 'Ожидающих платежей',
      value: safeStats.pending_payments ?? 0,
      icon: DollarSign,
      color: 'red'
    }
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-800 mb-1">Дашборд</h1>
        <p className="text-gray-500">Обзор вашего VPN бизнеса</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
          ⚠️ Не удалось загрузить статистику. Проверьте подключение к бэкенду.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {isLoading ? (
          Array(6)
            .fill(0)
            .map((_, i) => (
              <div key={i} className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
                <div className="h-8 bg-gray-200 rounded w-3/4"></div>
              </div>
            ))
        ) : (
          statCards.map((card, i) => (
            <StatCard
              key={i}
              title={card.title}
              value={card.value}
              icon={card.icon}
              trend={card.trend}
              color={card.color}
            />
          ))
        )}
      </div>

      {!isLoading && !error && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Недавняя активность</h3>
            <div className="space-y-3">
              {safeStats.recent_activity?.length > 0 ? safeStats.recent_activity.map((activity, i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                  <p className="text-gray-700">{activity.description}</p>
                  <span className="text-sm text-gray-500">{activity.time}</span>
                </div>
              )) : (
                <p className="text-gray-500 text-sm">Нет активности</p>
              )}
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Статус серверов</h3>
            <div className="space-y-3">
              {safeStats.servers?.length > 0 ? safeStats.servers.map((server, i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                  <p className="text-gray-700">{server.name}</p>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    server.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {server.is_active ? 'В сети' : 'Не в сети'}
                  </span>
                </div>
              )) : (
                <p className="text-gray-500 text-sm">Серверов нет</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
