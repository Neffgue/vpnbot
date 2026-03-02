import { NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import {
  LayoutDashboard, Users, CreditCard, Server, Settings,
  Send, DollarSign, FileText, MousePointer, Sliders,
  Tag, LogOut, ChevronDown, ChevronRight, Shield, BookOpen,
} from 'lucide-react'
import { useState } from 'react'

const navLinkClass = ({ isActive }) =>
  `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
    isActive
      ? 'bg-blue-600 text-white shadow-sm'
      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-800'
  }`

function Group({ label, icon: Icon, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-800 transition-colors"
      >
        <span className="flex items-center gap-2">
          {Icon && <Icon size={12} />}
          {label}
        </span>
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>
      {open && <div className="space-y-0.5 mt-0.5">{children}</div>}
    </div>
  )
}

export default function Sidebar() {
  const { logout } = useAuthStore()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <aside className="w-60 bg-white border-r border-gray-100 flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-gray-100">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <Shield size={16} className="text-white" />
          </div>
          <div>
            <div className="font-bold text-gray-800 text-sm">VPN Admin</div>
            <div className="text-xs text-gray-400">Панель управления</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-4">
        {/* Обзор */}
        <Group label="Обзор" defaultOpen={true}>
          <NavLink to="/dashboard" className={navLinkClass}>
            <LayoutDashboard size={16} /> Дашборд
          </NavLink>
        </Group>

        {/* Пользователи */}
        <Group label="Пользователи" defaultOpen={true}>
          <NavLink to="/users" className={navLinkClass}>
            <Users size={16} /> Пользователи
          </NavLink>
          <NavLink to="/subscriptions" className={navLinkClass}>
            <CreditCard size={16} /> Подписки
          </NavLink>
          <NavLink to="/payments" className={navLinkClass}>
            <DollarSign size={16} /> Платежи
          </NavLink>
          <NavLink to="/add-balance" className={navLinkClass}>
            <DollarSign size={16} /> Начислить баланс
          </NavLink>
        </Group>

        {/* Управление ботом */}
        <Group label="Управление ботом" defaultOpen={true}>
          <NavLink to="/broadcast" className={navLinkClass}>
            <Send size={16} /> Рассылка
          </NavLink>
          <NavLink to="/bot-texts" className={navLinkClass}>
            <FileText size={16} /> Тексты бота
          </NavLink>
          <NavLink to="/bot-buttons" className={navLinkClass}>
            <MousePointer size={16} /> Кнопки меню
          </NavLink>
          <NavLink to="/bot-settings" className={navLinkClass}>
            <Sliders size={16} /> Настройки бота
          </NavLink>
          <NavLink to="/plan-prices" className={navLinkClass}>
            <Tag size={16} /> Цены тарифов
          </NavLink>
          <NavLink to="/instructions" className={navLinkClass}>
            <BookOpen size={16} /> Инструкции
          </NavLink>
        </Group>

        {/* Инфраструктура */}
        <Group label="Инфраструктура">
          <NavLink to="/servers" className={navLinkClass}>
            <Server size={16} /> VPN Серверы
          </NavLink>
          <NavLink to="/settings" className={navLinkClass}>
            <Settings size={16} /> Системные
          </NavLink>
        </Group>
      </nav>

      {/* Footer */}
      <div className="px-3 py-4 border-t border-gray-100">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all"
        >
          <LogOut size={16} /> Выйти
        </button>
      </div>
    </aside>
  )
}
