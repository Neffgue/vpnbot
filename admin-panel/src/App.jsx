import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Users from './pages/Users'
import UserDetail from './pages/UserDetail'
import Subscriptions from './pages/Subscriptions'
import Payments from './pages/Payments'
import Servers from './pages/Servers'
import BotTexts from './pages/BotTexts'
import BotButtons from './pages/BotButtons'
import Broadcast from './pages/Broadcast'
import AddBalance from './pages/AddBalance'
import BotSettings from './pages/BotSettings'
import Instructions from './pages/Instructions'
import PlanPrices from './pages/PlanPrices'
import Settings from './pages/Settings'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30000,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/admin">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="users" element={<Users />} />
            <Route path="users/:id" element={<UserDetail />} />
            <Route path="subscriptions" element={<Subscriptions />} />
            <Route path="payments" element={<Payments />} />
            <Route path="servers" element={<Servers />} />
            {/* Управление ботом */}
            <Route path="bot-texts" element={<BotTexts />} />
            <Route path="bot-buttons" element={<BotButtons />} />
            <Route path="broadcast" element={<Broadcast />} />
            <Route path="add-balance" element={<AddBalance />} />
            <Route path="bot-settings" element={<BotSettings />} />
            <Route path="instructions" element={<Instructions />} />
            <Route path="plan-prices" element={<PlanPrices />} />
            {/* Системные */}
            <Route path="settings" element={<Settings />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
