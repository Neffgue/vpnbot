import React from 'react'

export default function StatCard({ title, value, icon: Icon, trend, color = 'blue' }) {
  const iconBg = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    red: 'bg-red-100 text-red-600',
    purple: 'bg-purple-100 text-purple-600',
  }

  return (
    <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-gray-500 text-sm mb-1">{title}</p>
          <p className="text-2xl font-bold text-gray-800">{value}</p>
          {trend !== undefined && trend !== null && (
            <p className={`text-sm mt-1 ${trend > 0 ? 'text-green-600' : 'text-red-500'}`}>
              {trend > 0 ? '+' : ''}{trend}% за прошлый период
            </p>
          )}
        </div>
        {Icon && (
          <div className={`p-3 rounded-lg ${iconBg[color] || iconBg.blue}`}>
            <Icon size={24} />
          </div>
        )}
      </div>
    </div>
  )
}
