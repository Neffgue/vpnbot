import client from './client'

export const authApi = {
  login: async (username, password) => {
    const { data } = await client.post('/auth/login', { username, password })
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    return data
  },

  logout: async () => {
    try {
      await client.post('/auth/logout')
    } finally {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    }
  },

  getProfile: async () => {
    const { data } = await client.get('/auth/profile')
    return data
  },

  refreshToken: async (refreshToken) => {
    const { data } = await client.post('/auth/refresh', { refresh_token: refreshToken })
    localStorage.setItem('access_token', data.access_token)
    return data
  }
}
