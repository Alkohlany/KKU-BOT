import React, { useState, useEffect } from 'react';
import api from '../services/api';

export default function ScheduledPosts() {
  const [posts, setPosts] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ content: '', scheduledTime: '', recurring: false, publish_to_channel: false });
  const [uploadFile, setUploadFile] = useState(null);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadPosts();
  }, []);

  const loadPosts = async () => {
    try {
      const data = await api.getScheduledPosts();
      setPosts(data);
    } catch (err) {
      console.error('Failed to load scheduled posts:', err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = posts.filter(
    (p) => p.content?.includes(search) || p.title?.includes(search)
  );

  const handleSave = async () => {
    if (!form.content || !form.scheduledTime) return;
    setSaving(true);
    try {
      let newItem;
      if (uploadFile) {
        const formData = new FormData();
        formData.append('content', form.content);
        formData.append('schedule_time', form.scheduledTime);
        formData.append('is_recurring', form.recurring);
        formData.append('publish_to_channel', form.publish_to_channel);
        if (form.title) formData.append('title', form.title);
        formData.append('file', uploadFile);
        newItem = await api.addScheduledPostWithFile(formData);
      } else {
        newItem = await api.addScheduledPost({
          content: form.content,
          schedule_time: form.scheduledTime,
          is_recurring: form.recurring,
          publish_to_channel: form.publish_to_channel,
        });
      }
      setPosts([...posts, newItem]);
      setForm({ content: '', scheduledTime: '', recurring: false, publish_to_channel: false });
      setUploadFile(null);
      setShowModal(false);
    } catch (err) {
      console.error('Failed to save scheduled post:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('هل أنت متأكد من حذف هذا المنشور المجدول؟')) return;
    try {
      await api.deleteScheduledPost(id);
      setPosts(posts.filter((p) => p.id !== id));
    } catch (err) {
      console.error('Failed to delete scheduled post:', err);
    }
  };

  const formatDateTime = (dt) => {
    if (!dt) return '-';
    const d = new Date(dt);
    return d.toLocaleDateString('ar-SA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const isPast = (item) => item.isPublished === true;

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 40, color: '#888' }}>
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
                placeholder="بحث في المنشورات..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <button className="btn btn-primary" onClick={() => { setForm({ content: '', scheduledTime: '', recurring: false, publish_to_channel: false }); setUploadFile(null); setShowModal(true); }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              إضافة منشور جديد
            </button>
          </div>

          {/* Desktop Table */}
          <div className="table-container desktop-only">
            <table>
              <thead>
                <tr>
                  <th>المحتوى</th>
                  <th>المرفقات</th>
                  <th>وقت النشر</th>
                  <th>متكرر</th>
                  <th>الحالة</th>
                  <th>إجراءات</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr key={item.id}>
                    <td style={{ maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.content?.substring(0, 80)}...
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 4 }}>
                        {item.imageUrl && <span className="status-badge active">🖼️ صورة</span>}
                        {item.fileUrl && <span className="status-badge active">📎 ملف</span>}
                        {!item.imageUrl && !item.fileUrl && <span style={{ color: 'var(--gray-400)' }}>-</span>}
                      </div>
                    </td>
                    <td>{formatDateTime(item.scheduledTime)}</td>
                    <td>
                      <span className={`status-badge ${item.recurring ? 'active' : 'inactive'}`}>
                        {item.recurring ? 'متكرر' : 'مرة واحدة'}
                      </span>
                    </td>
                    <td>
                      <span className={`status-badge ${item.isPublished ? 'active' : 'inactive'}`}>
                        {item.isPublished ? 'منشور' : 'قيد الانتظار'}
                      </span>
                    </td>
                    <td>
                      <button className="btn btn-danger btn-icon" onClick={() => handleDelete(item.id)}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && (
              <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
                <h4>لا توجد منشورات مجدولة</h4>
                <p>ابدأ بإضافة منشورات مجدولة للبوت</p>
              </div>
            )}
          </div>

          {/* Mobile Cards */}
          <div className="mobile-cards">
            {filtered.map((item) => (
              <div key={item.id} className="mobile-card">
                <div className="mobile-card-header">
                  <strong>{item.title || item.content?.substring(0, 30)}...</strong>
                  <span className={`status-badge ${item.isPublished ? 'active' : 'inactive'}`}>
                    {item.isPublished ? 'منشور' : 'قيد الانتظار'}
                  </span>
                </div>
                <div className="mobile-card-body">
                  {item.imageUrl && (
                    <img src={item.imageUrl} alt="" style={{ width: '100%', height: 120, borderRadius: 8, objectFit: 'cover', marginBottom: 8 }} />
                  )}
                  <p style={{ fontSize: 13, color: 'var(--gray-600)', marginBottom: 8 }}>
                    {item.content?.substring(0, 100)}...
                  </p>
                  <div className="mobile-card-meta">
                    <span>📅 {formatDateTime(item.scheduledTime)}</span>
                    <span className={`status-badge ${item.isPublished ? 'active' : 'inactive'}`} style={{ fontSize: 11 }}>
                      {item.isPublished ? '✅ منشور' : '⏱️ قيد الانتظار'}
                    </span>
                    {item.imageUrl && <span className="status-badge active" style={{ fontSize: 11 }}>🖼️ صورة</span>}
                    {item.fileUrl && <span className="status-badge active" style={{ fontSize: 11 }}>📎 ملف</span>}
                  </div>
                </div>
                <div className="mobile-card-meta">
                  <button className="btn btn-danger btn-sm" onClick={() => handleDelete(item.id)}>
                    حذف
                  </button>
                </div>
              </div>
            ))}
            {filtered.length === 0 && (
              <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
                <h4>لا توجد منشورات مجدولة</h4>
                <p>ابدأ بإضافة منشورات مجدولة للبوت</p>
              </div>
            )}
          </div>
        </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>إضافة منشور جديد</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>المحتوى</label>
                <textarea
                  className="form-input"
                  placeholder="اكتب محتوى المنشور هنا..."
                  value={form.content}
                  onChange={(e) => setForm({ ...form, content: e.target.value })}
                  style={{ minHeight: 150 }}
                />
              </div>
              <div className="form-group">
                <label>الملف المرفق (اختياري)</label>
                <input
                  type="file"
                  className="form-input"
                  onChange={(e) => setUploadFile(e.target.files[0])}
                />
                {uploadFile && (
                  <small style={{ color: 'var(--gray-500)', marginTop: 4, display: 'block' }}>
                    {uploadFile.name}
                  </small>
                )}
              </div>
              <div className="form-group">
                <label>وقت النشر</label>
                <input
                  type="datetime-local"
                  className="form-input"
                  value={form.scheduledTime}
                  onChange={(e) => setForm({ ...form, scheduledTime: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={form.recurring}
                    onChange={(e) => setForm({ ...form, recurring: e.target.checked })}
                    style={{ width: 18, height: 18 }}
                  />
                  منشور متكرر
                </label>
              </div>
              <div className="form-group">
                <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={form.publish_to_channel}
                    onChange={(e) => setForm({ ...form, publish_to_channel: e.target.checked })}
                    style={{ width: 18, height: 18 }}
                  />
                  نشر في القناة الرسمية أيضاً
                </label>
                <small style={{ color: 'var(--gray-400)', marginTop: 4, display: 'block', fontSize: 12 }}>
                  عند التفعيل، سيتم نشر المنشور في القروبات والقناة الرسمية معاً
                </small>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? 'جاري الحفظ...' : 'إضافة'}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>إلغاء</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
