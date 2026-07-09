import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useConfirm } from '../components/ConfirmDialog';
import { useToast } from '../components/ToastContext';
import ChannelGroupSelector from '../components/ChannelGroupSelector';

export default function News() {
  const { confirm } = useConfirm();
  const { showToast } = useToast();
  const [news, setNews] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);

  const [showRelinkModal, setShowRelinkModal] = useState(false);
  const [form, setForm] = useState({ content: '', as_document: false });
  const [editForm, setEditForm] = useState({ content: '', as_document: false });
  const [editItem, setEditItem] = useState(null);

  const [uploadFile, setUploadFile] = useState(null);
  const [editUploadFile, setEditUploadFile] = useState(null);

  const [aiKeywords, setAiKeywords] = useState([]);
  const [aiQuestions, setAiQuestions] = useState([]);
  const [selectedKeywords, setSelectedKeywords] = useState([]);
  const [selectedQuestions, setSelectedQuestions] = useState([]);
  const [uploadProgress, setUploadProgress] = useState(null);

  const [showAiPanel, setShowAiPanel] = useState(false);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [enhancingContent, setEnhancingContent] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [relinkItem, setRelinkItem] = useState(null);

  const [selectedChannels, setSelectedChannels] = useState([]);
  const [editSelectedChannels, setEditSelectedChannels] = useState([]);

  useEffect(() => {
    loadNews();
    const interval = setInterval(() => {
      loadNews();
    }, 30000);
    return () => clearInterval(interval);
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
    (n) => n.content?.includes(search)
  );

  const handleEnhance = async () => {
    if (!form.content) {
      showToast('يرجى كتابة المحتوى أولاً', 'error');
      return;
    }
    setEnhancingContent(true);
    try {
      const result = await api.post('/news/enhance', {
        content: form.content,
        title: ''
      });
      setForm({ ...form, content: result.enhanced?.enhanced_content || result.enhanced?.content || form.content });
      showToast('تم تحسين المحتوى بنجاح', 'success');
    } catch (err) {
      console.error('Failed to enhance content:', err);
      showToast('فشل تحسين المحتوى', 'error');
    } finally {
      setEnhancingContent(false);
    }
  };

  const handleGenerateAI = async () => {
    if (!form.content) {
      showToast('يرجى كتابة المحتوى أولاً', 'error');
      return;
    }
    setGenerating(true);
    try {
      const result = await api.analyzeNews({ title: '', content: form.content });
      setAiKeywords(result.keywords || []);
      setAiQuestions(result.questions || []);
      setSelectedKeywords([]);
      setSelectedQuestions([]);
      setShowAiPanel(true);
    } catch (err) {
      console.error('Failed to generate AI content:', err);
      showToast('فشل توليد المحتوى بالذكاء الاصطناعي', 'error');
    } finally {
      setGenerating(false);
    }
  };

  const toggleKeyword = (kw) => {
    setSelectedKeywords(prev =>
      prev.includes(kw) ? prev.filter(k => k !== kw) : [...prev, kw]
    );
  };

  const toggleQuestion = (q) => {
    setSelectedQuestions(prev =>
      prev.includes(q) ? prev.filter(item => item !== q) : [...prev, q]
    );
  };

  const handleSave = async () => {
    if (!form.content) return;
    setSaving(true);
    setUploadProgress(0);
    try {
      let newItem;
      if (uploadFile) {
        const formData = new FormData();
        formData.append('title', '');
        formData.append('content', form.content);
        formData.append('file', uploadFile);
        formData.append('as_document', form.as_document);
        formData.append('target_channels', JSON.stringify(selectedChannels));
        formData.append('selected_keywords', JSON.stringify(selectedKeywords));
        formData.append('selected_questions', JSON.stringify(selectedQuestions));
        newItem = await api.uploadWithProgress('/news/upload', formData, (percent) => {
          setUploadProgress(percent);
        });
      } else {
        newItem = await api.addNews({ ...form, title: '', target_channels: JSON.stringify(selectedChannels) });
      }
      setNews([...news, newItem]);
      setForm({ content: '', as_document: false });
      setUploadFile(null);
      setSelectedChannels([]);
      setShowModal(false);
      setShowAiPanel(false);
      setAiKeywords([]);
      setAiQuestions([]);
      setSelectedKeywords([]);
      setSelectedQuestions([]);
      showToast('تم إضافة المنشور بنجاح', 'success');
    } catch (err) {
      console.error('Failed to save news:', err);
      showToast('فشل حفظ المنشور', 'error');
    } finally {
      setSaving(false);
      setUploadProgress(null);
    }
  };

  const handleEditSave = async () => {
    if (!editForm.content || !editItem) return;
    setSaving(true);
    try {
      if (editUploadFile) {
        const formData = new FormData();
        formData.append('title', '');
        formData.append('content', editForm.content);
        formData.append('as_document', editForm.as_document);
        formData.append('target_channels', JSON.stringify(editSelectedChannels));
        formData.append('file', editUploadFile);
        await api.uploadWithProgress(`/news/${editItem.id}/upload`, formData, () => {});
      } else {
        await api.put(`/news/${editItem.id}`, { ...editForm, title: '', target_channels: JSON.stringify(editSelectedChannels) });
      }
      setNews(news.map(n => n.id === editItem.id ? { 
        ...n, 
        content: editForm.content, 
        as_document: editForm.as_document,
      } : n));
      setShowEditModal(false);
      setEditItem(null);
      setEditUploadFile(null);
      showToast('تم تعديل المنشور بنجاح', 'success');
    } catch (err) {
      console.error('Failed to edit news:', err);
      showToast('فشل تعديل المنشور', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handlePublishDirect = async (item) => {
    try {
      await api.post(`/news/${item.id}/publish`);
      setNews(news.map((n) => n.id === item.id ? { ...n, published: true } : n));
      showToast('تم نشر المنشور بنجاح', 'success');
    } catch (err) {
      console.error('Failed to publish news:', err);
      showToast('فشل نشر المنشور', 'error');
    }
  };

  const handleDelete = async (id) => {
    const ok = await confirm('هل أنت متأكد من حذف هذا المنشور؟ سيتم حذفه من القنوات أيضاً');
    if (!ok) return;
    try {
      await api.delete(`/news/${id}`);
      setNews(news.filter((n) => n.id !== id));
      showToast('تم حذف المنشور بنجاح', 'success');
    } catch (err) {
      console.error('Failed to delete news:', err);
      showToast('فشل حذف المنشور', 'error');
    }
  };

  const handleDeleteAll = async () => {
    const ok = await confirm('هل أنت متأكد من حذف جميع المنشورات؟ هذا الإجراء لا يمكن التراجع عنه.');
    if (!ok) return;
    try {
      await api.delete('/news');
      setNews([]);
      showToast('تم حذف جميع المنشورات بنجاح', 'success');
    } catch (err) {
      console.error('Failed to delete all news:', err);
      showToast('فشل حذف جميع المنشورات', 'error');
    }
  };

  const handleRelink = async () => {
    if (!relinkItem) return;
    try {
      const result = await api.post(`/news/${relinkItem.id}/relink`, {
        keywords: selectedKeywords,
        questions: selectedQuestions,
      });
      setNews(news.map(n => n.id === relinkItem.id ? { ...n, keywords: result.keywords, questions: result.questions } : n));
      setShowRelinkModal(false);
      setRelinkItem(null);
      setSelectedKeywords([]);
      setSelectedQuestions([]);
      showToast('تم ربط المنشور بالقاموس بنجاح', 'success');
    } catch (err) {
      console.error('Failed to relink:', err);
      showToast('فشل إعادة الربط', 'error');
    }
  };

  const handleRelinkGenerate = async () => {
    if (!relinkItem) return;
    setGenerating(true);
    try {
      const result = await api.analyzeNews({ title: '', content: relinkItem.content });
      setAiKeywords(result.keywords || []);
      setAiQuestions(result.questions || []);
      setSelectedKeywords(relinkItem.keywords || []);
      setSelectedQuestions(relinkItem.questions || []);
    } catch (err) {
      showToast('فشل توليد المحتوى', 'error');
    } finally {
      setGenerating(false);
    }
  };

  const openEditModal = (item) => {
    setEditItem(item);
    setEditForm({ 
      content: item.content, 
      as_document: item.as_document || false,
    });
    setEditSelectedChannels(item.target_channels ? (typeof item.target_channels === 'string' ? JSON.parse(item.target_channels) : item.target_channels) : []);
    setEditUploadFile(null);
    setShowEditModal(true);
  };


  const openRelinkModal = async (item) => {
    setRelinkItem(item);
    setSelectedKeywords(item.keywords || []);
    setSelectedQuestions(item.questions || []);
    setAiKeywords(item.keywords || []);
    setAiQuestions(item.questions || []);
    setShowRelinkModal(true);
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
              placeholder="بحث في المنشورات..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-danger" onClick={handleDeleteAll}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
              حذف الكل
            </button>
            <button className="btn btn-primary" onClick={() => { setForm({ content: '', as_document: false }); setUploadFile(null); setSelectedChannels([]); setShowModal(true); }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              إضافة منشور جديد
            </button>
          </div>
        </div>

        <div className="table-container desktop-only">
          <table>
            <thead>
              <tr>
                <th>المحتوى</th>
                <th>الحالة</th>
                <th>مكان النشر</th>
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
                    <span className={`status-badge ${item.published ? 'active' : 'inactive'}`}>
                      {item.published ? 'منشور' : 'مسودة'}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {(item.publish_to_channel || item.publishToChannel) && (
                        <span className="status-badge active" style={{ fontSize: 11, padding: '2px 8px' }}>قناة</span>
                      )}
                      {(item.publish_to_groups || item.publishToGroups) && (
                        <span className="status-badge active" style={{ fontSize: 11, padding: '2px 8px' }}>قروبات</span>
                      )}
                      {!item.published && (
                        <span style={{ color: 'var(--gray-400)', fontSize: 12 }}>-</span>
                      )}
                    </div>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => openEditModal(item)} title="تعديل">
                        تعديل
                      </button>
                      <button className="btn btn-primary btn-sm" onClick={() => handlePublishDirect(item)} title={item.published ? 'إعادة النشر' : 'نشر'}>
                        {item.published ? 'إعادة النشر' : 'نشر'}
                      </button>
                      <button className="btn btn-secondary btn-sm" onClick={() => openRelinkModal(item)} title="إعادة ربط">
                        إعادة ربط
                      </button>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(item.id)} title="حذف">
                        حذف
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
              <h4>لا توجد منشورات</h4>
              <p>ابدأ بإضافة منشورات للبوت</p>
            </div>
          )}
        </div>

        <div className="mobile-cards">
          {filtered.map((item) => (
            <div key={item.id} className="mobile-card">
              <div className="mobile-card-header">
                <span className={`status-badge ${item.published ? 'active' : 'inactive'}`}>
                  {item.published ? 'منشور' : 'مسودة'}
                </span>
              </div>
              <div className="mobile-card-body">
                <p style={{ fontSize: 13, color: 'var(--gray-600)', marginBottom: 0 }}>
                  {item.content?.substring(0, 100)}...
                </p>
                {(item.publish_to_channel || item.publishToChannel || item.publish_to_groups || item.publishToGroups) && (
                  <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                    {(item.publish_to_channel || item.publishToChannel) && (
                      <span className="status-badge active" style={{ fontSize: 11 }}>قناة</span>
                    )}
                    {(item.publish_to_groups || item.publishToGroups) && (
                      <span className="status-badge active" style={{ fontSize: 11 }}>قروبات</span>
                    )}
                  </div>
                )}
              </div>
              <div className="mobile-card-meta" style={{ flexWrap: 'wrap', gap: 6 }}>
                <button className="btn btn-secondary btn-sm" onClick={() => openEditModal(item)}>
                  تعديل
                </button>
                <button className="btn btn-primary btn-sm" onClick={() => handlePublishDirect(item)}>
                  {item.published ? 'إعادة النشر' : 'نشر'}
                </button>
                <button className="btn btn-secondary btn-sm" onClick={() => openRelinkModal(item)}>
                  إعادة ربط
                </button>
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
              <h4>لا توجد منشورات</h4>
              <p>ابدأ بإضافة منشورات للبوت</p>
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
                    disabled={enhancingContent || !form.content}
                    style={{ fontSize: 12, padding: '4px 12px' }}
                  >
                    {enhancingContent ? 'جاري التحسين...' : uploadFile ? 'تحليل الصورة + تحسين المحتوى' : 'تحسين بالذكاء الاصطناعي'}
                  </button>
                </label>
                <textarea
                  className="form-input"
                  placeholder="محتوى المنشور..."
                  value={form.content}
                  onChange={(e) => setForm({ ...form, content: e.target.value })}
                  style={{ minHeight: 150 }}
                />
              </div>
              {form.content && !showAiPanel && (
                <div className="form-group">
                  <button
                    className="btn btn-secondary"
                    onClick={handleGenerateAI}
                    disabled={generating}
                    style={{ width: '100%' }}
                  >
                    {generating ? (
                      <span>جاري التوليد...</span>
                    ) : (
                      <span>توليد كلمات مفتاحية وأسئلة بالذكاء الاصطناعي</span>
                    )}
                  </button>
                </div>
              )}
              {showAiPanel && (
                <div className="form-group" style={{ background: 'var(--gray-50)', padding: 12, borderRadius: 8, border: '1px solid var(--gray-200)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <label style={{ fontWeight: 600, margin: 0 }}>الكلمات المفتاحية المقترحة</label>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={handleGenerateAI}
                      disabled={generating}
                      style={{ fontSize: 12, padding: '4px 12px' }}
                    >
                      {generating ? 'جاري التوليد...' : 'إعادة التوليد'}
                    </button>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
                    {aiKeywords.map((kw, i) => (
                      <span
                        key={i}
                        onClick={() => toggleKeyword(kw)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: 20,
                          fontSize: 13,
                          cursor: 'pointer',
                          background: selectedKeywords.includes(kw) ? 'var(--primary)' : 'var(--gray-200)',
                          color: selectedKeywords.includes(kw) ? 'white' : 'var(--gray-700)',
                          transition: 'all 0.2s',
                          border: 'none',
                        }}
                      >
                        {kw}
                      </span>
                    ))}
                    {aiKeywords.length === 0 && (
                      <span style={{ fontSize: 13, color: 'var(--gray-400)' }}>لا توجد كلمات مفتاحية</span>
                    )}
                  </div>
                  <label style={{ fontWeight: 600, marginBottom: 8, display: 'block' }}>الأسئلة المقترحة</label>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {aiQuestions.map((q, i) => (
                      <span
                        key={i}
                        onClick={() => toggleQuestion(q)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: 20,
                          fontSize: 13,
                          cursor: 'pointer',
                          background: selectedQuestions.includes(q) ? 'var(--primary)' : 'var(--gray-200)',
                          color: selectedQuestions.includes(q) ? 'white' : 'var(--gray-700)',
                          transition: 'all 0.2s',
                          border: 'none',
                        }}
                      >
                        {q}
                      </span>
                    ))}
                    {aiQuestions.length === 0 && (
                      <span style={{ fontSize: 13, color: 'var(--gray-400)' }}>لا توجد أسئلة مقترحة</span>
                    )}
                  </div>
                </div>
              )}
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
                  إرسال كملف
                </label>
                <small style={{ color: 'var(--gray-400)', marginTop: 4, display: 'block', fontSize: 12 }}>
                  عند التفعيل، سيتم إرسال الملف كمرفق قابل للتحميل بدلاً من عرضه مباشرة
                </small>
              </div>
              <div className="form-group">
                <ChannelGroupSelector
                  selected={selectedChannels}
                  onChange={setSelectedChannels}
                />
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
                {saving ? 'جاري الحفظ...' : 'حفظ'}
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
              <h3>تعديل المنشور</h3>
              <button className="modal-close" onClick={() => setShowEditModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>المحتوى</label>
                <textarea
                  className="form-input"
                  placeholder="محتوى المنشور..."
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
                  إرسال كملف
                </label>
              </div>
              <div className="form-group">
                <ChannelGroupSelector
                  selected={editSelectedChannels}
                  onChange={setEditSelectedChannels}
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

      {showRelinkModal && (
        <div className="modal-overlay" onClick={() => { setShowRelinkModal(false); setRelinkItem(null); }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>إعادة ربط المنشور بالقاموس</h3>
              <button className="modal-close" onClick={() => { setShowRelinkModal(false); setRelinkItem(null); }}>✕</button>
            </div>
            <div className="modal-body">
              <p style={{ marginBottom: 16, color: 'var(--gray-600)', fontSize: 14 }}>
                اختر الكلمات والأسئلة المراد ربطها بـ "{relinkItem?.title}"
              </p>
              <div className="form-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <label style={{ fontWeight: 600, margin: 0 }}>الكلمات المفتاحية</label>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={handleRelinkGenerate}
                    disabled={generating}
                    style={{ fontSize: 12, padding: '4px 12px' }}
                  >
                    {generating ? 'جاري التوليد...' : 'توليد بالذكاء الاصطناعي'}
                  </button>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {aiKeywords.map((kw, i) => (
                    <span
                      key={i}
                      onClick={() => toggleKeyword(kw)}
                      style={{
                        padding: '6px 12px',
                        borderRadius: 20,
                        fontSize: 13,
                        cursor: 'pointer',
                        background: selectedKeywords.includes(kw) ? 'var(--primary)' : 'var(--gray-200)',
                        color: selectedKeywords.includes(kw) ? 'white' : 'var(--gray-700)',
                        transition: 'all 0.2s',
                        border: 'none',
                      }}
                    >
                      {kw}
                    </span>
                  ))}
                  {aiKeywords.length === 0 && (
                    <span style={{ fontSize: 13, color: 'var(--gray-400)' }}>لا توجد كلمات مفتاحية</span>
                  )}
                </div>
              </div>
              <div className="form-group">
                <label style={{ fontWeight: 600, marginBottom: 8, display: 'block' }}>الأسئلة المقترحة</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {aiQuestions.map((q, i) => (
                    <span
                      key={i}
                      onClick={() => toggleQuestion(q)}
                      style={{
                        padding: '6px 12px',
                        borderRadius: 20,
                        fontSize: 13,
                        cursor: 'pointer',
                        background: selectedQuestions.includes(q) ? 'var(--primary)' : 'var(--gray-200)',
                        color: selectedQuestions.includes(q) ? 'white' : 'var(--gray-700)',
                        transition: 'all 0.2s',
                        border: 'none',
                      }}
                    >
                      {q}
                    </span>
                  ))}
                  {aiQuestions.length === 0 && (
                    <span style={{ fontSize: 13, color: 'var(--gray-400)' }}>لا توجد أسئلة مقترحة</span>
                  )}
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={handleRelink}>
                حفظ الربط
              </button>
              <button className="btn btn-secondary" onClick={() => { setShowRelinkModal(false); setRelinkItem(null); }}>إلغاء</button>
            </div>
          </div>
        </div>
      )}


    </>
  );
}
