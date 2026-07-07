import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useConfirm } from '../components/ConfirmDialog';
import { useToast } from '../components/ToastContext';

export default function News() {
  const { confirm } = useConfirm();
  const { showToast } = useToast();
  const [news, setNews] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ title: '', content: '', as_document: false });
  const [uploadFile, setUploadFile] = useState(null);
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [publishItem, setPublishItem] = useState(null);
  const [publishToChannel, setPublishToChannel] = useState(false);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [publishProgress, setPublishProgress] = useState(null);

  useEffect(() => {
    loadNews();
  }, []);

  const loadNews = async () => {
    try {
      const data = await api.getNews();
      setNews(data);
    } catch (err) {
      console.error('Failed to load news:', err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = news.filter(
    (n) => n.title?.includes(search) || n.content?.includes(search)
  );

  const handleSave = async () => {
    if (!form.title || !form.content) return;
    setSaving(true);
    setUploadProgress(0);
    try {
      let newItem;
      if (uploadFile) {
        const config = await api.getUploadConfig();

        const formData = new FormData();
        formData.append('file', uploadFile);
        formData.append('api_key', config.api_key);
        formData.append('timestamp', config.timestamp);
        formData.append('signature', config.signature);
        formData.append('folder', config.folder);

        const result = await api.uploadToCloudinary(config.cloud_name, formData, (percent) => {
          setUploadProgress(percent);
        });

        newItem = await api.addNews({
          title: form.title,
          content: form.content,
          file_url: result.secure_url,
          file_name: uploadFile.name,
          as_document: form.as_document,
        });
      } else {
        newItem = await api.addNews(form);
      }
      setNews([...news, newItem]);
      setForm({ title: '', content: '', as_document: false });
      setUploadFile(null);
      setShowModal(false);
      showToast('تم إضافة الخبر بنجاح', 'success');
    } catch (err) {
      console.error('Failed to save news:', err);
      showToast('فشل حفظ الخبر', 'error');
    } finally {
      setSaving(false);
      setUploadProgress(null);
    }
  };

  const handlePublish = async () => {
    if (!publishItem) return;
    setPublishing(publishItem.id);
    setPublishProgress(0);
    try {
      const publishPromise = api.publishNews(publishItem.id, { publish_to_channel: publishToChannel });
      const progressInterval = setInterval(() => {
        setPublishProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 300);

      await publishPromise;
      clearInterval(progressInterval);
      setPublishProgress(100);
      setNews(news.map((n) => n.id === publishItem.id ? { ...n, published: true } : n));
      setShowPublishModal(false);
      setPublishItem(null);
      setPublishToChannel(false);
    } catch (err) {
      console.error('Failed to publish news:', err);
    } finally {
      setTimeout(() => {
        setPublishing(null);
        setPublishProgress(null);
      }, 500);
    }
  };

  const handleDelete = async (id) => {
    const ok = await confirm('هل أنت متأكد من حذف هذا الخبر؟');
    if (!ok) return;
    try {
      await api.deleteNews(id);
      setNews(news.filter((n) => n.id !== id));
      showToast('تم حذف الخبر بنجاح', 'success');
    } catch (err) {
      console.error('Failed to delete news:', err);
      showToast('فشل حذف الخبر', 'error');
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
          <div className="card-header" style={{ flexWrap: 'wrap', gap: 12 }}>
            <div className="search-box">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                type="text"
                placeholder="بحث في الأخبار..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <button className="btn btn-primary" onClick={() => { setForm({ title: '', content: '', as_document: false }); setUploadFile(null); setShowModal(true); }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              إضافة خبر جديد
            </button>
          </div>

          {/* Desktop Table */}
          <div className="table-container desktop-only">
            <table>
              <thead>
                <tr>
                  <th>العنوان</th>
                  <th>المحتوى</th>
                  <th>الصورة</th>
                  <th>الملف</th>
                  <th>طريقة الإرسال</th>
                  <th>الحالة</th>
                  <th>إجراءات</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr key={item.id}>
                    <td><strong>{item.title}</strong></td>
                    <td style={{ maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.content?.substring(0, 80)}...
                    </td>
                    <td>
                      {item.imageUrl ? (
                        <img src={item.imageUrl} alt="" style={{ width: 40, height: 40, borderRadius: 8, objectFit: 'cover' }} />
                      ) : (
                        <span style={{ color: 'var(--gray-400)' }}>-</span>
                      )}
                    </td>
                    <td>
                      {item.fileUrl ? (
                        <span className="status-badge active">مرفق</span>
                      ) : (
                        <span style={{ color: 'var(--gray-400)' }}>-</span>
                      )}
                    </td>
                    <td style={{ fontSize: 13, color: 'var(--gray-500)' }}>
                      {item.fileUrl || item.imageUrl ? (item.asDocument ? 'كمرفق' : 'عرض مباشر') : '-'}
                    </td>
                    <td>
                      <span className={`status-badge ${item.published ? 'active' : 'inactive'}`}>
                        {item.published ? 'منشور' : 'مسودة'}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        {!item.published && (
                          publishing === item.id ? (
                            <div style={{ flex: 1 }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2, fontSize: 11 }}>
                                <span>نشر...</span>
                                <span>{publishProgress}%</span>
                              </div>
                              <div style={{ width: 80, height: 4, background: 'var(--gray-200)', borderRadius: 2, overflow: 'hidden' }}>
                                <div style={{ width: `${publishProgress}%`, height: '100%', background: publishProgress === 100 ? 'var(--success)' : 'var(--primary)', borderRadius: 2, transition: 'width 0.3s' }} />
                              </div>
                            </div>
                          ) : (
                            <button
                              className="btn btn-primary btn-icon"
                              onClick={() => { setPublishItem(item); setPublishToChannel(item.publishToChannel || false); setShowPublishModal(true); }}
                              title="نشر في جميع القروبات"
                            >
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <line x1="22" y1="2" x2="11" y2="13" />
                                <polygon points="22 2 15 22 11 13 2 9 22 2" />
                              </svg>
                            </button>
                          )
                        )}
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
                  <path d="M19 20H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v1m2 13a2 2 0 0 1-2-2V7m2 13a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-2" />
                </svg>
                <h4>لا توجد أخبار</h4>
                <p>ابدأ بإضافة أخبار للبوت</p>
              </div>
            )}
          </div>

          {/* Mobile Cards */}
          <div className="mobile-cards">
            {filtered.map((item) => (
              <div key={item.id} className="mobile-card">
                <div className="mobile-card-header">
                  <strong>{item.title}</strong>
                  <span className={`status-badge ${item.published ? 'active' : 'inactive'}`}>
                    {item.published ? 'منشور' : 'مسودة'}
                  </span>
                </div>
                <div className="mobile-card-body">
                  {item.imageUrl && (
                    <img src={item.imageUrl} alt="" style={{ width: '100%', height: 120, borderRadius: 8, objectFit: 'cover', marginBottom: 8 }} />
                  )}
                  {!item.imageUrl && item.fileUrl && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', background: 'var(--gray-100)', borderRadius: 8, marginBottom: 8 }}>
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                      </svg>
                      <span style={{ fontSize: 12, color: 'var(--gray-600)' }}>📎 ملف مرفق</span>
                    </div>
                  )}
                  {(item.fileUrl || item.imageUrl) && (
                    <p style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 4, marginBottom: 8 }}>
                      طريقة الإرسال: {item.asDocument ? 'كمرفق' : 'عرض مباشر'}
                    </p>
                  )}
                  <p style={{ fontSize: 13, color: 'var(--gray-600)', marginBottom: 0 }}>
                    {item.content?.substring(0, 100)}...
                  </p>
                </div>
                <div className="mobile-card-meta">
                  {!item.published && (
                    publishing === item.id ? (
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2, fontSize: 11 }}>
                          <span>نشر...</span>
                          <span>{publishProgress}%</span>
                        </div>
                        <div style={{ width: '100%', height: 4, background: 'var(--gray-200)', borderRadius: 2, overflow: 'hidden' }}>
                          <div style={{ width: `${publishProgress}%`, height: '100%', background: publishProgress === 100 ? 'var(--success)' : 'var(--primary)', borderRadius: 2, transition: 'width 0.3s' }} />
                        </div>
                      </div>
                    ) : (
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => { setPublishItem(item); setPublishToChannel(item.publishToChannel || false); setShowPublishModal(true); }}
                      >
                        نشر
                      </button>
                    )
                  )}
                  <button className="btn btn-danger btn-sm" onClick={() => handleDelete(item.id)}>
                    حذف
                  </button>
                </div>
              </div>
            ))}
            {filtered.length === 0 && (
              <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M19 20H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v1m2 13a2 2 0 0 1-2-2V7m2 13a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-2" />
                </svg>
                <h4>لا توجد أخبار</h4>
                <p>ابدأ بإضافة أخبار للبوت</p>
              </div>
            )}
          </div>
        </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>إضافة خبر جديد</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>العنوان</label>
                <input
                  className="form-input"
                  placeholder="عنوان الخبر"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>المحتوى</label>
                <textarea
                  className="form-input"
                  placeholder="محتوى الخبر..."
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
            <div className="modal-footer">
              {uploadProgress !== null && (
                <div style={{ width: '100%', marginBottom: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 13 }}>
                    <span>جاري رفع الملف...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div style={{ width: '100%', height: 8, background: 'var(--gray-200)', borderRadius: 4, overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${uploadProgress}%`,
                        height: '100%',
                        background: uploadProgress === 100 ? 'var(--success)' : 'var(--primary)',
                        borderRadius: 4,
                        transition: 'width 0.3s ease',
                      }}
                    />
                  </div>
                </div>
              )}
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? 'جاري الحفظ...' : 'إضافة'}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>إلغاء</button>
            </div>
          </div>
        </div>
      )}

      {/* Publish Modal */}
      {showPublishModal && (
        <div className="modal-overlay" onClick={() => { setShowPublishModal(false); setPublishItem(null); }}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 420 }}>
            <div className="modal-header">
              <h3>نشر الخبر</h3>
              <button className="modal-close" onClick={() => { setShowPublishModal(false); setPublishItem(null); }}>✕</button>
            </div>
            <div className="modal-body">
              <p style={{ marginBottom: 16, color: 'var(--gray-600)', fontSize: 14 }}>
                هل أنت متأكد من نشر هذا الخبر؟
              </p>
              <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', padding: '10px 0', fontSize: 14 }}>
                <input
                  type="checkbox"
                  checked={publishToChannel}
                  onChange={(e) => setPublishToChannel(e.target.checked)}
                  style={{ width: 18, height: 18 }}
                />
                نشر في القناة الرسمية أيضاً
              </label>
              <p style={{ marginTop: 8, fontSize: 12, color: 'var(--gray-400)' }}>
                عند تفعيل هذا الخيار، سيتم نشر الخبر في القروبات والقناة الرسمية معاً
              </p>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={handlePublish} disabled={publishing !== null}>
                {publishing === publishItem?.id ? 'جاري النشر...' : 'تأكيد النشر'}
              </button>
              <button className="btn btn-secondary" onClick={() => { setShowPublishModal(false); setPublishItem(null); }}>إلغاء</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
