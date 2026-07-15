import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useConfirm } from '../components/ConfirmDialog';
import { useToast } from '../components/ToastContext';
import ChannelGroupSelector from '../components/ChannelGroupSelector';
import FileUpload from '../components/FileUpload';

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

  const [uploadFiles, setUploadFiles] = useState([]);
  const [editUploadFile, setEditUploadFile] = useState(null);
  const [editUploadFiles, setEditUploadFiles] = useState([]);
  const [editExistingFiles, setEditExistingFiles] = useState([]);
  const [editRemovedExisting, setEditRemovedExisting] = useState([]);
  const [editPerFileContent, setEditPerFileContent] = useState(false);
  const [editFileCaptions, setEditFileCaptions] = useState({});

  const [aiKeywords, setAiKeywords] = useState([]);
  const [aiQuestions, setAiQuestions] = useState([]);
  const [selectedKeywords, setSelectedKeywords] = useState([]);
  const [selectedQuestions, setSelectedQuestions] = useState([]);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [editUploadProgress, setEditUploadProgress] = useState(null);

  const [showAiPanel, setShowAiPanel] = useState(false);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [enhancingContent, setEnhancingContent] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [relinkItem, setRelinkItem] = useState(null);

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletingNewsId, setDeletingNewsId] = useState(null);
  const [deletingAll, setDeletingAll] = useState(false);
  const [publishingId, setPublishingId] = useState(null);
  const [relinking, setRelinking] = useState(false);
  const [resettingChannel, setResettingChannel] = useState(false);
  const [permanentDeleting, setPermanentDeleting] = useState(false);

  const [perFileContent, setPerFileContent] = useState(false);
  const [fileCaptions, setFileCaptions] = useState({});
  const [selectedChannels, setSelectedChannels] = useState([]);
  const [editSelectedChannels, setEditSelectedChannels] = useState([]);
  const [channelGroups, setChannelGroups] = useState([]);

  useEffect(() => {
    loadNews();
    const interval = setInterval(() => {
      loadNews();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!showModal) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setShowModal(false);
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [showModal]);

  useEffect(() => {
    const loadChannels = async () => {
      try {
        const data = await api.get('/channels/active');
        setChannelGroups(data);
      } catch (err) {
        console.error('Failed to load channels:', err);
      }
    };
    loadChannels();
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

  const getChannelName = (chatId) => {
    const ch = channelGroups.find(c => c.chatId === parseInt(chatId) || c.chatId === chatId);
    return ch ? ch.title : chatId;
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

  const handleEditEnhance = async () => {
    if (!editForm.content) {
      showToast('يرجى كتابة المحتوى أولاً', 'error');
      return;
    }
    setEnhancingContent(true);
    try {
      const result = await api.post('/news/enhance', {
        content: editForm.content,
        title: ''
      });
      setEditForm({ ...editForm, content: result.enhanced?.enhanced_content || result.enhanced?.content || editForm.content });
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
    if (uploadFiles.length === 0) return;
    setSaving(true);
    setUploadProgress(0);
    try {
      let newItem;
      const allFiles = uploadFiles;
      if (allFiles.length > 0) {
        const formData = new FormData();
        formData.append('title', '');
        formData.append('content', form.content);
        allFiles.forEach(f => formData.append('files', f));
        formData.append('as_document', form.as_document);
        formData.append('file_captions', JSON.stringify(fileCaptions));
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
      setUploadFiles([]);
      setFileCaptions({});
      setSelectedChannels([]);
      setPerFileContent(false);
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
    setEditUploadProgress(0);
    try {
      const allEditFiles = editUploadFiles.length > 0 ? editUploadFiles : (editUploadFile ? [editUploadFile] : []);
      if (allEditFiles.length > 0 || editRemovedExisting.length > 0 || editPerFileContent) {
        const formData = new FormData();
        formData.append('title', '');
        formData.append('content', editForm.content);
        formData.append('as_document', editForm.as_document);
        formData.append('target_channels', JSON.stringify(editSelectedChannels));
        formData.append('removed_existing', JSON.stringify(editRemovedExisting));
        formData.append('file_captions', JSON.stringify(editFileCaptions));
        allEditFiles.forEach(f => formData.append('files', f));
        await api.uploadWithProgress(`/news/${editItem.id}/upload`, formData, (percent) => {
          setEditUploadProgress(percent);
        }, 'PUT');
      } else {
        await api.put(`/news/${editItem.id}`, { content: editForm.content, as_document: editForm.as_document, target_channels: JSON.stringify(editSelectedChannels) });
      }
      setNews(news.map(n => n.id === editItem.id ? { 
        ...n, 
        content: editForm.content, 
        as_document: editForm.as_document,
      } : n));
      setShowEditModal(false);
      setEditItem(null);
      setEditUploadFile(null);
      setEditUploadFiles([]);
      setEditPerFileContent(false);
      setEditFileCaptions({});
      showToast('تم تعديل المنشور بنجاح', 'success');
    } catch (err) {
      console.error('Failed to edit news:', err);
      showToast('فشل تعديل المنشور', 'error');
    } finally {
      setSaving(false);
      setEditUploadProgress(null);
    }
  };

  const handleDeleteNews = (id) => {
    setDeletingNewsId(id);
    setShowDeleteModal(true);
  };

  const handlePublish = async (item) => {
    setPublishingId(item.id);
    try {
      await api.post(`/news/${item.id}/publish`);
      setNews(news.map(n => n.id === item.id ? { ...n, published: true } : n));
      showToast('تم النشر بنجاح', 'success');
    } catch (err) {
      console.error('Publish failed:', err);
      showToast('فشل النشر', 'error');
    } finally {
      setPublishingId(null);
    }
  };

  const handleNewsResetPublish = async (id) => {
    setShowDeleteModal(false);
    setResettingChannel(true);
    try {
      await api.delete(`/news/${id}/channel`);
      setNews(news.map(n => n.id === id ? { ...n, published: false } : n));
      showToast('تم حذف المنشور من القنوات بنجاح', 'success');
    } catch (err) {
      showToast('حدث خطأ أثناء الحذف', 'error');
    } finally {
      setResettingChannel(false);
    }
  };

  const handleNewsPermanentDelete = async (id) => {
    setShowDeleteModal(false);
    const ok = await confirm('هل أنت متأكد من الحذف النهائي؟ سيتم حذف المنشور نهائياً.');
    if (!ok) return;
    setPermanentDeleting(true);
    try {
      await api.delete(`/news/${id}`);
      setNews(news.filter((n) => n.id !== id));
      showToast('تم حذف المنشور نهائياً', 'success');
    } catch (err) {
      showToast('حدث خطأ أثناء الحذف', 'error');
    } finally {
      setPermanentDeleting(false);
    }
  };

  const handleDeleteAll = async () => {
    const ok = await confirm('هل أنت متأكد من حذف جميع المنشورات؟ هذا الإجراء لا يمكن التراجع عنه.');
    if (!ok) return;
    setDeletingAll(true);
    try {
      await api.delete('/news');
      setNews([]);
      showToast('تم حذف جميع المنشورات بنجاح', 'success');
    } catch (err) {
      console.error('Failed to delete all news:', err);
      showToast('فشل حذف جميع المنشورات', 'error');
    } finally {
      setDeletingAll(false);
    }
  };

  const handleRelink = async () => {
    if (!relinkItem) return;
    setRelinking(true);
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
    } finally {
      setRelinking(false);
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
    const channels = item.targetChannels || item.target_channels;
    setEditSelectedChannels(channels ? (typeof channels === 'string' ? JSON.parse(channels) : channels) : []);
    setEditUploadFile(null);
    setEditUploadFiles([]);
    try {
      const fj = item.filesJson ? (typeof item.filesJson === 'string' ? JSON.parse(item.filesJson) : item.filesJson) : [];
      setEditExistingFiles(Array.isArray(fj) ? fj : []);
      const captions = {};
      let hasCaptions = false;
      (Array.isArray(fj) ? fj : []).forEach((f, i) => {
        if (f.caption) {
          captions[i] = f.caption;
          hasCaptions = true;
        }
      });
      setEditFileCaptions(captions);
      setEditPerFileContent(hasCaptions);
    } catch { setEditExistingFiles([]); setEditFileCaptions({}); setEditPerFileContent(false); }
    setEditRemovedExisting([]);
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
            <button className="btn btn-danger" onClick={handleDeleteAll} disabled={deletingAll} style={{ opacity: deletingAll ? 0.7 : 1, transition: 'all 0.2s' }}>
              {deletingAll ? (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" style={{ animation: 'spin 1s linear infinite' }}>
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" strokeDasharray="31.4 31.4" strokeLinecap="round" />
                  </svg>
                  جاري...
                </span>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                  حذف الكل
                </>
              )}
            </button>
            <button className="btn btn-primary" onClick={() => { setForm({ content: '', as_document: false }); setUploadFiles([]); setSelectedChannels([]); setShowModal(true); }}>
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
                  <td style={{ display: 'flex', alignItems: 'center', gap: 8, maxWidth: 300 }}>
                    {(() => {
                      const files = (() => { try { return item.filesJson ? (typeof item.filesJson === 'string' ? JSON.parse(item.filesJson) : item.filesJson) : []; } catch { return []; } })();
                      const f = files[0];
                      if (!f) return null;
                      if (/\.(jpg|jpeg|png|gif|webp)$/i.test(f.thumbnail || f.url || '')) {
                        return <img src={f.thumbnail || f.url} alt="" style={{ width: 32, height: 32, objectFit: 'cover', borderRadius: 4, flexShrink: 0 }} />;
                      }
                      return <span style={{ fontSize: 18, flexShrink: 0 }}>📄</span>;
                    })()}
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.content?.substring(0, 80)}...
                    </span>
                  </td>
                  <td>
                    <span className={`status-badge ${item.published ? 'active' : 'inactive'}`}>
                      {item.published ? 'منشور' : 'مسودة'}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {(() => {
                        try {
                          const targets = item.targetChannels 
                            ? (typeof item.targetChannels === 'string' ? JSON.parse(item.targetChannels) : item.targetChannels)
                            : [];
                          if (targets.length === 0 && !item.published) {
                            return <span style={{ color: 'var(--gray-400)', fontSize: 12 }}>-</span>;
                          }
                          return targets.map(id => (
                            <span key={id} className="status-badge active" style={{ fontSize: 11, padding: '2px 8px' }}>
                              {getChannelName(id)}
                            </span>
                          ));
                        } catch {
                          return <span style={{ color: 'var(--gray-400)', fontSize: 12 }}>-</span>;
                        }
                      })()}
                    </div>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                      {!item.published && (
                        <button className="btn btn-secondary btn-sm" onClick={() => openEditModal(item)} title="تعديل">
                          تعديل
                        </button>
                      )}
                      {!item.published && (
                        <button className="btn btn-primary btn-sm" onClick={() => handlePublish(item)} title="نشر" disabled={publishingId === item.id} style={{ opacity: publishingId === item.id ? 0.7 : 1, transition: 'all 0.2s' }}>
                          {publishingId === item.id ? (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                              <svg width="14" height="14" viewBox="0 0 24 24" style={{ animation: 'spin 1s linear infinite' }}>
                                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" strokeDasharray="31.4 31.4" strokeLinecap="round" />
                              </svg>
                              جاري...
                            </span>
                          ) : 'نشر'}
                        </button>
                      )}
                      <button className="btn btn-secondary btn-sm" onClick={() => openRelinkModal(item)} title="إعادة ربط">
                        إعادة ربط
                      </button>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDeleteNews(item.id)} title="حذف">
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
                {(() => {
                  const files = (() => { try { return item.filesJson ? (typeof item.filesJson === 'string' ? JSON.parse(item.filesJson) : item.filesJson) : []; } catch { return []; } })();
                  const f = files[0];
                  if (!f) return null;
                  if (/\.(jpg|jpeg|png|gif|webp)$/i.test(f.thumbnail || f.url || '')) {
                    return <img src={f.thumbnail || f.url} alt="" style={{ width: 32, height: 32, objectFit: 'cover', borderRadius: 4, marginBottom: 8 }} />;
                  }
                  return <span style={{ fontSize: 18, marginBottom: 8, display: 'block' }}>📄</span>;
                })()}
                <p style={{ fontSize: 13, color: 'var(--gray-600)', marginBottom: 0 }}>
                  {item.content?.substring(0, 100)}...
                </p>
                <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                  {(() => {
                    try {
                      const targets = item.targetChannels 
                        ? (typeof item.targetChannels === 'string' ? JSON.parse(item.targetChannels) : item.targetChannels)
                        : [];
                      if (targets.length === 0 && !item.published) {
                        return <span style={{ color: 'var(--gray-400)', fontSize: 12 }}>-</span>;
                      }
                      return targets.map(id => (
                        <span key={id} className="status-badge active" style={{ fontSize: 11 }}>
                          {getChannelName(id)}
                        </span>
                      ));
                    } catch {
                      return <span style={{ color: 'var(--gray-400)', fontSize: 12 }}>-</span>;
                    }
                  })()}
                </div>
              </div>
              <div className="mobile-card-meta" style={{ flexWrap: 'wrap', gap: 6 }}>
                {!item.published && (
                  <button className="btn btn-secondary btn-sm" onClick={() => openEditModal(item)}>
                    تعديل
                  </button>
                )}
                {!item.published && (
                  <button className="btn btn-primary btn-sm" onClick={() => handlePublish(item)} disabled={publishingId === item.id} style={{ opacity: publishingId === item.id ? 0.7 : 1, transition: 'all 0.2s' }}>
                    {publishingId === item.id ? (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                        <svg width="14" height="14" viewBox="0 0 24 24" style={{ animation: 'spin 1s linear infinite' }}>
                          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" strokeDasharray="31.4 31.4" strokeLinecap="round" />
                        </svg>
                        جاري...
                      </span>
                    ) : 'نشر'}
                  </button>
                )}
                <button className="btn btn-secondary btn-sm" onClick={() => openRelinkModal(item)}>
                  إعادة ربط
                </button>
                <button className="btn btn-danger btn-sm" onClick={() => handleDeleteNews(item.id)}>
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
        <div className="modal-overlay" onClick={() => { setShowModal(false); setPerFileContent(false); setFileCaptions({}); }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>إضافة منشور جديد</h3>
              <button className="modal-close" onClick={() => { setShowModal(false); setPerFileContent(false); setFileCaptions({}); }}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={perFileContent}
                    onChange={(e) => setPerFileContent(e.target.checked)}
                    style={{ width: 18, height: 18 }}
                  />
                  إضافة محتوى خاص لكل ملف
                </label>
              </div>
              <FileUpload
                files={uploadFiles}
                setFiles={(newFiles) => setUploadFiles(newFiles)}
                asDocument={form.as_document}
                setAsDocument={(val) => setForm({ ...form, as_document: val })}
              />
              <div style={{ borderTop: '1px solid var(--gray-200)', margin: '12px 0' }} />
                  <div className="form-group">
                    <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      المحتوى
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={handleEnhance}
                        disabled={enhancingContent || !form.content}
                        style={{ fontSize: 12, padding: '4px 12px' }}
                      >
                        {enhancingContent ? 'جاري التحسين...' : uploadFiles.length > 0 ? 'تحليل الصورة + تحسين المحتوى' : 'تحسين بالذكاء الاصطناعي'}
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
              {perFileContent && uploadFiles.length > 0 && (
                <>
                  <div style={{ borderTop: '1px solid var(--gray-200)', margin: '12px 0' }} />
                  <div className="form-group">
                    <label>محتوى لكل ملف</label>
                    {uploadFiles.map((f, idx) => (
                      <div key={idx} style={{ marginBottom: 10, padding: 10, border: '1px solid var(--gray-200)', borderRadius: 6 }}>
                        <div style={{ fontSize: 13, color: 'var(--gray-500)', marginBottom: 4 }}>{f.name}</div>
                        <textarea
                          className="form-input"
                          placeholder={`محتوى ${f.name}...`}
                          value={fileCaptions[idx] || ''}
                          onChange={(e) => setFileCaptions({ ...fileCaptions, [idx]: e.target.value })}
                          style={{ minHeight: 80 }}
                        />
                      </div>
                    ))}
                  </div>
                </>
              )}
              <div style={{ borderTop: '1px solid var(--gray-200)', margin: '12px 0' }} />
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
              {((!form.content) || uploadFiles.length === 0) && (
                <div style={{ width: '100%', marginBottom: 8, fontSize: 12, color: 'var(--gray-500)', textAlign: 'center' }}>
                  {!form.content && uploadFiles.length === 0
                    ? 'يرجى إضافة ملف وكتابة المحتوى'
                    : !form.content
                    ? 'يرجى كتابة المحتوى'
                    : 'يرجى إضافة ملف'}
                </div>
              )}
              <button
                className="btn btn-primary"
                onClick={handleSave}
                disabled={saving || uploadFiles.length === 0 || !form.content}
              >
                {saving ? 'جاري الحفظ...' : 'حفظ'}
              </button>
              <button className="btn btn-secondary" onClick={() => { setShowModal(false); setPerFileContent(false); setFileCaptions({}); }}>إلغاء</button>
            </div>
          </div>
        </div>
      )}

      {showEditModal && (
        <div className="modal-overlay" onClick={() => { setShowEditModal(false); setEditPerFileContent(false); setEditFileCaptions({}); }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>تعديل المنشور</h3>
              <button className="modal-close" onClick={() => { setShowEditModal(false); setEditPerFileContent(false); setEditFileCaptions({}); }}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  المحتوى
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={handleEditEnhance}
                    disabled={enhancingContent || !editForm.content}
                    style={{ fontSize: 12, padding: '4px 12px' }}
                  >
                    {enhancingContent ? 'جاري التحسين...' : (editUploadFiles.length > 0 || editUploadFile) ? 'تحليل الصورة + تحسين المحتوى' : 'تحسين بالذكاء الاصطناعي'}
                  </button>
                </label>
                <textarea
                  className="form-input"
                  placeholder="محتوى المنشور..."
                  value={editForm.content}
                  onChange={(e) => setEditForm({ ...editForm, content: e.target.value })}
                  style={{ minHeight: 150 }}
                />
              </div>
              <div className="form-group">
                <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={editPerFileContent}
                    onChange={(e) => setEditPerFileContent(e.target.checked)}
                    style={{ width: 18, height: 18 }}
                  />
                  إضافة محتوى خاص لكل ملف
                </label>
              </div>
              {editPerFileContent && editExistingFiles.length > 0 && (
                <>
                  <div style={{ borderTop: '1px solid var(--gray-200)', margin: '12px 0' }} />
                  <div className="form-group">
                    <label>محتوى لكل ملف</label>
                    {editExistingFiles.map((f, idx) => {
                      if (editRemovedExisting.includes(idx)) return null;
                      return (
                        <div key={idx} style={{ marginBottom: 10, padding: 10, border: '1px solid var(--gray-200)', borderRadius: 6 }}>
                          <div style={{ fontSize: 13, color: 'var(--gray-500)', marginBottom: 4 }}>
                            {f.name || f.url?.split('/').pop() || `ملف ${idx + 1}`} <span style={{ color: 'var(--gray-400)' }}>(حالي)</span>
                          </div>
                          <textarea
                            className="form-input"
                            placeholder={`محتوى ${f.name || `ملف ${idx + 1}`}...`}
                            value={editFileCaptions[idx] || ''}
                            onChange={(e) => setEditFileCaptions({ ...editFileCaptions, [idx]: e.target.value })}
                            style={{ minHeight: 80 }}
                          />
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
              {editPerFileContent && editUploadFiles.length > 0 && (
                <>
                  <div style={{ borderTop: '1px solid var(--gray-200)', margin: '12px 0' }} />
                  <div className="form-group">
                    <label>محتوى للملفات الجديدة</label>
                    {editUploadFiles.map((f, idx) => (
                      <div key={`new-${idx}`} style={{ marginBottom: 10, padding: 10, border: '1px solid var(--gray-200)', borderRadius: 6 }}>
                        <div style={{ fontSize: 13, color: 'var(--gray-500)', marginBottom: 4 }}>{f.name}</div>
                        <textarea
                          className="form-input"
                          placeholder={`محتوى ${f.name}...`}
                          value={editFileCaptions[`new_${idx}`] || ''}
                          onChange={(e) => setEditFileCaptions({ ...editFileCaptions, [`new_${idx}`]: e.target.value })}
                          style={{ minHeight: 80 }}
                        />
                      </div>
                    ))}
                  </div>
                </>
              )}
              <FileUpload
                files={editUploadFiles}
                setFiles={(newFiles) => { setEditUploadFiles(newFiles); setEditUploadFile(newFiles[0] || null); }}
                asDocument={editForm.as_document}
                setAsDocument={(val) => setEditForm({ ...editForm, as_document: val })}
                existingFiles={editExistingFiles}
                onRemoveExisting={setEditRemovedExisting}
              />
              <div className="form-group">
                <ChannelGroupSelector
                  selected={editSelectedChannels}
                  onChange={setEditSelectedChannels}
                />
              </div>
            </div>
            <div className="modal-footer">
              {editUploadProgress !== null && (
                <div style={{ width: '100%', marginBottom: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 13 }}>
                    <span>جاري رفع الملف...</span>
                    <span>{editUploadProgress}%</span>
                  </div>
                  <div style={{ width: '100%', height: 8, background: 'var(--gray-200)', borderRadius: 4, overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${editUploadProgress}%`,
                        height: '100%',
                        background: editUploadProgress === 100 ? 'var(--success)' : 'var(--primary)',
                        borderRadius: 4,
                        transition: 'width 0.3s ease',
                      }}
                    />
                  </div>
                </div>
              )}
              <button className="btn btn-primary" onClick={handleEditSave} disabled={saving}>
                {saving ? 'جاري الحفظ...' : 'حفظ التعديلات'}
              </button>
              <button className="btn btn-secondary" onClick={() => { setShowEditModal(false); setEditPerFileContent(false); setEditFileCaptions({}); }}>إلغاء</button>
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
              <button className="btn btn-primary" onClick={handleRelink} disabled={relinking} style={{ opacity: relinking ? 0.7 : 1, transition: 'all 0.2s' }}>
                {relinking ? (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" style={{ animation: 'spin 1s linear infinite' }}>
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" strokeDasharray="31.4 31.4" strokeLinecap="round" />
                    </svg>
                    جاري حفظ الربط...
                  </span>
                ) : 'حفظ الربط'}
              </button>
              <button className="btn btn-secondary" onClick={() => { setShowRelinkModal(false); setRelinkItem(null); }}>إلغاء</button>
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
                style={{ width: '100%', marginBottom: 10, justifyContent: 'center', opacity: resettingChannel ? 0.7 : 1, transition: 'all 0.2s' }}
                onClick={() => handleNewsResetPublish(deletingNewsId)}
                disabled={resettingChannel}
              >
                {resettingChannel ? (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" style={{ animation: 'spin 1s linear infinite' }}>
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" strokeDasharray="31.4 31.4" strokeLinecap="round" />
                    </svg>
                    جاري الحذف...
                  </span>
                ) : 'حذف من القنوات فقط'}
              </button>
              <p style={{ fontSize: 12, color: 'var(--gray-500)', marginBottom: 16, textAlign: 'center' }}>
                حذف المنشور من القنوات والقروبات مع الاحتفاظ به كمسودة
              </p>
              <button
                className="btn btn-danger"
                style={{ width: '100%', justifyContent: 'center', opacity: permanentDeleting ? 0.7 : 1, transition: 'all 0.2s' }}
                onClick={() => handleNewsPermanentDelete(deletingNewsId)}
                disabled={permanentDeleting}
              >
                {permanentDeleting ? (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" style={{ animation: 'spin 1s linear infinite' }}>
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" strokeDasharray="31.4 31.4" strokeLinecap="round" />
                    </svg>
                    جاري الحذف...
                  </span>
                ) : 'حذف نهائي'}
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
