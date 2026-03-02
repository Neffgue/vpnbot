import client from './client'

export const serversApi = {
  getServers: async () => {
    const { data } = await client.get('/admin/servers')
    return data
  },

  getServer: async (id) => {
    const { data } = await client.get(`/admin/servers/${id}`)
    return data
  },

  createServer: async (serverData) => {
    const { data } = await client.post('/admin/servers', serverData)
    return data
  },

  updateServer: async (id, serverData) => {
    const { data } = await client.put(`/admin/servers/${id}`, serverData)
    return data
  },

  deleteServer: async (id) => {
    const { data } = await client.delete(`/admin/servers/${id}`)
    return data
  },

  toggleServerActive: async (id) => {
    const { data } = await client.post(`/admin/servers/${id}/toggle-active`)
    return data
  },

  testConnection: async (id) => {
    const { data } = await client.post(`/admin/servers/${id}/test-connection`)
    return data
  },

  getServerStats: async (id) => {
    const { data } = await client.get(`/admin/servers/${id}/stats`)
    return data
  }
}
