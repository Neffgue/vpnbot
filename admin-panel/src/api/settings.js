import client from './client'

export const settingsApi = {
  getSettings: async () => {
    const { data } = await client.get('/admin/settings')
    return data
  },

  updateSettings: async (settings) => {
    const { data } = await client.put('/admin/settings', settings)
    return data
  },

  getBotTexts: async () => {
    const { data } = await client.get('/admin/bot-texts')
    return data
  },

  updateBotTexts: async (texts) => {
    // texts is an object {key: value, ...} — save each key individually
    const results = {}
    for (const [key, value] of Object.entries(texts)) {
      const { data } = await client.put(`/admin/bot-texts/${key}`, { value })
      results[key] = data
    }
    return results
  },

  getPlanPrices: async () => {
    const { data } = await client.get('/admin/plans')
    return data
  },

  updatePlanPrices: async (prices) => {
    const { data } = await client.put('/admin/plans', prices)
    return data
  },

  broadcast: async (message, userIds = null) => {
    const payload = { message }
    if (userIds) payload.user_ids = userIds
    const { data } = await client.post('/admin/broadcast', payload)
    return data
  }
}
