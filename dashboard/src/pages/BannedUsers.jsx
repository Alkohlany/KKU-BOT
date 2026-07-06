import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useConfirm } from '../components/ConfirmDialog';
import { useToast } from '../components/ToastContext';

export default function BannedUsers() {
  const { confirm } = useConfirm();
  const { showToast } = useToast();
  const [banned, setBanned] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ username: '', reason: '' });
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadBannedUsers();
  }, []);

  const loadBannedUsers = async () => {
    try {
      const data = await api.getBannedUsers();
      setBanned(data);
    } catch (err) {
      console.error('Failed to load banned users:', err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = banned.filter(
    (b) => b.username?.includes(search) || b.reason?.includes(search)
  );

  const handleBan = async () => {
    if (!form.username || !form.reason) return;
    setSaving(true);
    try {
      const newItem = await api.banUser(form);
      setBanned([newItem, ...banned]);
      setForm({ username: '', reason: '' });
      setShowModal(false);
    } catch (err) {
      console.error('Failed to ban user:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleUnban = async (id) => {
    const ok = await confirm('هل أنت متأكد من إلغاء الحظر؟');
    if (!ok) return;
    try {
      await api.unbanUser(id);
      setBanned(banned.filter((b) => b.id !== id));
      showToast('تم إلغاء الحظر بنجاح', 'success');
    } catch (err) {
      console.error('Failed to unban user:', err);
      showToast('فشل إلغاء الحظر', 'error');
    }
  };

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
            <div className="search-box">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                type="text"
                placeholder="بحث في المحظورين..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <button className="btn btn-danger" onClick={() => setShowModal(true)}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
              </svg>
              حظر مستخدم
            </button>
          </div>

          {/* Desktop Table */}
          <div className="table-container desktop-only">
            <table>
              <thead>
                <tr>
                  <th>اسم المستخدم</th>
                  <th>سبب الحظر</th>
                  <th>تاريخ الحظر</th>
                  <th> المحظور بواسطة</th>
                  <th>إجراءات</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr key={item.id}>
                    <td><strong>{item.username}</strong></td>
                    <td>{item.reason}</td>
                    <td>{item.bannedDate}</td>
                    <td>{item.bannedBy}</td>
                    <td>
                      <button className="btn btn-secondary btn-sm" title="إلغاء الحظر" onClick={() => handleUnban(item.id)}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="12" r="10" />
                          <line x1="15" y1="9" x2="9" y2="15" />
                          <line x1="9" y1="9" x2="15" y2="15" />
                        </svg>
                        <span className="btn-text-desktop">إلغاء الحظر</span>
                        <span className="btn-text-mobile">إلغاء</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && (
              <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
                </svg>
                <h4>لا يوجد محظورين</h4>
                <p>لم يتم حظر أي مستخدم بعد</p>
              </div>
            )}
          </div>

          {/* Mobile Cards */}
          <div className="mobile-cards" style={{ padding: '16px 24px' }}>
            {filtered.map((item) => (
              <div key={item.id} className="mobile-card">
                <div className="mobile-card-header">
                  <strong>{item.username}</strong>
                  <button className="btn btn-secondary btn-sm" onClick={() => handleUnban(item.id)}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="15" y1="9" x2="9" y2="15" />
                      <line x1="9" y1="9" x2="15" y2="15" />
                    </svg>
                    إلغاء
                  </button>
                </div>
                <div className="mobile-card-body">
                  <div className="mobile-card-meta">
                    <span>سبب الحظر: {item.reason}</span>
                    <span>تاريخ الحظر: {item.bannedDate}</span>
                    <span>بواسطة: {item.bannedBy}</span>
                  </div>
                </div>
              </div>
            ))}
            {filtered.length === 0 && (
              <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
                </svg>
                <h4>لا يوجد محظورين</h4>
                <p>لم يتم حظر أي مستخدم بعد</p>
              </div>
            )}
          </div>
        </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>حظر مستخدم جديد</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>اسم المستخدم</label>
                <input
                  className="form-input"
                  placeholder="@username"
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>سبب الحظر</label>
                <textarea
                  className="form-input"
                  placeholder="اكتب سبب الحظر..."
                  value={form.reason}
                  onChange={(e) => setForm({ ...form, reason: e.target.value })}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-danger" onClick={handleBan} disabled={saving}>
                {saving ? 'جاري الحظر...' : 'حظر'}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>إلغاء</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
