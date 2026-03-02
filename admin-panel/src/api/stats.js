import client from './client'

export const statsApi = {
  // Dashboard stats — uses the existing /admin/stats endpoint
  getDashboardStats: async () => {
    const { data } = await client.get('/admin/stats')
    return data
  },

  getUserStats: async (dateFrom = null, dateTo = null) => {
    const { data } = await client.get('/admin/stats', {
      params: {
        date_from: dateFrom,
        date_to: dateTo
      }
    })
    return data
  },

  getSubscriptionStats: async (dateFrom = null, dateTo = null) => {
    const { data } = await client.get('/admin/stats', {
      params: {
        date_from: dateFrom,
        date_to: dateTo
      }
    })
    return data
  },

  getRevenueStats: async (dateFrom = null, dateTo = null) => {
    const { data } = await client.get('/admin/stats', {
      params: {
        date_from: dateFrom,
        date_to: dateTo
      }
    })
    return data
  },

  getServerStats: async () => {
    const { data } = await client.get('/admin/stats')
    return data
  }
}
