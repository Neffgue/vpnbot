import React from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut, Bell } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { authApi } from '../api/auth'

export default function Header() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)

  const handleLogout = async () => {
    try {
      await authApi.logout()
      useAuthStore.setState({ isAuthenticated: false, user: null })
      navigate('/login')
    } catch (error) {
      console.error('Logout failed:', error)
    }
  }

  return (
    <header className="bg-dark-800 border-b border-dark-700 px-6 py-4 flex justify-between items-center">
      <div>
        <h2 className="text-xl font-semibold text-white">
          Добро пожаловать, {user?.username || user?.email || 'Администратор'}
        </h2>
      </div>

      <div className="flex items-center gap-4">
        <button className="p-2 rounded-lg hover:bg-dark-700 transition-colors">
          <Bell size={20} className="text-gray-400" />
        </button>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 transition-colors"
        >
          <LogOut size={18} />
          <span>Выйти</span>
        </button>
      </div>
    </header>
  )
}
