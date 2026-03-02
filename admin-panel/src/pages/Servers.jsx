import React, { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Plus, Trash2, Edit2 } from 'lucide-react'
import DataTable from '../components/DataTable'
import Modal from '../components/Modal'
import { serversApi } from '../api/servers'
import { showError, showSuccess } from '../store/uiStore'

export default function Servers() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingServer, setEditingServer] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    country: '',
    host: '',
    port: 443,
    panel_url: '',
    panel_username: '',
    panel_password: '',
    inbound_id: '',
    bypass_ru: false
  })

  const { data: servers, isLoading, refetch } = useQuery({
    queryKey: ['servers'],
    queryFn: serversApi.getServers
  })

  const createMutation = useMutation({
    mutationFn: () => serversApi.createServer(formData),
    onSuccess: () => {
      refetch()
      resetForm()
      showSuccess('Server created successfully')
    },
    onError: () => showError('Failed to create server')
  })

  const updateMutation = useMutation({
    mutationFn: () => serversApi.updateServer(editingServer.id, formData),
    onSuccess: () => {
      refetch()
      resetForm()
      showSuccess('Server updated successfully')
    },
    onError: () => showError('Failed to update server')
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => serversApi.deleteServer(id),
    onSuccess: () => {
      refetch()
      showSuccess('Server deleted successfully')
    },
    onError: () => showError('Failed to delete server')
  })

  const toggleMutation = useMutation({
    mutationFn: (id) => serversApi.toggleServerActive(id),
    onSuccess: () => {
      refetch()
      showSuccess('Server status updated')
    },
    onError: () => showError('Failed to update server status')
  })

  const resetForm = () => {
    setFormData({
      name: '',
      country: '',
      host: '',
      port: 443,
      panel_url: '',
      panel_username: '',
      panel_password: '',
      inbound_id: '',
      bypass_ru: false
    })
    setEditingServer(null)
    setIsModalOpen(false)
  }

  const handleEditClick = (server) => {
    setEditingServer(server)
    setFormData({
      name: server.name,
      country: server.country,
      host: server.host,
      port: server.port,
      panel_url: server.panel_url,
      panel_username: server.panel_username,
      panel_password: server.panel_password,
      inbound_id: server.inbound_id,
      bypass_ru: server.bypass_ru
    })
    setIsModalOpen(true)
  }

  const handleSubmit = () => {
    if (editingServer) {
      updateMutation.mutate()
    } else {
      createMutation.mutate()
    }
  }

  const columns = [
    {
      key: 'name',
      label: 'Название'
    },
    {
      key: 'country',
      label: 'Страна'
    },
    {
      key: 'host',
      label: 'Хост'
    },
    {
      key: 'port',
      label: 'Порт'
    },
    {
      key: 'is_active',
      label: 'Статус',
      render: (value, row) => (
        <button
          onClick={() => toggleMutation.mutate(row.id)}
          className={`badge cursor-pointer ${value ? 'badge-success' : 'badge-danger'}`}
        >
          {value ? 'В сети' : 'Не в сети'}
        </button>
      )
    },
    {
      key: 'id',
      label: 'Действия',
      render: (value, row) => (
        <div className="flex gap-2">
          <button
            onClick={() => handleEditClick(row)}
            className="p-1 hover:bg-dark-700 rounded transition-colors"
          >
            <Edit2 size={16} className="text-blue-400" />
          </button>
          <button
            onClick={() => deleteMutation.mutate(value)}
            className="p-1 hover:bg-dark-700 rounded transition-colors"
          >
            <Trash2 size={16} className="text-red-400" />
          </button>
        </div>
      )
    }
  ]

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Серверы</h1>
          <p className="text-gray-400">Управляйте вашими 3x-ui VPN серверами</p>
        </div>
        <button
          onClick={() => {
            resetForm()
            setIsModalOpen(true)
          }}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors"
        >
          <Plus size={20} />
          Добавить сервер
        </button>
      </div>

      <DataTable
        columns={columns}
        data={servers || []}
        loading={isLoading}
      />

      <Modal
        isOpen={isModalOpen}
        title={editingServer ? 'Редактировать сервер' : 'Добавить сервер'}
        onClose={resetForm}
        onSubmit={handleSubmit}
        submitText={editingServer ? 'Обновить' : 'Создать'}
      >
        <div className="space-y-4 max-h-96 overflow-y-auto">
          <div>
            <label htmlFor="name">Название сервера</label>
            <input
              id="name"
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              placeholder="Сервер 1"
            />
          </div>
          <div>
            <label htmlFor="country">Страна</label>
            <input
              id="country"
              type="text"
              value={formData.country}
              onChange={(e) => setFormData({...formData, country: e.target.value})}
              placeholder="США"
            />
          </div>
          <div>
            <label htmlFor="host">Хост/IP</label>
            <input
              id="host"
              type="text"
              value={formData.host}
              onChange={(e) => setFormData({...formData, host: e.target.value})}
              placeholder="1.2.3.4"
            />
          </div>
          <div>
            <label htmlFor="port">Порт</label>
            <input
              id="port"
              type="number"
              value={formData.port}
              onChange={(e) => setFormData({...formData, port: parseInt(e.target.value)})}
            />
          </div>
          <div>
            <label htmlFor="panel_url">URL панели</label>
            <input
              id="panel_url"
              type="text"
              value={formData.panel_url}
              onChange={(e) => setFormData({...formData, panel_url: e.target.value})}
              placeholder="https://server.com:2053"
            />
          </div>
          <div>
            <label htmlFor="panel_username">Пользователь панели</label>
            <input
              id="panel_username"
              type="text"
              value={formData.panel_username}
              onChange={(e) => setFormData({...formData, panel_username: e.target.value})}
            />
          </div>
          <div>
            <label htmlFor="panel_password">Пароль панели</label>
            <input
              id="panel_password"
              type="password"
              value={formData.panel_password}
              onChange={(e) => setFormData({...formData, panel_password: e.target.value})}
            />
          </div>
          <div>
            <label htmlFor="inbound_id">ID входящего трафика</label>
            <input
              id="inbound_id"
              type="text"
              value={formData.inbound_id}
              onChange={(e) => setFormData({...formData, inbound_id: e.target.value})}
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              id="bypass_ru"
              type="checkbox"
              checked={formData.bypass_ru}
              onChange={(e) => setFormData({...formData, bypass_ru: e.target.checked})}
              className="w-4 h-4"
            />
            <label htmlFor="bypass_ru" className="m-0">Обход РФ</label>
          </div>
        </div>
      </Modal>
    </div>
  )
}
