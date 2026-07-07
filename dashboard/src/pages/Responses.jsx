import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useConfirm } from '../components/ConfirmDialog';
import { useToast } from '../components/ToastContext';

export default function Responses() {
  const { confirm } = useConfirm();
  const { showToast } = useToast();
  const [responses, setResponses] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [form, setForm] = useState({ keyword: '', response: '', file: null, file_url: '', file_type: '', as_document: false });
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    try {
      const data = await api.getResponses();
      setResponses(data);
    } catch (err) {
      console.error('Failed to load:', err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = responses.filter((r) => {
    return r.keyword?.includes(search) || r.response?.includes(search);
  });

  const handleSave = async () => {
    if (!form.keyword || !form.response) return;
    setSaving(true);
    try {
      if (editItem && editItem.id) {
        if (form.file) {
          const formData = new FormData();
          formData.append('keyword', form.keyword);
          formData.append('response', form.response);
          formData.append('file', form.file);
          formData.append('as_document', form.as_document);
          const updated = await api.updateResponseWithFileProgress(editItem.id, formData, setUploadProgress);
          setResponses(responses.map((r) => r.id === editItem.id ? updated : r));
        } else {
          const payload = { keyword: form.keyword, response: form.response, as_document: form.as_document };
          if (form.file_url !== editItem.file_url) {
            payload.file_url = form.file_url || null;
            payload.file_type = form.file_type || null;
          }
          const updated = await api.updateResponse(editItem.id, payload);
          setResponses(responses.map((r) => r.id === editItem.id ? updated : r));
        }
      } else {
        if (form.file) {
          const formData = new FormData();
          formData.append('keyword', form.keyword);
          formData.append('response', form.response);
          formData.append('file', form.file);
          formData.append('as_document', form.as_document);
          const newItem = await api.addResponseWithFileProgress(formData, setUploadProgress);
          setResponses([...responses, newItem]);
        } else {
          const newItem = await api.addResponse(form);
          setResponses([...responses, newItem]);
        }
      }
      setForm({ keyword: '', response: '', file: null, file_url: '', file_type: '', as_document: false });
      setEditItem(null);
      setShowModal(false);
    } catch (err) {
      console.error('Failed to save response:', err);
    } finally {
      setSaving(false);
      setUploadProgress(null);
    }
  };

  const handleEdit = (item) => {
    setEditItem(item);
    setForm({ keyword: item.keyword, response: item.response || '', file: null, file_url: item.file_url || '', file_type: item.file_type || '', as_document: item.as_document || false });
    setShowModal(true);
  };

  const handleDelete = async (id) => {
    if (!id) return;
    const ok = await confirm('هل أنت متأكد من حذف هذا الرد؟');
    if (!ok) return;
    try {
      await api.deleteResponse(id);
      setResponses(responses.filter((r) => r.id !== id));
      showToast('تم حذف الرد بنجاح', 'success');
    } catch (err) {
      console.error('Failed to delete response:', err);
      showToast('فشل حذف الرد', 'error');
    }
  };

  const handleDeleteAll = async () => {
    if (responses.length === 0) return;
    const ok = await confirm(`هل أنت متأكد من حذف جميع الردود (${responses.length})؟`);
    if (!ok) return;
    try {
      await api.deleteAllResponses();
      setResponses([]);
      showToast('تم حذف جميع الردود بنجاح', 'success');
    } catch (err) {
      console.error('Failed to delete all responses:', err);
      showToast('فشل حذف جميع الردود', 'error');
    }
  };

  const toggleEnabled = async (item) => {
    if (!item.id) return;
    try {
      await api.updateResponse(item.id, { enabled: !item.enabled });
      setResponses(responses.map((r) =>
        r.id === item.id ? { ...r, enabled: !r.enabled } : r
      ));
    } catch (err) {
      console.error('Failed to toggle response:', err);
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
      <div className="card">
          <div className="card-header">
            <div className="search-box">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                type="text"
                placeholder="بحث في الردود..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              {responses.length > 0 && (
                <button className="btn btn-danger" onClick={handleDeleteAll}>
                  🗑 حذف الكل ({responses.length})
                </button>
              )}
              <button className="btn btn-primary" onClick={() => { setEditItem(null); setForm({ keyword: '', response: '', file: null, file_url: '', file_type: '', as_document: false }); setShowModal(true); }}>
                + إضافة رد جديد
              </button>
            </div>
          </div>

          {/* Desktop Table */}
          <div className="table-container desktop-only">
            <table>
              <thead>
                <tr>
                  <th>الكلمة المفتاحية</th>
                  <th>الرد</th>
                  <th>المرفق</th>
                  <th>طريقة الإرسال</th>
                  <th>الحالة</th>
                  <th>إجراءات</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr key={item.id}>
                    <td><strong>{item.keyword}</strong></td>
                    <td style={{ maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.response}
                    </td>
                    <td style={{ fontSize: 13, color: 'var(--gray-500)' }}>
                      {item.file_url ? (
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                          </svg>
                          {item.file_type === 'photo' ? 'صورة' : item.file_type === 'video' ? 'فيديو' : 'ملف'}
                        </span>
                      ) : '-'}
                    </td>
                    <td style={{ fontSize: 13, color: 'var(--gray-500)' }}>
                      {item.file_url ? (item.as_document ? 'كمرفق' : 'عرض مباشر') : '-'}
                    </td>
                    <td>
                      <label className="toggle-switch">
                        <input
                          type="checkbox"
                          checked={item.enabled}
                          onChange={() => toggleEnabled(item)}
                        />
                        <span className="toggle-slider" />
                      </label>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button className="btn btn-secondary btn-icon" onClick={() => handleEdit(item)}>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                          </svg>
                        </button>
                        <button className="btn btn-danger btn-icon" onClick={() => handleDelete(item.id)}>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && (
              <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
                <h4>لا توجد ردود</h4>
                <p>اضغط على "إضافة رد جديد" لإضافة رد</p>
              </div>
            )}
          </div>

          {/* Mobile Cards */}
          <div className="mobile-cards">
            {filtered.map((item) => (
              <div key={item.id} className="mobile-card">
                <div className="mobile-card-header">
                  <strong>{item.keyword}</strong>
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={item.enabled}
                      onChange={() => toggleEnabled(item)}
                    />
                    <span className="toggle-slider" />
                  </label>
                </div>
                <div className="mobile-card-body">
                  <p>{item.response}</p>
                  {item.file_url && (
                    <p style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 4 }}>
                      📎 {item.file_type === 'photo' ? 'صورة' : item.file_type === 'video' ? 'فيديو' : 'ملف'}
                      {item.as_document ? ' (كمرفق)' : ' (عرض مباشر)'}
                    </p>
                  )}
                </div>
                <div className="mobile-card-meta">
                  <button className="btn btn-secondary btn-sm" onClick={() => handleEdit(item)}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                    </svg>
                    تعديل
                  </button>
                  <button className="btn btn-danger btn-sm" onClick={() => handleDelete(item.id)}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="3 6 5 6 21 6" />
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                    حذف
                  </button>
                </div>
              </div>
            ))}
            {filtered.length === 0 && (
              <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
                <h4>لا توجد ردود</h4>
                <p>اضغط على "إضافة رد جديد" لإضافة رد</p>
              </div>
            )}
          </div>
        </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editItem ? 'تعديل رد' : 'إضافة رد جديد'}</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>الكلمة المفتاحية</label>
                <input
                  className="form-input"
                  placeholder="مثال: مواعيد, جدول, امتحانات..."
                  value={form.keyword}
                  onChange={(e) => setForm({ ...form, keyword: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>الرد</label>
                <textarea
                  className="form-input"
                  placeholder="اكتب نص الرد هنا..."
                  value={form.response}
                  onChange={(e) => setForm({ ...form, response: e.target.value })}
                  style={{ minHeight: 200 }}
                />
              </div>
              <div className="form-group">
                <label>الملف المرفق (اختياري)</label>
                <input
                  type="file"
                  accept=".jpg,.jpeg,.png,.gif,.webp,.mp4,.avi,.mov,.mkv,.pdf,.doc,.docx"
                  className="form-input"
                  onChange={(e) => setForm({ ...form, file: e.target.files[0] || null })}
                />
                {form.file && (
                  <small style={{ color: 'var(--gray-500)', marginTop: 4, display: 'block' }}>
                    {form.file.name}
                  </small>
                )}
                {editItem && editItem.file_url && !form.file && (
                  <small style={{ color: 'var(--primary)', marginTop: 4, display: 'block' }}>
                    📎 يوجد ملف مرفق حالياً
                  </small>
                )}
              </div>
              <div className="form-group">
                <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 14 }}>
                  <input
                    type="checkbox"
                    checked={form.as_document}
                    onChange={(e) => setForm({ ...form, as_document: e.target.checked })}
                    style={{ width: 18, height: 18 }}
                  />
                  إرسال كملف مرفق (بدلاً من العرض المباشر)
                </label>
                <small style={{ color: 'var(--gray-400)', marginTop: 4, display: 'block', fontSize: 12 }}>
                  عند التفعيل، سيتم إرسال الملف كمرفق قابل للتحميل بدلاً من عرضه مباشرة
                </small>
              </div>
            </div>
            {uploadProgress !== null && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ height: 6, background: 'var(--gray-200)', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${uploadProgress}%`, background: 'var(--primary)', borderRadius: 3, transition: 'width 0.3s ease' }} />
                </div>
                <p style={{ fontSize: 11, color: 'var(--gray-500)', marginTop: 4, textAlign: 'center' }}>{uploadProgress}%</p>
              </div>
            )}
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? 'جاري الحفظ...' : (editItem ? 'حفظ التعديلات' : 'إضافة')}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>إلغاء</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
