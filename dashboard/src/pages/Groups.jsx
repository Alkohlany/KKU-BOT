import React, { useState, useEffect } from 'react';
import api from '../services/api';

export default function Groups() {
  const [groups, setGroups] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ chat_id: '', title: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadGroups();
  }, []);

  const loadGroups = async () => {
    try {
      const data = await api.getGroups();
      setGroups(data);
    } catch (err) {
      console.error('Failed to load groups:', err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = groups.filter((g) => g.name?.includes(search));

  const toggleGroup = async (id) => {
    const group = groups.find(g => g.id === id);
    if (group) {
      try {
        await api.toggleGroup(id, !group.enabled);
        setGroups(groups.map((g) => g.id === id ? { ...g, enabled: !g.enabled } : g));
      } catch (err) {
        console.error('Failed to toggle group:', err);
      }
    }
  };

  const handleAddGroup = async () => {
    if (!form.chat_id) return;
    setSaving(true);
    try {
      const result = await api.addGroup({ chat_id: parseInt(form.chat_id), title: form.title || null });
      if (result.error) {
        alert(result.error);
      } else {
        setGroups([...groups, result]);
        setForm({ chat_id: '', title: '' });
        setShowModal(false);
      }
    } catch (err) {
      console.error('Failed to add group:', err);
    } finally {
      setSaving(false);
    }
  };

  const totalMembers = groups.reduce((sum, g) => sum + (g.members || 0), 0);
  const activeGroups = groups.filter((g) => g.enabled).length;

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 20, color: '#888' }}>
        جاري تحميل البيانات...
      </div>
    );
  }

  return (
    <>
      <div className="stats-grid" style={{ marginBottom: 24 }}>
          <div className="stats-card green">
            <div className="stats-card-header">
              <div className="stats-card-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                </svg>
              </div>
            </div>
            <div className="stats-card-value">{groups.length}</div>
            <div className="stats-card-label">إجمالي القروبات</div>
          </div>
          <div className="stats-card blue">
            <div className="stats-card-header">
              <div className="stats-card-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                </svg>
              </div>
            </div>
            <div className="stats-card-value">{activeGroups}</div>
            <div className="stats-card-label">قروبات نشطة</div>
          </div>
          <div className="stats-card orange">
            <div className="stats-card-header">
              <div className="stats-card-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
              </div>
            </div>
            <div className="stats-card-value">{totalMembers.toLocaleString()}</div>
            <div className="stats-card-label">إجمالي الأعضاء</div>
          </div>
        </div>

        <div className="card">
          <div className="card-header" style={{ flexWrap: 'wrap', gap: 12 }}>
            <div className="search-box">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                type="text"
                placeholder="بحث في القروبات..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <button className="btn btn-primary" onClick={() => { setForm({ chat_id: '', title: '' }); setShowModal(true); }}>
              + إضافة قروب
            </button>
          </div>

          {/* Desktop Table */}
          <div className="table-container desktop-only">
            <table>
              <thead>
                <tr>
                  <th>اسم القروب</th>
                  <th>Chat ID</th>
                  <th>تاريخ الإضافة</th>
                  <th>الحالة</th>
                  <th>إجراءات</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((group) => (
                  <tr key={group.id}>
                    <td><strong>{group.name}</strong></td>
                    <td><code style={{ fontSize: 12 }}>{group.chat_id}</code></td>
                    <td>{group.joinDate || '-'}</td>
                    <td>
                      <span className={`status-badge ${group.enabled ? 'active' : 'inactive'}`}>
                        {group.enabled ? 'نشط' : 'معطل'}
                      </span>
                    </td>
                    <td>
                      <label className="toggle-switch">
                        <input type="checkbox" checked={group.enabled} onChange={() => toggleGroup(group.id)} />
                        <span className="toggle-slider" />
                      </label>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && (
              <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                </svg>
                <h4>لا توجد قروبات</h4>
                <p>أضف قروب يدوياً أو أرسل /registergroup داخل القروب</p>
              </div>
            )}
          </div>

          {/* Mobile Cards */}
          <div className="mobile-cards" style={{ padding: '16px 24px' }}>
            {filtered.map((group) => (
              <div key={group.id} className="mobile-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <strong style={{ fontSize: 14, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{group.name}</strong>
                  <code style={{ fontSize: 11, color: 'var(--gray-500)' }}>{group.chat_id}</code>
                </div>
                <label className="toggle-switch" style={{ marginLeft: 12 }}>
                  <input type="checkbox" checked={group.enabled} onChange={() => toggleGroup(group.id)} />
                  <span className="toggle-slider" />
                </label>
              </div>
            ))}
            {filtered.length === 0 && (
              <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                </svg>
                <h4>لا توجد قروبات</h4>
                <p>أضف قروب يدوياً أو أرسل /registergroup داخل القروب</p>
              </div>
            )}
          </div>
        </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>إضافة قروب جديد</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Chat ID</label>
                <input
                  className="form-input"
                  placeholder="مثال: -1001234567890"
                  value={form.chat_id}
                  onChange={(e) => setForm({ ...form, chat_id: e.target.value })}
                />
                <small style={{ color: 'var(--gray-500)', fontSize: 12 }}>
                  احصل على Chat ID من @userinfobot أو @getidsbot داخل القروب
                </small>
              </div>
              <div className="form-group">
                <label>اسم القروب (اختياري)</label>
                <input
                  className="form-input"
                  placeholder="مثال: قروب هندسة الحاسب"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={handleAddGroup} disabled={saving}>
                {saving ? 'جاري الإضافة...' : 'إضافة'}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>إلغاء</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
