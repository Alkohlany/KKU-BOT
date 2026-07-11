import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useConfirm } from '../components/ConfirmDialog';
import { useToast } from '../components/ToastContext';
import ChannelGroupSelector from '../components/ChannelGroupSelector';
import FileUpload from '../components/FileUpload';

export default function ScheduledPosts() {
  const { confirm } = useConfirm();
  const { showToast } = useToast();
  const [posts, setPosts] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ content: '', scheduledTime: '', recurring: false, publish_to_channel: false, as_document: false });
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadFiles, setUploadFiles] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedChannels, setSelectedChannels] = useState([]);

  const [showEditModal, setShowEditModal] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [editForm, setEditForm] = useState({ content: '', scheduledTime: '', recurring: false, publish_to_channel: false, as_document: false });
  const [editUploadFile, setEditUploadFile] = useState(null);
  const [editUploadFiles, setEditUploadFiles] = useState([]);
  const [editExistingFiles, setEditExistingFiles] = useState([]);
  const [editRemovedExisting, setEditRemovedExisting] = useState([]);
  const [editSelectedChannels, setEditSelectedChannels] = useState([]);

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletingPostId, setDeletingPostId] = useState(null);

  const [enhancing, setEnhancing] = useState(false);

  useEffect(() => {
    loadPosts();
    const interval = setInterval(() => {
      loadPosts();
    }, 30000);
    return () => clearInterval(interval);
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

  const handleEnhance = async () => {
    if (!form.content) return;
    setEnhancing(true);
    try {
      const result = await api.post('/news/enhance', {
        content: form.content,
        title: ''
      });
      if (result && result.enhanced) {
        const enhanced = result.enhanced;
        setForm({ ...form, content: enhanced.enhanced_content || enhanced.content || form.content });
        showToast('تم تحسين المحتوى بنجاح', 'success');
      }
    } catch (err) {
      console.error('Failed to enhance:', err);
      showToast('فشل تحسين المحتوى', 'error');
    } finally {
      setEnhancing(false);
    }
  };

  const handleSave = async () => {
    if (!form.content || !form.scheduledTime) return;
    setSaving(true);
    try {
      let newItem;
      const allFiles = uploadFiles.length > 0 ? uploadFiles : (uploadFile ? [uploadFile] : []);
      if (allFiles.length > 0) {
        const formData = new FormData();
        formData.append('content', form.content);
        formData.append('schedule_time', form.scheduledTime);
        formData.append('is_recurring', form.recurring);
        formData.append('publish_to_channel', form.publish_to_channel);
        formData.append('as_document', form.as_document);
        if (form.title) formData.append('title', form.title);
        allFiles.forEach(f => formData.append('files', f));
        if (selectedChannels.length > 0) {
          formData.append('target_channels', JSON.stringify(selectedChannels));
        }
        newItem = await api.addScheduledPostWithFile(formData);
      } else {
        newItem = await api.addScheduledPost({
          content: form.content,
          schedule_time: form.scheduledTime,
          is_recurring: form.recurring,
          publish_to_channel: form.publish_to_channel,
          as_document: form.as_document,
          target_channels: selectedChannels.length > 0 ? JSON.stringify(selectedChannels) : null,
        });
      }
      setPosts([...posts, newItem]);
      setForm({ content: '', scheduledTime: '', recurring: false, publish_to_channel: false, as_document: false });
      setUploadFile(null);
      setUploadFiles([]);
      setSelectedChannels([]);
      setShowModal(false);
    } catch (err) {
      console.error('Failed to save scheduled post:', err);
    } finally {
      setSaving(false);
    }
  };

  const openEditModal = (item) => {
    setEditItem(item);
    setEditForm({
      content: item.content,
      scheduledTime: item.scheduledTime ? new Date(item.scheduledTime).toISOString().slice(0, 16) : '',
      recurring: item.recurring || false,
      publish_to_channel: item.publishToChannel || false,
      as_document: item.asDocument || false,
    });
    try {
      const targets = item.targetChannels ? JSON.parse(item.targetChannels) : [];
      setEditSelectedChannels(targets);
    } catch {
      setEditSelectedChannels([]);
    }
    setEditUploadFile(null);
    setEditUploadFiles([]);
    try {
      const fj = item.filesJson ? (typeof item.filesJson === 'string' ? JSON.parse(item.filesJson) : item.filesJson) : [];
      setEditExistingFiles(Array.isArray(fj) ? fj : []);
    } catch { setEditExistingFiles([]); }
    setEditRemovedExisting([]);
    setShowEditModal(true);
  };

  const handleEditSave = async () => {
    if (!editForm.content || !editForm.scheduledTime || !editItem) return;
    try {
      const scheduledDate = new Date(editForm.scheduledTime);
      const utcDate = new Date(scheduledDate.getTime() - (scheduledDate.getTimezoneOffset() * 60000));

      const allEditFiles = editUploadFiles.length > 0 ? editUploadFiles : (editUploadFile ? [editUploadFile] : []);
      if (allEditFiles.length > 0) {
        const formData = new FormData();
        formData.append('content', editForm.content);
        formData.append('schedule_time', utcDate.toISOString());
        formData.append('is_recurring', editForm.recurring);
        formData.append('publish_to_channel', editForm.publish_to_channel);
        formData.append('as_document', editForm.as_document);
        allEditFiles.forEach(f => formData.append('files', f));
        if (editSelectedChannels.length > 0) {
          formData.append('target_channels', JSON.stringify(editSelectedChannels));
        }
        formData.append('removed_existing', JSON.stringify(editRemovedExisting));
        await api.uploadWithProgress(`/scheduled-posts/${editItem.id}/upload`, formData, () => {}, 'PUT');
      } else {
        await api.updateScheduledPost(editItem.id, {
          content: editForm.content,
          schedule_time: utcDate.toISOString(),
          is_recurring: editForm.recurring,
          publish_to_channel: editForm.publish_to_channel,
          as_document: editForm.as_document,
          target_channels: editSelectedChannels.length > 0 ? JSON.stringify(editSelectedChannels) : null,
          removed_existing: JSON.stringify(editRemovedExisting),
        });
      }
      setShowEditModal(false);
      loadPosts();
      showToast('تم تعديل المنشور بنجاح', 'success');
    } catch (err) {
      console.error('Failed to edit scheduled post:', err);
      showToast('فشل تعديل المنشور', 'error');
    }
  };

  const handleDeletePost = (id) => {
    setDeletingPostId(id);
    setShowDeleteModal(true);
  };

  const handlePostResetPublish = async (id) => {
    setShowDeleteModal(false);
    try {
      await api.delete(`/scheduled-posts/${id}/channel`);
      setPosts(posts.map(p => p.id === id ? { ...p, isPublished: false } : p));
      showToast('تم حذف المنشور من القنوات بنجاح', 'success');
    } catch (err) {
      showToast('حدث خطأ أثناء الحذف', 'error');
    }
  };

  const handlePostPermanentDelete = async (id) => {
    setShowDeleteModal(false);
    const ok = await confirm('هل أنت متأكد من الحذف النهائي؟');
    if (!ok) return;
    try {
      await api.delete(`/scheduled-posts/${id}`);
      setPosts(posts.filter((p) => p.id !== id));
      showToast('تم حذف المنشور نهائياً', 'success');
    } catch (err) {
      showToast('حدث خطأ أثناء الحذف', 'error');
    }
  };

  const handleDeleteAll = async () => {
    const ok = await confirm('هل أنت متأكد من حذف جميع المنشورات المجدولة؟');
    if (!ok) return;
    try {
      await api.delete('/scheduled-posts');
      setPosts([]);
      showToast('تم حذف جميع المنشورات بنجاح', 'success');
    } catch (err) {
      showToast('حدث خطأ أثناء الحذف', 'error');
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
            <button className="btn btn-primary" onClick={() => { setForm({ content: '', scheduledTime: '', recurring: false, publish_to_channel: false, as_document: false }); setUploadFile(null); setUploadFiles([]); setSelectedChannels([]); setShowModal(true); }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              إضافة منشور جديد
            </button>
            <button className="btn btn-danger" onClick={handleDeleteAll}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
              حذف الكل
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
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {item.imageUrl && <span className="status-badge active">🖼️ صورة</span>}
                        {item.fileUrl && <span className="status-badge active">📎 ملف</span>}
                        {(item.imageUrl || item.fileUrl) && (
                          <span className="status-badge active">
                            {item.asDocument ? 'كمرفق' : 'عرض مباشر'}
                          </span>
                        )}
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
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                        {!item.isPublished && (
                          <button className="btn btn-outline btn-sm" onClick={() => openEditModal(item)}>
                            تعديل
                          </button>
                        )}
                        <button className="btn btn-danger btn-icon" onClick={() => handleDeletePost(item.id)}>
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
                    {(item.imageUrl || item.fileUrl) && (
                      <span className="status-badge active" style={{ fontSize: 11 }}>
                        {item.asDocument ? 'كمرفق' : 'عرض مباشر'}
                      </span>
                    )}
                  </div>
                </div>
                <div className="mobile-card-meta">
                  {!item.isPublished && (
                    <button className="btn btn-outline btn-sm" onClick={() => openEditModal(item)}>
                      تعديل
                    </button>
                  )}
                  <button className="btn btn-danger btn-sm" onClick={() => handleDeletePost(item.id)}>
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
                <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  المحتوى
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={handleEnhance}
                    disabled={enhancing || !form.content}
                    style={{ fontSize: 12, padding: '4px 12px' }}
                  >
                    {enhancing ? 'جاري التحسين...' : 'تحسين بالذكاء الاصطناعي'}
                  </button>
                </label>
                <textarea
                  className="form-input"
                  placeholder="اكتب محتوى المنشور هنا..."
                  value={form.content}
                  onChange={(e) => setForm({ ...form, content: e.target.value })}
                  style={{ minHeight: 150 }}
                />
              </div>
              <FileUpload
                files={uploadFiles}
                setFiles={(newFiles) => { setUploadFiles(newFiles); setUploadFile(newFiles[0] || null); }}
                asDocument={form.as_document}
                setAsDocument={(val) => setForm({ ...form, as_document: val })}
              />
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
                <ChannelGroupSelector
                  selected={selectedChannels}
                  onChange={setSelectedChannels}
                  label="اختر القنوات والجروبات للنشر"
                />
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

      {showEditModal && (
        <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>تعديل المنشور المجدول</h3>
              <button className="modal-close" onClick={() => setShowEditModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>المحتوى</label>
                <textarea
                  className="form-input"
                  placeholder="اكتب محتوى المنشور هنا..."
                  value={editForm.content}
                  onChange={(e) => setEditForm({ ...editForm, content: e.target.value })}
                  style={{ minHeight: 150 }}
                />
              </div>
              <FileUpload
                files={editUploadFiles}
                setFiles={(newFiles) => { setEditUploadFiles(newFiles); setEditUploadFile(newFiles[0] || null); }}
                asDocument={editForm.as_document}
                setAsDocument={(val) => setEditForm({ ...editForm, as_document: val })}
                existingFiles={editExistingFiles}
                onRemoveExisting={setEditRemovedExisting}
              />
              <div className="form-group">
                <label>وقت النشر</label>
                <input
                  type="datetime-local"
                  className="form-input"
                  value={editForm.scheduledTime}
                  onChange={(e) => setEditForm({ ...editForm, scheduledTime: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={editForm.recurring}
                    onChange={(e) => setEditForm({ ...editForm, recurring: e.target.checked })}
                    style={{ width: 18, height: 18 }}
                  />
                  منشور متكرر
                </label>
              </div>
              <div className="form-group">
                <ChannelGroupSelector
                  selected={editSelectedChannels}
                  onChange={setEditSelectedChannels}
                  label="اختر القنوات والجروبات للنشر"
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={handleEditSave} disabled={saving}>
                {saving ? 'جاري الحفظ...' : 'حفظ التعديلات'}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowEditModal(false)}>إلغاء</button>
            </div>
          </div>
        </div>
      )}

      {showDeleteModal && (
        <div className="modal-overlay" onClick={() => setShowDeleteModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 420 }}>
            <div className="modal-header">
              <h3>خيارات حذف المنشور</h3>
              <button className="modal-close" onClick={() => setShowDeleteModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: 14, color: 'var(--gray-600)', lineHeight: 1.6, marginBottom: 16 }}>
                ماذا تريد أن تفعل بهذا المنشور؟
              </p>
              <button
                className="btn btn-primary"
                style={{ width: '100%', marginBottom: 10, justifyContent: 'center' }}
                onClick={() => handlePostResetPublish(deletingPostId)}
              >
                حذف من القنوات فقط
              </button>
              <p style={{ fontSize: 12, color: 'var(--gray-500)', marginBottom: 16, textAlign: 'center' }}>
                حذف المنشور من القنوات مع الاحتفاظ به كمسودة
              </p>
              <button
                className="btn btn-danger"
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={() => handlePostPermanentDelete(deletingPostId)}
              >
                حذف نهائي
              </button>
              <p style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 8, textAlign: 'center' }}>
                حذف المنشور وجميع بياناته نهائياً
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}