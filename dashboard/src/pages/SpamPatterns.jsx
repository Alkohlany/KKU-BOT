import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useConfirm } from '../components/ConfirmDialog';
import { useToast } from '../components/ToastContext';

export default function SpamPatterns() {
  const { confirm } = useConfirm();
  const { showToast } = useToast();
  const [patterns, setPatterns] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [content, setContent] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => { setPage(1); }, [search]);

  useEffect(() => {
    loadPatterns();
  }, [page, search]);

  const loadPatterns = async () => {
    try {
      const params = { page, limit: 50 };
      if (search) params.search = search;
      const data = await api.getSpamPatterns(params);
      const items = data.items || data;
      setPatterns(Array.isArray(items) ? items : []);
      setTotal(data.total || 0);
      setTotalPages(Math.max(1, Math.ceil((data.total || 0) / 50)));
    } catch (err) {
      console.error('Failed to load spam patterns:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async () => {
    if (!content.trim()) return;
    setSaving(true);
    try {
      await api.addSpamPattern({ content: content.trim() });
      setContent('');
      setShowModal(false);
      loadPatterns();
    } catch (err) {
      console.error('Failed to add pattern:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    const ok = await confirm('هل أنت متأكد من حذف هذا النمط؟');
    if (!ok) return;
    try {
      await api.deleteSpamPattern(id);
      setPatterns(patterns.filter((p) => p.id !== id));
      setTotal(total - 1);
      showToast('تم الحذف بنجاح', 'success');
    } catch (err) {
      console.error('Failed to delete pattern:', err);
      showToast('فشل الحذف', 'error');
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 20, color: '#888' }}>جاري تحميل البيانات...</div>;
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
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            إضافة نمط
          </button>
        </div>

        <div className="table-container desktop-only">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>النمط</th>
                <th>التاريخ</th>
                <th>إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {patterns.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td><strong>{item.content}</strong></td>
                  <td>{item.created_at}</td>
                  <td>
                    <button className="btn btn-secondary btn-sm" onClick={() => handleDelete(item.id)}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                      <span className="btn-text-desktop">حذف</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {patterns.length === 0 && (
            <div className="empty-state">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                <polyline points="22,6 12,13 2,6" />
              </svg>
              <h4>لا يوجد أنماط سبام</h4>
              <p>لم يتم إضافة أي أنماط بعد</p>
            </div>
          )}
        </div>

        <div className="mobile-cards" style={{ padding: '16px 24px' }}>
          {patterns.map((item) => (
            <div key={item.id} className="mobile-card">
              <div className="mobile-card-header">
                <strong>{item.content}</strong>
                <button className="btn btn-secondary btn-sm" onClick={() => handleDelete(item.id)}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                  حذف
                </button>
              </div>
              <div className="mobile-card-body">
                <div className="mobile-card-meta">
                  <span>التاريخ: {item.created_at}</span>
                </div>
              </div>
            </div>
          ))}
          {patterns.length === 0 && (
            <div className="empty-state">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                <polyline points="22,6 12,13 2,6" />
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
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn btn-secondary btn-sm">السابق</button>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="btn btn-secondary btn-sm">التالي</button>
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
                <textarea
                  className="form-input"
                  placeholder="اكتب نمط السبام..."
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-danger" onClick={handleAdd} disabled={saving || !content.trim()}>
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
