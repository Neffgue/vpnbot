import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import DataTable from '../components/DataTable'
import { usersApi } from '../api/users'
import { showError } from '../store/uiStore'

export default function Users() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')

  const { data, isLoading, error } = useQuery({
    queryKey: ['users', page, search],
    queryFn: () => usersApi.getUsers(page, 20, search),
    keepPreviousData: true
  })

  if (error) {
    showError('Ошибка загрузки пользователей')
  }

  const columns = [
    {
      key: 'telegram_id',
      label: 'Telegram ID',
      render: (value) => <span className="font-mono text-xs text-gray-800">{value || '-'}</span>
    },
    {
      key: 'username',
      label: 'Username',
      render: (value, row) => (
        <div>
          <div className="font-medium text-gray-800">{row.first_name || ''} {row.last_name || ''}</div>
          <div className="text-xs text-gray-400">{value ? `@${value}` : '-'}</div>
        </div>
      )
    },
    {
      key: 'balance',
      label: 'Баланс',
      render: (value) => <span className="font-medium text-gray-700">₽{parseFloat(value || 0).toFixed(2)}</span>
    },
    {
      key: 'created_at',
      label: 'Регистрация',
      render: (value) => value ? new Date(value).toLocaleDateString('ru-RU') : '-'
    },
    {
      key: 'is_banned',
      label: 'Статус',
      render: (value) => {
        const banned = value === true || value === 'true' || value === 'True' || value === 1 || value === '1'
        return (
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${banned ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
            {banned ? 'Заблокирован' : 'Активен'}
          </span>
        )
      }
    }
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800 mb-1">Пользователи</h1>
        <p className="text-gray-500">Управляйте пользователями VPN бота</p>
      </div>

      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search size={18} className="absolute left-3 top-3 text-gray-400" />
          <input
            type="text"
            placeholder="Поиск по username, имени или Telegram ID..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
          Ошибка загрузки пользователей. Проверьте подключение к бэкенду.
        </div>
      )}

      <DataTable
        columns={columns}
        data={data?.items || []}
        loading={isLoading}
        pagination={data && {
          page: data.page,
          total: data.total,
          from: (data.page - 1) * data.per_page + 1,
          to: Math.min(data.page * data.per_page, data.total),
          total_pages: Math.ceil(data.total / data.per_page)
        }}
        onPageChange={setPage}
        onRowClick={(row) => navigate(`/users/${row.id}`)}
      />
    </div>
  )
}
