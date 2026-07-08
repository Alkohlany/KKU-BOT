import React, { useState, useEffect } from 'react';
import StatsCard from '../components/StatsCard';
import api from '../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#2E7D32', '#1976D2', '#F57C00', '#D32F2F', '#9C27B0'];

export default function Dashboard() {
  const [stats, setStats] = useState({
    users: 0,
    groups: 0,
    responses: 0,
    banned: 0,
    totalNews: 0,
  });

  const [weeklyData, setWeeklyData] = useState([]);
  const [pieData, setPieData] = useState([]);
  const [activities, setActivities] = useState([]);
  const [channels, setChannels] = useState([]);
  const [groupsList, setGroupsList] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(() => {
      loadData();
    }, 30000);
    return () => clearInterval(interval);
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

      const typeCounts = { 'ردود تلقائية': 0, 'ردود يدوية': 0, 'رسائل نظام': 0, 'إجراءات أدمن': 0 };
      (activityData || []).forEach((a) => {
        const t = (a.type || '').toLowerCase();
        if (t.includes('auto_response') || t.includes('response')) typeCounts['ردود تلقائية']++;
        else if (t.includes('ban') || t.includes('rate_limit') || t.includes('spam') || t.includes('system')) typeCounts['رسائل نظام']++;
        else if (t.includes('add_') || t.includes('delete_') || t.includes('edit_') || t.includes('broadcast')) typeCounts['إجراءات أدمن']++;
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
        <StatsCard
          icon="users"
          value={totalMembers.toLocaleString()}
          label="إجمالي المستخدمين"
          color="green"
          subStats={[`${stats.banned} محظور`, `${totalMembers - stats.banned} نشط`]}
        />
        <StatsCard
          icon="newspaper"
          value={stats.totalNews}
          label="إجمالي المنشورات"
          color="blue"
        />
        <StatsCard
          icon="link"
          value={allConnections.length}
          label="القنوات والجروبات المتصلة"
          color="orange"
          subStats={[`${activeItems} نشط`, `${inactiveItems} غير نشط`]}
        />
        <StatsCard
          icon="chat"
          value={stats.responses}
          label="الردود التلقائية"
          color="green"
        />
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
