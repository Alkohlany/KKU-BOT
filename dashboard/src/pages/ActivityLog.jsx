import React, { useState, useEffect } from 'react';
import api from '../services/api';

export default function ActivityLog() {
  const [activities, setActivities] = useState([]);
  const [typeFilter, setTypeFilter] = useState('all');
  const [dateFilter, setDateFilter] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadActivities();
  }, []);

  const loadActivities = async () => {
    try {
      const data = await api.getActivityLog();
      setActivities(data);
    } catch (err) {
      console.error('Failed to load activities:', err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = activities.filter((a) => {
    if (typeFilter !== 'all' && a.type !== typeFilter) return false;
    if (dateFilter && !a.time?.startsWith(dateFilter)) return false;
    return true;
  });

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 20, color: '#888' }}>
        جاري تحميل البيانات...
      </div>
    );
  }

  return (
    <>
      <div className="card">
          <div className="card-header" style={{ flexWrap: 'wrap', gap: 12 }}>
            <div className="filter-bar" style={{ flex: 1, marginBottom: 0 }}>
              <select className="form-input" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
                <option value="all">جميع الأنواع</option>
                <option value="رد">ردود</option>
                <option value="قروب">قروبات</option>
                <option value="حظر">حظر</option>
                <option value="إعدادات">إعدادات</option>
              </select>
              <input
                type="date"
                className="form-input"
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
              />
            </div>
          </div>

          {/* Desktop Table */}
          <div className="table-container desktop-only">
            <table>
              <thead>
                <tr>
                  <th>النوع</th>
                  <th>النشاط</th>
                  <th>المستخدم</th>
                  <th>التاريخ والوقت</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <span className={`status-badge ${item.type === 'حظر' ? 'inactive' : 'active'}`}>
                        {item.type}
                      </span>
                    </td>
                    <td>{item.text}</td>
                    <td>{item.user}</td>
                    <td>{item.time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && (
              <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                <h4>لا توجد نشاطات</h4>
                <p>لم يتم تسجيل أي نشاطات بعد</p>
              </div>
            )}
          </div>

          {/* Mobile Cards */}
          <div className="mobile-cards" style={{ padding: '16px 24px' }}>
            {filtered.map((item) => (
              <div key={item.id} className="mobile-card">
                <div className="mobile-card-header">
                  <span className={`status-badge ${item.type === 'حظر' ? 'inactive' : 'active'}`}>
                    {item.type}
                  </span>
                  <span style={{ fontSize: 12, color: 'var(--gray-500)' }}>{item.time}</span>
                </div>
                <div className="mobile-card-body">
                  <p>{item.text}</p>
                  <div className="mobile-card-meta">
                    <span>المستخدم: {item.user}</span>
                  </div>
                </div>
              </div>
            ))}
            {filtered.length === 0 && (
              <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                <h4>لا توجد نشاطات</h4>
                <p>لم يتم تسجيل أي نشاطات بعد</p>
              </div>
            )}
          </div>
        </div>
    </>
  );
}
