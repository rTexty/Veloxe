import { useQuery } from 'react-query'
import { 
  UsersIcon, 
  ChatBubbleLeftIcon, 
  CreditCardIcon,
  ExclamationTriangleIcon,
  ArrowUpIcon,
  ArrowDownIcon
} from '@heroicons/react/24/outline'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const api = {
  getUserStats: () => 
    fetch('/api/users/stats', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('admin_token')}` }
    }).then(res => res.json()),
    
  getDailyStats: () =>
    fetch('/api/analytics/daily?days=7', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('admin_token')}` }
    }).then(res => res.json()),
    
  getCrisisStats: () =>
    fetch('/api/analytics/crisis?days=7', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('admin_token')}` }
    }).then(res => res.json())
}

export default function Dashboard() {
  const { data: userStats, isLoading: userStatsLoading } = useQuery(
    'userStats', 
    api.getUserStats,
    { refetchInterval: 30000 }
  )

  const { data: dailyStats } = useQuery(
    'dailyStats',
    api.getDailyStats,
    { refetchInterval: 60000 }
  )

  const { data: crisisStats } = useQuery(
    'crisisStats',
    api.getCrisisStats,
    { refetchInterval: 30000 }
  )

  const StatCard = ({ 
    title, 
    value, 
    change, 
    changeType, 
    icon: Icon, 
    loading = false 
  }: {
    title: string
    value: number | string
    change?: number
    changeType?: 'increase' | 'decrease'
    icon: any
    loading?: boolean
  }) => (
    <div className="card p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <div className="flex items-center mt-2">
            {loading ? (
              <div className="h-8 w-16 bg-gray-200 animate-pulse rounded"></div>
            ) : (
              <p className="text-3xl font-bold text-gray-900">{value}</p>
            )}
            {change !== undefined && (
              <div className={`flex items-center ml-2 text-sm ${
                changeType === 'increase' ? 'text-green-600' : 'text-red-600'
              }`}>
                {changeType === 'increase' ? (
                  <ArrowUpIcon className="w-4 h-4 mr-1" />
                ) : (
                  <ArrowDownIcon className="w-4 h-4 mr-1" />
                )}
                {Math.abs(change)}%
              </div>
            )}
          </div>
        </div>
        <div className="p-3 bg-primary-50 rounded-lg">
          <Icon className="w-6 h-6 text-primary-600" />
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-2">Overview of your chatbot performance</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Users"
          value={userStats?.total_users || 0}
          icon={UsersIcon}
          loading={userStatsLoading}
        />
        <StatCard
          title="Active Today"
          value={userStats?.active_users_today || 0}
          icon={ChatBubbleLeftIcon}
          loading={userStatsLoading}
        />
        <StatCard
          title="Subscribers"
          value={userStats?.subscribers || 0}
          icon={CreditCardIcon}
          loading={userStatsLoading}
        />
        <StatCard
          title="Crisis Users"
          value={userStats?.crisis_users || 0}
          icon={ExclamationTriangleIcon}
          loading={userStatsLoading}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Activity Chart */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Daily Activity (Last 7 Days)</h2>
          {dailyStats ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={dailyStats}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={(date) => new Date(date).toLocaleDateString()}
                />
                <YAxis />
                <Tooltip 
                  labelFormatter={(date) => new Date(date).toLocaleDateString()}
                />
                <Line 
                  type="monotone" 
                  dataKey="active_users" 
                  stroke="#0ea5e9" 
                  name="Active Users"
                  strokeWidth={2}
                />
                <Line 
                  type="monotone" 
                  dataKey="new_users" 
                  stroke="#10b981" 
                  name="New Users"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-300 bg-gray-100 animate-pulse rounded"></div>
          )}
        </div>

        {/* Crisis Stats */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Crisis Intervention (Last 7 Days)</h2>
          {crisisStats ? (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Crisis Triggered</span>
                <span className="font-semibold text-red-600">{crisisStats.crisis_triggered}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Crisis Resolved</span>
                <span className="font-semibold text-green-600">{crisisStats.crisis_resolved}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Currently in Crisis</span>
                <span className="font-semibold text-orange-600">{crisisStats.currently_in_crisis}</span>
              </div>
              <div className="pt-4 border-t border-gray-200">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Resolution Rate</span>
                  <span className="font-semibold text-blue-600">{crisisStats.resolution_rate}%</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-6 bg-gray-100 animate-pulse rounded"></div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">System Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center space-x-3">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span className="text-sm text-gray-600">Bot Status: Online</span>
          </div>
          <div className="flex items-center space-x-3">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span className="text-sm text-gray-600">Database: Connected</span>
          </div>
          <div className="flex items-center space-x-3">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span className="text-sm text-gray-600">API: Healthy</span>
          </div>
        </div>
      </div>
    </div>
  )
}