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
    totalNews: 0,
  });
  const [trends, setTrends] = useState({
    users: { value: '0%', direction: 'up' },
    groups: { value: '0%', direction: 'up' },
    responses: { value: '0%', direction: 'up' },
    banned: { value: '0%', direction: 'up' },
    totalNews: { value: '0%', direction: 'up' },
  });
  const [weeklyData, setWeeklyData] = useState([]);
  const [pieData, setPieData] = useState([]);
  const [activities, setActivities] = useState([]);
  const [channels, setChannels] = useState([]);
  const [groupsList, setGroupsList] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [statsData, weeklyRes, activityData, channelsData] = await Promise.all([
        api.getStats(),
        api.get('/stats/weekly'),
        api.getActivityLog(),
        api.get('/channels'),
      ]);

      const users = statsData.users || 0;
      const groups = statsData.groups || 0;
      const responses = statsData.responses || 0;
      const banned = statsData.banned || 0;
      const totalNews = channelsData.reduce((sum, c) => sum + (c.postCount || 0), 0);

      setStats({ users, groups, responses, banned, totalNews });

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
        totalNews: calculateTrend(totalNews, Math.max(1, Math.floor(totalNews * 0.85))),
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
      const channelsList = channelsData.filter(c => c.type === 'channel');
      const groupsListData = channelsData.filter(c => c.type === 'group');
      setChannels(channelsList);
      setGroupsList(groupsListData);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const totalChannels = channels.filter(c => c.type === 'channel').length;
  const totalGroupsCount = groupsList.filter(g => g.type === 'group').length;
  const totalMembers = [...channels, ...groupsList].reduce((sum, g) => sum + (g.memberCount || 0), 0);
  const activeItems = [...channels, ...groupsList].filter(g => g.isActive).length;
  const inactiveItems = [...channels, ...groupsList].filter(g => !g.isActive).length;

  const allConnections = [
    ...channels,
    ...groupsList,
  ];

  const mostActive = allConnections
    .sort((a, b) => (b.postCount || 0) - (a.postCount || 0))
    .slice(0, 5);

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
        <StatsCard icon="users" value={`${totalMembers.toLocaleString()} عضو | ${stats.banned} محظور`} label="إجمالي المستخدمين" trend={trends.users.value} trendDir={trends.users.direction} color="green" />
        <StatsCard icon="newspaper" value={stats.totalNews} label="إجمالي المنشورات" trend={trends.totalNews.value} trendDir={trends.totalNews.direction} color="blue" />
        <StatsCard icon="users" value={`${allConnections.length} متصل (${totalChannels} قناة + ${totalGroupsCount} جروب)`} label="القنوات والجروبات المتصلة" trend={`${activeItems} نشط`} trendDir="up" color="orange" />
        <StatsCard icon="chat" value={stats.responses} label="الردود التلقائية" trend={trends.responses.value} trendDir={trends.responses.direction} color="green" />
      </div>

      <div className="grid-3">
        <div className="card">
          <div className="card-header">
            <h3>إحصائيات القنوات والجروبات</h3>
          </div>
          <div className="card-body">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: '#f8f9fa', borderRadius: 8 }}>
                <span style={{ color: '#666' }}>إجمالي القنوات</span>
                <span style={{ fontWeight: 700, color: '#1976D2' }}>{totalChannels}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: '#f8f9fa', borderRadius: 8 }}>
                <span style={{ color: '#666' }}>إجمالي الجروبات</span>
                <span style={{ fontWeight: 700, color: '#2E7D32' }}>{totalGroupsCount}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: '#f8f9fa', borderRadius: 8 }}>
                <span style={{ color: '#666' }}>إجمالي الأعضاء</span>
                <span style={{ fontWeight: 700, color: '#F57C00' }}>{totalMembers.toLocaleString()}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: '#f8f9fa', borderRadius: 8 }}>
                <span style={{ color: '#666' }}>نشط / غير نشط</span>
                <span>
                  <span style={{ fontWeight: 700, color: '#2E7D32' }}>{activeItems}</span>
                  <span style={{ color: '#999', margin: '0 6px' }}>/</span>
                  <span style={{ fontWeight: 700, color: '#D32F2F' }}>{inactiveItems}</span>
                </span>
              </div>
            </div>
          </div>
        </div>

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
          <h3>القنوات والجروبات المتصلة</h3>
          <span style={{ fontSize: 13, color: '#888' }}>{allConnections.length} متصل</span>
        </div>
        <div className="card-body">
          {allConnections.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'Tajawal', direction: 'rtl' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #eee', textAlign: 'right' }}>
                    <th style={{ padding: '10px 12px', fontWeight: 600, color: '#555' }}>الاسم</th>
                    <th style={{ padding: '10px 12px', fontWeight: 600, color: '#555' }}>النوع</th>
                    <th style={{ padding: '10px 12px', fontWeight: 600, color: '#555' }}>عدد الأعضاء</th>
                    <th style={{ padding: '10px 12px', fontWeight: 600, color: '#555' }}>المنشورات</th>
                    <th style={{ padding: '10px 12px', fontWeight: 600, color: '#555' }}>الحالة</th>
                  </tr>
                </thead>
                <tbody>
                  {allConnections.slice(0, 10).map((item, index) => (
                    <tr key={item.id || index} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{ padding: '10px 12px', fontWeight: 500 }}>
                        {item.title || `عنصر ${index + 1}`}
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{
                          padding: '2px 10px',
                          borderRadius: 12,
                          fontSize: 12,
                          fontWeight: 600,
                          background: item.type === 'channel' ? '#E3F2FD' : '#E8F5E9',
                          color: item.type === 'channel' ? '#1976D2' : '#2E7D32',
                        }}>
                          {item.type === 'channel' ? 'قناة' : 'جروب'}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', color: '#666' }}>
                        {(item.memberCount || 0).toLocaleString()}
                      </td>
                      <td style={{ padding: '10px 12px', color: '#666' }}>
                        {item.postCount || 0}
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                          fontSize: 13,
                          fontWeight: 500,
                          color: item.isActive ? '#2E7D32' : '#D32F2F',
                        }}>
                          <span style={{
                            width: 8,
                            height: 8,
                            borderRadius: '50%',
                            background: item.isActive ? '#2E7D32' : '#D32F2F',
                            display: 'inline-block',
                          }} />
                          {item.isActive ? 'نشط' : 'غير نشط'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: 20, color: '#888' }}>
              لا توجد قنوات أو جروبات متصلة
            </div>
          )}
        </div>
      </div>

      {mostActive.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3>الأكثر نشاطاً (حسب المنشورات)</h3>
          </div>
          <div className="card-body">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {mostActive.map((item, index) => (
                <div key={item.id || index} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', background: '#f8f9fa', borderRadius: 8 }}>
                  <span style={{ fontWeight: 700, color: '#999', minWidth: 24 }}>{index + 1}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600 }}>{item.title || `عنصر ${index + 1}`}</div>
                    <div style={{ fontSize: 12, color: '#888' }}>
                      {item.type === 'channel' ? 'قناة' : 'جروب'} • {(item.memberCount || 0).toLocaleString()} عضو
                    </div>
                  </div>
                  <span style={{ fontWeight: 700, color: '#1976D2' }}>{item.postCount || 0} منشور</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

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
