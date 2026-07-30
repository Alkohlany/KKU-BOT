import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useConfirm } from '../components/ConfirmDialog';
import { useToast } from '../components/ToastContext';

export default function SpamPatterns() {
  const { confirm } = useConfirm();
  const { showToast } = useToast();
  const [patterns, setPatterns] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ content: '', created_at: '' });
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => { setPage(1); }, [search]);

  useEffect(() => {
    loadSpamPatterns();
  }, [page, search]);

  const loadSpamPatterns = async () => {
    try {
      const data = await api.get(`/spam?page=${page}&limit=5&search=${encodeURIComponent(search)}`);
      const items = data.items || data;
      setPatterns(Array.isArray(items) ? items : []);
      setTotal(data.total || 0);
      setTotalPages(Math.max(1, Math.ceil((data.total || 0) / 5)));
    } catch (err) {
      console.error('Failed to load spam patterns:', err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = patterns;

  const handleAdd = async () => {
    if (!form.content || !form.created_at) return;
    setSaving(true);
    try {
      const newItem = await api.addSpamPattern(form);
      setPatterns([newItem, ...patterns]);
      setForm({ content: '', created_at: '' });
      setShowModal(false);
    } catch (err) {
      console.error('Failed to add spam pattern:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    const ok = await confirm('هل أنت متأكد من الحذف؟');
    if (!ok) return;
    try {
      await api.deleteSpamPattern(id);
      setPatterns(patterns.filter((b) => b.id !== id));
      showToast('تم الحذف بنجاح', 'success');
    } catch (err) {
      console.error('Failed to delete spam pattern:', err);
      showToast('فشل الحذف', 'error');
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
                placeholder="بحث في أنماط السبام..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <button className="btn btn-danger" onClick={() => setShowModal(true)}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
              </svg>
              إضافة نمط
            </button>
          </div>

          {/* Desktop Table */}
          <div className="table-container desktop-only">
            <table>
              <thead>
                <tr>
                  <th>النمط</th>
                  <th>التاريخ</th>
                  <th>إجراءات</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr key={item.id}>
                    <td><strong>{item.content}</strong></td>
                    <td>{item.created_at}</td>
                    <td>
                      <button className="btn btn-secondary btn-sm" title="حذف" onClick={() => handleDelete(item.id)}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="12" r="10" />
                          <line x1="15" y1="9" x2="9" y2="15" />
                          <line x1="9" y1="9" x2="15" y2="15" />
                        </svg>
                        <span className="btn-text-desktop">حذف</span>
                        <span className="btn-text-mobile">حذف</span>
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
                <h4>لا يوجد أنماط سبام</h4>
                <p>لم يتم إضافة أي أنماط بعد</p>
              </div>
            )}
          </div>

          {/* Mobile Cards */}
          <div className="mobile-cards" style={{ padding: '16px 24px' }}>
            {filtered.map((item) => (
              <div key={item.id} className="mobile-card">
                <div className="mobile-card-header">
                  <strong>{item.content}</strong>
                  <button className="btn btn-secondary btn-sm" onClick={() => handleDelete(item.id)}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="15" y1="9" x2="9" y2="15" />
                      <line x1="9" y1="9" x2="15" y2="15" />
                    </svg>
                    حذف
                  </button>
                </div>
                <div className="mobile-card-body">
                  <div className="mobile-card-meta">
                    <span>النمط: {item.content}</span>
                    <span>التاريخ: {item.created_at}</span>
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
                <h4>لا يوجد أنماط سبام</h4>
                <p>لم يتم إضافة أي أنماط بعد</p>
              </div>
            )}
          </div>
        </div>

        {totalPages > 1 && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 16, padding: '12px 16px', background: 'var(--bg-card)', borderTop: '1px solid var(--gray-200)' }}>
            <div style={{ fontSize: 13, color: 'var(--gray-600)' }}>
              الصفحة {page} من {totalPages} ({total} إجمالي)
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                className="btn btn-secondary btn-sm">السابق</button>
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                className="btn btn-secondary btn-sm">التالي</button>
            </div>
          </div>
        )}

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>إضافة نمط سبام جديد</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>النمط</label>
                <input
                  className="form-input"
                  placeholder="أدخل النمط..."
                  value={form.content}
                  onChange={(e) => setForm({ ...form, content: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>النمط</label>
                <textarea
                  className="form-input"
                  placeholder="أدخل نمط السبام..."
                  value={form.created_at}
                  onChange={(e) => setForm({ ...form, created_at: e.target.value })}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-danger" onClick={handleAdd} disabled={saving}>
                {saving ? 'جاري الإضافة...' : 'إضافة'}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>إضافة</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
