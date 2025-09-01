import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';

interface Analytics {
  total_users: number;
  active_subscriptions: number;
  messages_today: number;
  messages_this_week: number;
  messages_this_month: number;
  revenue_this_month: number;
  new_users_today: number;
  new_users_this_week: number;
  crisis_interventions: number;
  memory_anchors_created: number;
}

export default function Analytics() {
  const [analytics, setAnalytics] = useState<Analytics>({
    total_users: 0,
    active_subscriptions: 0,
    messages_today: 0,
    messages_this_week: 0,
    messages_this_month: 0,
    revenue_this_month: 0,
    new_users_today: 0,
    new_users_this_week: 0,
    crisis_interventions: 0,
    memory_anchors_created: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch('/api/analytics/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setAnalytics(data);
      }
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-6">Loading analytics...</div>;
  }

  const StatCard = ({ title, value, subtitle }: { title: string; value: number; subtitle?: string }) => (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center">
          <div>
            <p className="text-sm font-medium text-gray-600">{title}</p>
            <p className="text-2xl font-bold">{value.toLocaleString()}</p>
            {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
          </div>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Analytics</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard 
          title="Total Users" 
          value={analytics.total_users} 
          subtitle="All registered users"
        />
        <StatCard 
          title="Active Subscriptions" 
          value={analytics.active_subscriptions}
          subtitle="Paying customers"
        />
        <StatCard 
          title="Messages Today" 
          value={analytics.messages_today}
          subtitle="Bot interactions"
        />
        <StatCard 
          title="Revenue This Month" 
          value={analytics.revenue_this_month}
          subtitle="₽ from subscriptions"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>User Growth</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span>New Users Today</span>
                <span className="font-bold text-green-600">{analytics.new_users_today}</span>
              </div>
              <div className="flex justify-between items-center">
                <span>New Users This Week</span>
                <span className="font-bold text-green-600">{analytics.new_users_this_week}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Message Statistics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span>This Week</span>
                <span className="font-bold">{analytics.messages_this_week}</span>
              </div>
              <div className="flex justify-between items-center">
                <span>This Month</span>
                <span className="font-bold">{analytics.messages_this_month}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Bot Intelligence</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span>Crisis Interventions</span>
                <span className="font-bold text-red-600">{analytics.crisis_interventions}</span>
              </div>
              <div className="flex justify-between items-center">
                <span>Memory Anchors Created</span>
                <span className="font-bold text-blue-600">{analytics.memory_anchors_created}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Conversion Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span>Subscription Rate</span>
                <span className="font-bold text-purple-600">
                  {analytics.total_users > 0 
                    ? `${Math.round((analytics.active_subscriptions / analytics.total_users) * 100)}%`
                    : '0%'
                  }
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span>Avg Messages/User</span>
                <span className="font-bold">
                  {analytics.total_users > 0 
                    ? Math.round(analytics.messages_this_month / analytics.total_users)
                    : 0
                  }
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}