import client from './client'

export const usersApi = {
  getUsers: async (page = 1, limit = 20, search = '') => {
    const params = { skip: (page - 1) * limit, limit }
    if (search) params.query = search
    const url = search ? '/admin/users/search' : '/admin/users'
    const { data } = await client.get(url, { params })
    // Backend returns a plain array — wrap into paginated shape
    const items = Array.isArray(data) ? data : (data?.items || [])
    return {
      items,
      total: items.length,
      page,
      per_page: limit,
    }
  },

  getUser: async (id) => {
    const { data } = await client.get(`/admin/users/${id}`)
    return data
  },

  getUserSubscriptions: async (userId) => {
    const { data } = await client.get(`/admin/users/${userId}/subscriptions`)
    return data
  },

  getUserPayments: async (userId) => {
    const { data } = await client.get(`/admin/users/${userId}/payments`)
    return data
  },

  getUserReferrals: async (userId) => {
    const { data } = await client.get(`/admin/users/${userId}/referrals`)
    return data
  },

  banUser: async (userId) => {
    const { data } = await client.post(`/admin/users/${userId}/ban`, {})
    return data
  },

  unbanUser: async (userId) => {
    const { data } = await client.post(`/admin/users/${userId}/unban`)
    return data
  },

  addBalance: async (userId, amount) => {
    const { data } = await client.post(`/admin/users/${userId}/balance`, { amount, reason: 'admin panel' })
    return data
  },

  sendMessage: async (userId, message) => {
    const { data } = await client.post(`/admin/broadcast`, { message, user_ids: [userId] })
    return data
  }
}
