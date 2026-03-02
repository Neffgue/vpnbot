import React, { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import DataTable from '../components/DataTable'
import Modal from '../components/Modal'
import { subscriptionsApi } from '../api/subscriptions'
import { showError, showSuccess } from '../store/uiStore'

export default function Subscriptions() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('all')
  const [selectedSub, setSelectedSub] = useState(null)
  const [extendDays, setExtendDays] = useState('')

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['subscriptions', page, status],
    queryFn: () => subscriptionsApi.getSubscriptions(page, 20, status),
    keepPreviousData: true
  })

  const extendMutation = useMutation({
    mutationFn: () => subscriptionsApi.extendSubscription(selectedSub.id, parseInt(extendDays)),
    onSuccess: () => {
      refetch()
      setSelectedSub(null)
      setExtendDays('')
      showSuccess('Подписка успешно продлена')
    },
    onError: () => showError('Не удалось продлить подписку')
  })

  const columns = [
    {
      key: 'user_id',
      label: 'User ID',
      render: (value) => <span className="font-mono text-xs text-gray-700">{String(value || '').slice(0, 8)}...</span>
    },
    {
      key: 'plan_name',
      label: 'План',
      render: (value) => <span className="font-medium text-gray-800">{value || '—'}</span>
    },
    {
      key: 'max_devices',
      label: 'Устройств',
      render: (value) => <span className="text-gray-800">{value ?? 1}</span>
    },
    {
      key: 'expires_at',
      label: 'Истекает',
      render: (value) => {
        if (!value) return '-'
        const d = new Date(value)
        const isExpired = d < new Date()
        return <span className={isExpired ? 'text-red-600' : 'text-gray-800'}>{d.toLocaleDateString('ru-RU')}</span>
      }
    },
    {
      key: 'created_at',
      label: 'Создана',
      render: (value) => <span className="text-gray-800">{value ? new Date(value).toLocaleDateString('ru-RU') : '-'}</span>
    },
    {
      key: 'is_active',
      label: 'Статус',
      render: (value) => (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${value ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
          {value ? 'Активна' : 'Истекла'}
        </span>
      )
    }
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800 mb-1">Подписки</h1>
        <p className="text-gray-500">Управляйте подписками пользователей</p>
      </div>

      <div className="flex gap-4">
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value)
            setPage(1)
          }}
          className="px-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">Все подписки</option>
          <option value="active">Активные</option>
          <option value="expired">Истекшие</option>
        </select>
      </div>

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
        onRowClick={(row) => setSelectedSub(row)}
      />

      <Modal
        isOpen={!!selectedSub}
        title={`Подписка #${String(selectedSub?.id || '').slice(0, 8)}`}
        onClose={() => { setSelectedSub(null); setExtendDays('') }}
        onSubmit={() => extendMutation.mutate()}
        submitText="Продлить"
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-gray-500 text-sm mb-1">Тариф</p>
              <p className="text-gray-800 font-semibold">{selectedSub?.plan_name || '—'}</p>
            </div>
            <div>
              <p className="text-gray-500 text-sm mb-1">Устройств</p>
              <p className="text-gray-800 font-semibold">{selectedSub?.max_devices ?? 1}</p>
            </div>
          </div>
          <div>
            <p className="text-gray-500 text-sm mb-1">Истекает</p>
            <p className="text-gray-800 font-semibold">
              {selectedSub?.expires_at
                ? new Date(selectedSub.expires_at).toLocaleString('ru-RU', {
                    day: '2-digit', month: '2-digit', year: 'numeric',
                    hour: '2-digit', minute: '2-digit'
                  })
                : '—'}
            </p>
          </div>
          <div>
            <p className="text-gray-500 text-sm mb-1">Создана</p>
            <p className="text-gray-800 font-medium">
              {selectedSub?.created_at
                ? new Date(selectedSub.created_at).toLocaleString('ru-RU', {
                    day: '2-digit', month: '2-digit', year: 'numeric',
                    hour: '2-digit', minute: '2-digit'
                  })
                : '—'}
            </p>
          </div>
          <div>
            <p className="text-gray-500 text-sm mb-1">Статус</p>
            <span className={`inline-flex px-2 py-1 rounded-full text-xs font-semibold ${selectedSub?.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
              {selectedSub?.is_active ? 'Активна' : 'Истекла'}
            </span>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Продлить на (дни)</label>
            <input
              type="number"
              value={extendDays}
              onChange={(e) => setExtendDays(e.target.value)}
              placeholder="30"
              min="1"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </Modal>
    </div>
  )
}
