import client from './client'

export const paymentsApi = {
  getPayments: async (page = 1, limit = 20, status = 'all', dateFrom = null, dateTo = null) => {
    const { data } = await client.get('/admin/payments', {
      params: {
        skip: (page - 1) * limit,
        limit,
        status: status === 'all' ? undefined : status,
        date_from: dateFrom,
        date_to: dateTo
      }
    })
    return data
  },

  getPayment: async (id) => {
    const { data } = await client.get(`/admin/payments/${id}`)
    return data
  },

  approvePayment: async (id) => {
    const { data } = await client.post(`/admin/payments/${id}/approve`)
    return data
  },

  rejectPayment: async (id, reason = '') => {
    const { data } = await client.post(`/admin/payments/${id}/reject`, { reason })
    return data
  },

  getPaymentStats: async (dateFrom = null, dateTo = null) => {
    const { data } = await client.get('/admin/stats', {
      params: {
        date_from: dateFrom,
        date_to: dateTo
      }
    })
    return data
  }
}
