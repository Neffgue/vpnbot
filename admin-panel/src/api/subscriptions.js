import client from './client'

export const subscriptionsApi = {
  getSubscriptions: async (page = 1, limit = 20, status = 'all') => {
    const { data } = await client.get('/admin/subscriptions', {
      params: {
        skip: (page - 1) * limit,
        limit,
        status: status === 'all' ? undefined : status
      }
    })
    // Backend returns plain array — wrap into paginated shape
    const items = Array.isArray(data) ? data : (data?.items || [])
    return { items, total: items.length, page, per_page: limit }
  },

  getSubscription: async (id) => {
    const { data } = await client.get(`/admin/subscriptions/${id}`)
    return data
  },

  extendSubscription: async (id, days) => {
    const { data } = await client.post(`/admin/subscriptions/${id}/extend`, { days })
    return data
  },

  cancelSubscription: async (id) => {
    const { data } = await client.post(`/admin/subscriptions/${id}/cancel`)
    return data
  },

  resetTraffic: async (id) => {
    const { data } = await client.post(`/admin/subscriptions/${id}/reset-traffic`)
    return data
  },

  createSubscription: async (userId, planId, days) => {
    const { data } = await client.post('/admin/subscriptions', {
      user_id: userId,
      plan_id: planId,
      days
    })
    return data
  }
}
