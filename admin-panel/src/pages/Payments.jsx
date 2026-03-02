import React, { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import DataTable from '../components/DataTable'
import { paymentsApi } from '../api/payments'
import { showError, showSuccess } from '../store/uiStore'

export default function Payments() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('all')
  const [selectedPayment, setSelectedPayment] = useState(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['payments', page, status],
    queryFn: () => paymentsApi.getPayments(page, 20, status),
    keepPreviousData: true
  })

  const approveMutation = useMutation({
    mutationFn: (paymentId) => paymentsApi.approvePayment(paymentId),
    onSuccess: () => {
      refetch()
      setSelectedPayment(null)
      showSuccess('Payment approved')
    },
    onError: () => showError('Failed to approve payment')
  })

  const rejectMutation = useMutation({
    mutationFn: (paymentId) => paymentsApi.rejectPayment(paymentId),
    onSuccess: () => {
      refetch()
      setSelectedPayment(null)
      showSuccess('Payment rejected')
    },
    onError: () => showError('Failed to reject payment')
  })

  const columns = [
    {
      key: 'id',
      label: 'ID',
      width: '60px'
    },
    {
      key: 'user_email',
      label: 'Пользователь'
    },
    {
      key: 'amount',
      label: 'Сумма',
      render: (value) => `₽${parseFloat(value || 0).toFixed(2)}`
    },
    {
      key: 'method',
      label: 'Способ'
    },
    {
      key: 'created_at',
      label: 'Дата',
      render: (value) => new Date(value).toLocaleDateString('ru-RU')
    },
    {
      key: 'status',
      label: 'Статус',
      render: (value) => {
        const statusMap = {
          pending: { label: 'Ожидает', cls: 'bg-yellow-100 text-yellow-700' },
          approved: { label: 'Одобрен', cls: 'bg-green-100 text-green-700' },
          completed: { label: 'Выполнен', cls: 'bg-green-100 text-green-700' },
          rejected: { label: 'Отклонён', cls: 'bg-red-100 text-red-700' },
        }
        const s = statusMap[value] || { label: value, cls: 'bg-gray-100 text-gray-700' }
        return (
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${s.cls}`}>
            {s.label}
          </span>
        )
      }
    }
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800 mb-1">Платежи</h1>
        <p className="text-gray-500">Управляйте платежами пользователей</p>
      </div>

      <div className="flex gap-4">
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value)
            setPage(1)
          }}
          className="px-4 py-2"
        >
          <option value="all">Все платежи</option>
          <option value="pending">Ожидающие</option>
          <option value="approved">Одобрены</option>
          <option value="rejected">Отклонены</option>
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
        onRowClick={(row) => setSelectedPayment(row)}
      />

      {selectedPayment && (
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h3 className="text-xl font-bold text-gray-800 mb-4">Детали платежа</h3>
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div>
              <p className="text-gray-500 text-sm">ID</p>
              <p className="text-gray-800 font-medium">{selectedPayment.id}</p>
            </div>
            <div>
              <p className="text-gray-500 text-sm">Пользователь</p>
              <p className="text-gray-800 font-medium">{selectedPayment.user_email || '—'}</p>
            </div>
            <div>
              <p className="text-gray-500 text-sm">Сумма</p>
              <p className="text-gray-800 font-medium">₽{parseFloat(selectedPayment.amount || 0).toFixed(2)}</p>
            </div>
            <div>
              <p className="text-gray-500 text-sm">Способ</p>
              <p className="text-gray-800 font-medium">{selectedPayment.method || '—'}</p>
            </div>
            <div>
              <p className="text-gray-500 text-sm">Статус</p>
              <p className="text-gray-800 font-medium">{selectedPayment.status || '—'}</p>
            </div>
            <div>
              <p className="text-gray-500 text-sm">Дата</p>
              <p className="text-gray-800 font-medium">{new Date(selectedPayment.created_at).toLocaleString('ru-RU')}</p>
            </div>
          </div>

          {selectedPayment.status === 'pending' && (
            <div className="flex gap-2">
              <button
                onClick={() => approveMutation.mutate(selectedPayment.id)}
                disabled={approveMutation.isPending}
                className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium disabled:opacity-50"
              >
                Одобрить
              </button>
              <button
                onClick={() => rejectMutation.mutate(selectedPayment.id)}
                disabled={rejectMutation.isPending}
                className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium disabled:opacity-50"
              >
                Отклонить
              </button>
            </div>
          )}

          <button
            onClick={() => setSelectedPayment(null)}
            className="w-full mt-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium"
          >
            Закрыть
          </button>
        </div>
      )}
    </div>
  )
}
