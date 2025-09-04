import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';

interface User {
  id: number;
  telegram_id: string;
  name: string;
  age?: number;
  gender?: string;
  city?: string;
  terms_accepted: boolean;
  is_active: boolean;
  is_in_crisis: boolean;
  created_at: string;
  subscription_active: boolean;
  subscription_plan?: string;
  subscription_ends_at?: string;
  daily_messages_used: number;
  daily_messages_limit: number;
}

export default function Users() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch('/api/users/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setUsers(data);
      }
    } catch (error) {
      console.error('Error fetching users:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleSubscription = async (userId: number, active: boolean) => {
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch(`/api/users/${userId}/subscription`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        setUsers(users.map(user => 
          user.id === userId 
            ? { ...user, subscription_active: !active }
            : user
        ));
      }
    } catch (error) {
      console.error('Error updating subscription:', error);
    }
  };

  const deleteUser = async (userId: number, userName: string) => {
    if (!confirm(`Вы уверены, что хотите удалить пользователя "${userName}"?\n\nЭто действие нельзя отменить!`)) {
      return;
    }

    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch(`/api/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        setUsers(users.filter(user => user.id !== userId));
        alert('Пользователь успешно удален');
      } else {
        const error = await response.json();
        alert(`Ошибка удаления: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error deleting user:', error);
      alert('Ошибка при удалении пользователя');
    }
  };

  const filteredUsers = users.filter(user =>
    user.name?.toLowerCase().includes(search.toLowerCase()) ||
    user.telegram_id?.toLowerCase().includes(search.toLowerCase()) ||
    user.city?.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return <div className="p-6">Loading...</div>;
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">👥 Пользователи</h1>
        <div className="flex items-center space-x-4">
          <input
            type="text"
            placeholder="Поиск пользователей..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="px-3 py-2 border rounded-md"
          />
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Список пользователей ({filteredUsers.length} чел.)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2">Пользователь</th>
                  <th className="text-left py-2">Telegram ID</th>
                  <th className="text-left py-2">Статус</th>
                  <th className="text-left py-2">Подписка</th>
                  <th className="text-left py-2">Сообщений</th>
                  <th className="text-left py-2">Создан</th>
                  <th className="text-left py-2">Действия</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-gray-500">
                      {users.length === 0 ? 'Пользователи не найдены' : 'Нет пользователей по запросу'}
                    </td>
                  </tr>
                ) : (
                  filteredUsers.map((user) => (
                    <tr key={user.id} className="border-b hover:bg-gray-50">
                      <td className="py-3">
                        <div>
                          <div className="font-medium">{user.name || 'Без имени'}</div>
                          <div className="text-sm text-gray-500">
                            {user.age && `${user.age} лет`} {user.gender && `• ${user.gender}`}
                          </div>
                          {user.city && (
                            <div className="text-xs text-gray-400">📍 {user.city}</div>
                          )}
                        </div>
                      </td>
                      <td className="py-3 font-mono">{user.telegram_id}</td>
                      <td className="py-3">
                        <div className="flex flex-col gap-1">
                          <span className={`px-2 py-1 rounded text-xs w-fit ${
                            user.is_active 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-gray-100 text-gray-800'
                          }`}>
                            {user.is_active ? 'Активен' : 'Неактивен'}
                          </span>
                          {user.is_in_crisis && (
                            <span className="px-2 py-1 rounded text-xs bg-red-100 text-red-800 w-fit">
                              🆘 Кризис
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3">
                        <div className="flex flex-col gap-1">
                          <span className={`px-2 py-1 rounded text-xs w-fit ${
                            user.subscription_active 
                              ? 'bg-blue-100 text-blue-800' 
                              : 'bg-gray-100 text-gray-800'
                          }`}>
                            {user.subscription_active ? '⭐ Премиум' : '🆓 Бесплатно'}
                          </span>
                          {user.subscription_plan && (
                            <div className="text-xs text-gray-500">{user.subscription_plan}</div>
                          )}
                        </div>
                      </td>
                      <td className="py-3">
                        <div className="text-sm">
                          <div>{user.daily_messages_used}/{user.daily_messages_limit}</div>
                          <div className="text-xs text-gray-500">сегодня</div>
                        </div>
                      </td>
                      <td className="py-3 text-sm text-gray-600">
                        {new Date(user.created_at).toLocaleDateString('ru-RU')}
                      </td>
                      <td className="py-3">
                        <div className="flex gap-1">
                          <button
                            onClick={() => toggleSubscription(user.id, user.subscription_active)}
                            className={`px-2 py-1 rounded text-xs ${
                              user.subscription_active
                                ? 'bg-red-500 hover:bg-red-600 text-white'
                                : 'bg-green-500 hover:bg-green-600 text-white'
                            }`}
                            title={user.subscription_active ? 'Отключить подписку' : 'Включить подписку'}
                          >
                            {user.subscription_active ? '📵 Отключить подписку' : '⭐ Включить подписку'}
                          </button>
                          <button
                            onClick={() => deleteUser(user.id, user.name || user.telegram_id)}
                            className="px-2 py-1 rounded text-xs bg-gray-600 hover:bg-red-600 text-white transition-colors"
                            title="Удалить пользователя"
                          >
                            🗑️ Удалить
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}