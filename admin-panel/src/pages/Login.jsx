import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Lock, User } from 'lucide-react'
import { authApi } from '../api/auth'
import { useAuthStore } from '../store/authStore'
import { showError, showSuccess } from '../store/uiStore'

export default function Login() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      const data = await authApi.login(username, password)
      useAuthStore.setState({
        isAuthenticated: true,
        user: data.user
      })
      showSuccess('Logged in successfully')
      navigate('/')
    } catch (error) {
      showError(error.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center">
      <div className="w-full max-w-md">
        <div className="bg-dark-800 rounded-lg p-8 border border-dark-700">
          <h1 className="text-3xl font-bold text-white mb-2">VPN Админ</h1>
          <p className="text-gray-400 mb-8">Панель управления</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="username">Логин</label>
              <div className="relative">
                <User size={18} className="absolute left-3 top-3 text-gray-500" />
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin"
                  className="pl-10"
                  required
                />
              </div>
            </div>

            <div>
              <label htmlFor="password">Пароль</label>
              <div className="relative">
                <Lock size={18} className="absolute left-3 top-3 text-gray-500" />
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="pl-10"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-6 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading && <div className="spinner w-4 h-4"></div>}
              {loading ? 'Вход...' : 'Войти'}
            </button>
          </form>

          <p className="text-center text-gray-400 text-sm mt-6">
            Доступ только для администраторов
          </p>
        </div>
      </div>
    </div>
  )
}
