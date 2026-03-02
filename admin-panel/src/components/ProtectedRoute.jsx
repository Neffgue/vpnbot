import React, { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { authApi } from '../api/auth'

export default function ProtectedRoute({ children }) {
  const navigate = useNavigate()
  const [loading, setLoading] = React.useState(true)
  const { isAuthenticated, user, setUser } = useAuthStore()
  // Используем ref чтобы checkAuth запускался только один раз
  const checkedRef = useRef(false)

  useEffect(() => {
    if (checkedRef.current) return
    checkedRef.current = true

    const checkAuth = async () => {
      try {
        const token = localStorage.getItem('access_token')

        if (!token) {
          navigate('/login', { replace: true })
          return
        }

        try {
          const profile = await authApi.getProfile()
          setUser(profile)
          useAuthStore.setState({ isAuthenticated: true })
        } catch (error) {
          // токен протух — пробуем refresh через interceptor в client.js
          // если refresh тоже упал — interceptor сам редиректит на /login
          const token2 = localStorage.getItem('access_token')
          if (!token2) {
            navigate('/login', { replace: true })
          }
        }
      } finally {
        setLoading(false)
      }
    }

    checkAuth()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-500">Загрузка...</p>
        </div>
      </div>
    )
  }

  return children
}
