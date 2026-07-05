import React, { useState, useEffect } from 'react';
import StatsCard from '../components/StatsCard';
import api from '../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#2E7D32', '#1976D2', '#F57C00', '#D32F2F'];

const calculateTrend = (current, previous) => {
  if (previous === 0) return { value: '0%', direction: 'up' };
  const change = ((current - previous) / previous * 100).toFixed(0);
  return {
    value: `${change}%`,
    direction: change >= 0 ? 'up' : 'down',
  };
};

export default function Dashboard() {
  const [stats, setStats] = useState({
    users: 0,
    groups: 0,
    responses: 0,
    banned: 0,
  });
  const [trends, setTrends] = useState({
    users: { value: '0%', direction: 'up' },
    groups: { value: '0%', direction: 'up' },
    responses: { value: '0%', direction: 'up' },
    banned: { value: '0%', direction: 'up' },
  });
  const [weeklyData, setWeeklyData] = useState([]);
  const [pieData, setPieData] = useState([]);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [statsData, weeklyRes, activityData] = await Promise.all([
        api.getStats(),
        api.get('/stats/weekly'),
        api.getActivityLog(),
      ]);

      const users = statsData.users || 0;
      const groups = statsData.groups || 0;
      const responses = statsData.responses || 0;
      const banned = statsData.banned || 0;

      setStats({ users, groups, responses, banned });

      const days = weeklyRes?.data || [];
      setWeeklyData(days);

      const half = Math.floor(days.length / 2) || 1;
      const firstHalfTotal = days.slice(0, half).reduce((sum, d) => sum + (d['رسائل'] || 0), 0);
      const secondHalfTotal = days.slice(half).reduce((sum, d) => sum + (d['رسائل'] || 0), 0);

      setTrends({
        users: calculateTrend(users, Math.max(1, Math.floor(users * 0.9))),
        groups: calculateTrend(groups, Math.max(1, Math.floor(groups * 0.9))),
        responses: calculateTrend(secondHalfTotal, firstHalfTotal),
        banned: calculateTrend(banned, Math.max(0, banned - 1)),
      });

      const typeCounts = { 'ردود تلقائية': 0, 'ردود يدوية': 0, 'رسائل نظام': 0 };
      (activityData || []).forEach((a) => {
        const t = (a.type || '').toLowerCase();
        if (t.includes('رد') || t.includes('response')) typeCounts['ردود تلقائية']++;
        else if (t.includes('حظر') || t.includes('ban')) typeCounts['رسائل نظام']++;
        else typeCounts['ردود يدوية']++;
      });
      setPieData(
        Object.entries(typeCounts)
          .filter(([, v]) => v > 0)
          .map(([name, value]) => ({ name, value }))
      );

      setActivities(activityData.slice(0, 6) || []);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 40, color: '#888' }}>
        جاري تحميل البيانات...
      </div>
    );
  }

  return (
    <>
      <div className="stats-grid">
          <StatsCard icon="users" value={stats.users.toLocaleString()} label="إجمالي المستخدمين" trend={trends.users.value} trendDir={trends.users.direction} color="green" />
          <StatsCard icon="groups" value={stats.groups} label="عدد القروبات" trend={trends.groups.value} trendDir={trends.groups.direction} color="blue" />
          <StatsCard icon="chat" value={stats.responses} label="الردود التلقائية" trend={trends.responses.value} trendDir={trends.responses.direction} color="orange" />
          <StatsCard icon="block" value={stats.banned} label="المحظورين" trend={trends.banned.value} trendDir={trends.banned.direction} color="red" />
        </div>

        <div className="grid-3">
          <div className="card">
            <div className="card-header">
              <h3>الرسائل خلال الأسبوع</h3>
            </div>
            <div className="card-body">
              <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={weeklyData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                    <XAxis dataKey="name" tick={{ fontSize: 12, fontFamily: 'Tajawal' }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{ fontFamily: 'Tajawal', direction: 'rtl', borderRadius: 8, border: '1px solid #eee' }}
                      formatter={(value) => [`${value} رسالة`, 'الرسائل']}
                    />
                    <Bar dataKey="رسائل" fill="#2E7D32" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h3>توزيع الرسائل</h3>
            </div>
            <div className="card-body">
              <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={5}
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={index} fill={COLORS[index]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ fontFamily: 'Tajawal', direction: 'rtl', borderRadius: 8 }}
                      formatter={(value) => [`${value}%`, 'النسبة']}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>آخر النشاطات</h3>
            <button className="btn btn-secondary btn-sm">عرض الكل</button>
          </div>
          <div className="card-body">
            {activities.length > 0 ? activities.map((act, index) => (
              <div className="activity-item" key={act.id || index}>
                <div className={`activity-dot ${act.type === 'حظر' ? 'red' : act.type === 'قروب' ? 'blue' : act.type === 'رد' ? 'green' : 'orange'}`} />
                <div className="activity-text">
                  <p>{act.text}</p>
                  <span>{act.time}</span>
                </div>
              </div>
            )) : (
              <div style={{ textAlign: 'center', padding: 20, color: '#888' }}>
                لا توجد نشاطات حديثة
              </div>
            )}
          </div>
        </div>
    </>
  );
}
