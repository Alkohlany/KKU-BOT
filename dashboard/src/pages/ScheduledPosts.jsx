import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useConfirm } from '../components/ConfirmDialog';
import { useToast } from '../components/ToastContext';
import ChannelGroupSelector from '../components/ChannelGroupSelector';

export default function ScheduledPosts() {
  const { confirm } = useConfirm();
  const { showToast } = useToast();
  const [posts, setPosts] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ content: '', scheduledTime: '', recurring: false, publish_to_channel: false, as_document: false });
  const [uploadFile, setUploadFile] = useState(null);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedChannels, setSelectedChannels] = useState([]);

  const [showEditModal, setShowEditModal] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [editForm, setEditForm] = useState({ content: '', scheduledTime: '', recurring: false, publish_to_channel: false, as_document: false });
  const [editUploadFile, setEditUploadFile] = useState(null);
  const [editSelectedChannels, setEditSelectedChannels] = useState([]);

  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteItem, setDeleteItem] = useState(null);
  const [deleteOptions, setDeleteOptions] = useState({
    fromChannels: false,
    fromGroups: false,
    deleteAll: false,
    permanent: false,
    channelIds: [],
    groupIds: []
  });

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
      if (uploadFile) {
        const formData = new FormData();
        formData.append('content', form.content);
        formData.append('schedule_time', form.scheduledTime);
        formData.append('is_recurring', form.recurring);
        formData.append('publish_to_channel', form.publish_to_channel);
        formData.append('as_document', form.as_document);
        if (form.title) formData.append('title', form.title);
        formData.append('file', uploadFile);
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
    setShowEditModal(true);
  };

  const handleEditSave = async () => {
    if (!editForm.content || !editForm.scheduledTime || !editItem) return;
    try {
      const scheduledDate = new Date(editForm.scheduledTime);
      const utcDate = new Date(scheduledDate.getTime() - (scheduledDate.getTimezoneOffset() * 60000));

      if (editUploadFile) {
        const formData = new FormData();
        formData.append('content', editForm.content);
        formData.append('schedule_time', utcDate.toISOString());
        formData.append('is_recurring', editForm.recurring);
        formData.append('publish_to_channel', editForm.publish_to_channel);
        formData.append('as_document', editForm.as_document);
        formData.append('file', editUploadFile);
        if (editSelectedChannels.length > 0) {
          formData.append('target_channels', JSON.stringify(editSelectedChannels));
        }
        await api.uploadWithProgress(`/scheduled-posts/${editItem.id}/upload`, formData, () => {});
      } else {
        await api.updateScheduledPost(editItem.id, {
          content: editForm.content,
          schedule_time: utcDate.toISOString(),
          is_recurring: editForm.recurring,
          publish_to_channel: editForm.publish_to_channel,
          as_document: editForm.as_document,
          target_channels: editSelectedChannels.length > 0 ? JSON.stringify(editSelectedChannels) : null,
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

  const openDeleteDialog = (item) => {
    setDeleteItem(item);
    setDeleteOptions({
      fromChannels: false,
      fromGroups: false,
      deleteAll: false,
      permanent: false,
      channelIds: [],
      groupIds: []
    });
    setShowDeleteDialog(true);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteItem) return;
    try {
      if (deleteOptions.deleteAll) {
        await api.delete('/scheduled-posts');
        setPosts([]);
        showToast('تم حذف جميع المنشورات بنجاح', 'success');
      } else {
        await api.delete(`/scheduled-posts/${deleteItem.id}`);
        setPosts(posts.filter((p) => p.id !== deleteItem.id));
        showToast('تم حذف المنشور بنجاح', 'success');
      }
      setShowDeleteDialog(false);
      setDeleteItem(null);
    } catch (err) {
      console.error('Failed to delete scheduled post:', err);
      showToast('فشل حذف المنشور', 'error');
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
            <button className="btn btn-primary" onClick={() => { setForm({ content: '', scheduledTime: '', recurring: false, publish_to_channel: false, as_document: false }); setUploadFile(null); setSelectedChannels([]); setShowModal(true); }}>
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
                        <button className="btn btn-danger btn-icon" onClick={() => openDeleteDialog(item)}>
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
                  <button className="btn btn-danger btn-sm" onClick={() => openDeleteDialog(item)}>
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
              <div className="form-group">
                <label>الملف المرفق (اختياري)</label>
                <input
                  type="file"
                  className="form-input"
                  onChange={(e) => setEditUploadFile(e.target.files[0])}
                />
                {editUploadFile && (
                  <small style={{ color: 'var(--gray-500)', marginTop: 4, display: 'block' }}>
                    {editUploadFile.name}
                  </small>
                )}
              </div>
              <div className="form-group">
                <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 14 }}>
                  <input
                    type="checkbox"
                    checked={editForm.as_document}
                    onChange={(e) => setEditForm({ ...editForm, as_document: e.target.checked })}
                    style={{ width: 18, height: 18 }}
                  />
                  إرسال كملف مرفق (بدلاً من العرض المباشر)
                </label>
                <small style={{ color: 'var(--gray-400)', marginTop: 4, display: 'block', fontSize: 12 }}>
                  عند التفعيل، سيتم إرسال الملف كمرفق قابل للتحميل بدلاً من عرضه مباشرة
                </small>
              </div>
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

      {showDeleteDialog && (
        <div className="modal-overlay" onClick={() => setShowDeleteDialog(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 480 }}>
            <div className="modal-header">
              <h3>حذف المنشور المجدول</h3>
              <button className="modal-close" onClick={() => setShowDeleteDialog(false)}>✕</button>
            </div>
            <div className="modal-body">
              <p style={{ marginBottom: 16, color: 'var(--gray-600)', fontSize: 14 }}>
                هل أنت متأكد من حذف هذا المنشور المجدول؟
              </p>
              <div style={{ background: 'var(--gray-50)', padding: 12, borderRadius: 8, marginBottom: 16 }}>
                <p style={{ fontSize: 13, color: 'var(--gray-700)', margin: 0 }}>
                  {deleteItem?.content?.substring(0, 100)}...
                </p>
                <p style={{ fontSize: 12, color: 'var(--gray-400)', margin: '4px 0 0' }}>
                  الوقت: {formatDateTime(deleteItem?.scheduledTime)}
                </p>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 14 }}>
                  <input
                    type="checkbox"
                    checked={deleteOptions.fromChannels}
                    onChange={(e) => setDeleteOptions({ ...deleteOptions, fromChannels: e.target.checked })}
                    style={{ width: 18, height: 18 }}
                  />
                  حذف من القنوات
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 14 }}>
                  <input
                    type="checkbox"
                    checked={deleteOptions.fromGroups}
                    onChange={(e) => setDeleteOptions({ ...deleteOptions, fromGroups: e.target.checked })}
                    style={{ width: 18, height: 18 }}
                  />
                  حذف من القروبات
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 14 }}>
                  <input
                    type="checkbox"
                    checked={deleteOptions.deleteAll}
                    onChange={(e) => setDeleteOptions({ ...deleteOptions, deleteAll: e.target.checked })}
                    style={{ width: 18, height: 18 }}
                  />
                  حذف جميع المنشورات المجدولة
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 14 }}>
                  <input
                    type="checkbox"
                    checked={deleteOptions.permanent}
                    onChange={(e) => setDeleteOptions({ ...deleteOptions, permanent: e.target.checked })}
                    style={{ width: 18, height: 18 }}
                  />
                  حذف نهائي (لا يمكن التراجع)
                </label>
              </div>
              {deleteOptions.permanent && (
                <div style={{ marginTop: 12, padding: 10, background: 'var(--danger-bg, #fff5f5)', borderRadius: 8, border: '1px solid var(--danger, #e53e3e)' }}>
                  <p style={{ fontSize: 12, color: 'var(--danger, #e53e3e)', margin: 0 }}>
                    ⚠️ هذا الإجراء لا يمكن التراجع عنه. سيتم حذف المنشور نهائياً من قاعدة البيانات.
                  </p>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-danger" onClick={handleDeleteConfirm}>
                {deleteOptions.deleteAll ? 'حذف الكل' : 'حذف'}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowDeleteDialog(false)}>إلغاء</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}