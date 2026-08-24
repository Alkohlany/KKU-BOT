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
  const [savePhase, setSavePhase] = useState('');
  const [enhancingContent, setEnhancingContent] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletingNewsId, setDeletingNewsId] = useState(null);
  const [deletingAll, setDeletingAll] = useState(false);
  const [publishingId, setPublishingId] = useState(null);
  const [resettingChannel, setResettingChannel] = useState(false);
  const [permanentDeleting, setPermanentDeleting] = useState(false);

  const [perFileContent, setPerFileContent] = useState(false);
  const [fileCaptions, setFileCaptions] = useState({});
  const [selectedChannels, setSelectedChannels] = useState([]);
  const [addWizardStep, setAddWizardStep] = useState(1);
  const [linkedResponseId, setLinkedResponseId] = useState('');
  const [availableResponses, setAvailableResponses] = useState([]);
  const [editSelectedChannels, setEditSelectedChannels] = useState([]);
  const [editWizardStep, setEditWizardStep] = useState(1);
  const [editIsPublished, setEditIsPublished] = useState(false);
  const [editAiKeywords, setEditAiKeywords] = useState([]);
  const [editAiQuestions, setEditAiQuestions] = useState([]);
  const [editSelectedKeywords, setEditSelectedKeywords] = useState([]);
  const [editSelectedQuestions, setEditSelectedQuestions] = useState([]);
  const [editShowAiPanel, setEditShowAiPanel] = useState(false);
  const [editGenerating, setEditGenerating] = useState(false);
  const [editLinkedResponseId, setEditLinkedResponseId] = useState('');
  const [editAvailableResponses, setEditAvailableResponses] = useState([]);
  const [channelGroups, setChannelGroups] = useState([]);

  useEffect(() => {
    loadNews();
    const interval = setInterval(() => {
      loadNews();
    }, 120000);
    return () => clearInterval(interval);
  }, [search]);

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

  useEffect(() => {
    if (addWizardStep === 3) {
      api.getResponses().then(data => setAvailableResponses(data.items || data || [])).catch(() => {});
    }
  }, [addWizardStep]);

  useEffect(() => {
    if (showEditModal && editWizardStep === 3) {
      api.getResponses().then(data => setEditAvailableResponses(data.items || data || [])).catch(() => {});
    }
  }, [showEditModal, editWizardStep]);

  const loadNews = async () => {
    try {
      const data = await api.get(`/news?search=${encodeURIComponent(search)}`);
      const items = data.items || data;
      setNews(Array.isArray(items) ? items : []);
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

  const filtered = news;

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

  const toggleEditKeyword = (kw) => {
    setEditSelectedKeywords(prev =>
      prev.includes(kw) ? prev.filter(k => k !== kw) : [...prev, kw]
    );
  };

  const toggleEditQuestion = (q) => {
    setEditSelectedQuestions(prev =>
      prev.includes(q) ? prev.filter(item => item !== q) : [...prev, q]
    );
  };

  const handleEditGenerateAI = async () => {
    if (!editForm.content) {
      showToast('يرجى كتابة المحتوى أولاً', 'error');
      return;
    }
    setEditGenerating(true);
    try {
      const result = await api.analyzeNews({ title: '', content: editForm.content });
      setEditAiKeywords(result.keywords || []);
      setEditAiQuestions(result.questions || []);
      setEditSelectedKeywords([]);
      setEditSelectedQuestions([]);
      setEditShowAiPanel(true);
    } catch (err) {
      console.error('Failed to generate AI content:', err);
      showToast('فشل توليد المحتوى بالذكاء الاصطناعي', 'error');
    } finally {
      setEditGenerating(false);
    }
  };

  const handleSave = async () => {
    const hasFiles = uploadFiles.length > 0;
    const hasContent = perFileContent
      ? Object.values(fileCaptions).some(c => c && c.trim())
      : !!form.content?.trim();
    if (!hasContent) return;
    setSaving(true);
    setSavePhase(hasFiles ? 'جاري رفع الملفات' : 'جاري الحفظ');
    setUploadProgress(hasFiles ? 0 : null);
    try {
      let contentToSend = form.content;
      if (perFileContent && hasFiles) {
        const parts = uploadFiles.map((f, i) => fileCaptions[i] || '').filter(Boolean);
        contentToSend = parts.join('\n\n---\n\n');
        if (!contentToSend.trim()) return;
      }
      let newItem;
      if (hasFiles) {
        const formData = new FormData();
        formData.append('title', '');
        formData.append('content', contentToSend);
        uploadFiles.forEach(f => formData.append('files', f));
        formData.append('as_document', form.as_document);
        formData.append('file_captions', JSON.stringify(fileCaptions));
        formData.append('target_channels', JSON.stringify(selectedChannels));
        formData.append('selected_keywords', JSON.stringify(selectedKeywords));
        formData.append('selected_questions', JSON.stringify(selectedQuestions));
        formData.append('linked_response_id', linkedResponseId || '');
        const cloudFiles = [];
        uploadFiles.forEach((f, i) => {
          if (f._isCloud && f._cloudUrl) cloudFiles.push({ index: i, url: f._cloudUrl, name: f.name });
        });
        formData.append('cloud_files', JSON.stringify(cloudFiles));
        setSavePhase('جاري رفع الملفات');
        newItem = await api.uploadWithProgress('/news/upload', formData, (percent) => {
          setUploadProgress(percent);
          if (percent >= 100) setSavePhase('جاري الحفظ');
        });
      } else {
        setSavePhase('جاري الحفظ');
        newItem = await api.addNews({
          content: contentToSend,
          title: '',
          target_channels: JSON.stringify(selectedChannels),
          selected_keywords: JSON.stringify(selectedKeywords),
          selected_questions: JSON.stringify(selectedQuestions),
          linked_response_id: linkedResponseId || '',
        });
      }
      setSavePhase('تم بنجاح');
      setUploadProgress(100);
      await new Promise(r => setTimeout(r, 800));
      loadNews();
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
      setLinkedResponseId('');
      setAddWizardStep(1);
      showToast('تم إضافة المنشور بنجاح', 'success');
    } catch (err) {
      console.error('Failed to save news:', err);
      setSavePhase('');
      showToast('فشل حفظ المنشور', 'error');
    } finally {
      setSaving(false);
      setSavePhase('');
      setUploadProgress(null);
    }
  };

  const handleEditSave = async () => {
    const hasEditContent = editPerFileContent
      ? Object.values(editFileCaptions).some(c => c && c.trim())
      : !!editForm.content?.trim();
    if (!hasEditContent || !editItem) {
      showToast('يرجى كتابة المحتوى أولاً', 'error');
      return;
    }
    setSaving(true);
    setSavePhase('جاري الحفظ');
    try {
      if (editItem.published) {
        await api.put(`/news/${editItem.id}`, {
          content: editForm.content,
          selected_keywords: JSON.stringify(editSelectedKeywords),
          selected_questions: JSON.stringify(editSelectedQuestions),
          linked_response_id: editLinkedResponseId || '',
        });
      } else {
        let contentToSend = editForm.content;
        if (editPerFileContent) {
          const parts = editExistingFiles.map((f, i) => editRemovedExisting.includes(i) ? '' : (editFileCaptions[i] || '')).filter(Boolean);
          const newParts = editUploadFiles.map((f, i) => editFileCaptions[`new_${i}`] || '').filter(Boolean);
          const allParts = [...parts, ...newParts];
          if (allParts.length > 0) {
            contentToSend = allParts.join('\n\n---\n\n');
          }
        }
        const allEditFiles = editUploadFiles.length > 0 ? editUploadFiles : (editUploadFile ? [editUploadFile] : []);
        const hasFiles = allEditFiles.length > 0 || editRemovedExisting.length > 0;
        if (hasFiles || editPerFileContent) {
          setUploadProgress(0);
          setSavePhase('جاري رفع الملفات');
          const formData = new FormData();
          formData.append('title', '');
          formData.append('content', contentToSend);
          formData.append('as_document', editForm.as_document);
          formData.append('target_channels', JSON.stringify(editSelectedChannels));
          formData.append('removed_existing', JSON.stringify(editRemovedExisting));
          formData.append('file_captions', JSON.stringify(editFileCaptions));
          formData.append('selected_keywords', JSON.stringify(editSelectedKeywords));
          formData.append('selected_questions', JSON.stringify(editSelectedQuestions));
          formData.append('linked_response_id', editLinkedResponseId || '');
          const cloudFiles = [];
          allEditFiles.forEach((f, i) => {
            if (f._isCloud && f._cloudUrl) cloudFiles.push({ index: i, url: f._cloudUrl, name: f.name });
          });
          formData.append('cloud_files', JSON.stringify(cloudFiles));
          allEditFiles.forEach(f => formData.append('files', f));
          await api.uploadWithProgress(`/news/${editItem.id}/upload`, formData, (percent) => {
            setUploadProgress(percent);
            if (percent >= 100) setSavePhase('جاري الحفظ');
          }, 'PUT');
        } else {
          await api.put(`/news/${editItem.id}`, {
            content: contentToSend,
            as_document: editForm.as_document,
            target_channels: JSON.stringify(editSelectedChannels),
            selected_keywords: JSON.stringify(editSelectedKeywords),
            selected_questions: JSON.stringify(editSelectedQuestions),
            linked_response_id: editLinkedResponseId || '',
          });
        }
      }
      setSavePhase('تم بنجاح');
      setUploadProgress(100);
      await new Promise(r => setTimeout(r, 800));
      loadNews();
      setShowEditModal(false);
      setEditItem(null);
      setEditIsPublished(false);
      setEditForm({ content: '', as_document: false });
      setEditUploadFile(null);
      setEditUploadFiles([]);
      setEditExistingFiles([]);
      setEditRemovedExisting([]);
      setEditPerFileContent(false);
      setEditFileCaptions({});
      setEditSelectedChannels([]);
      setEditWizardStep(1);
      setEditAiKeywords([]);
      setEditAiQuestions([]);
      setEditSelectedKeywords([]);
      setEditSelectedQuestions([]);
      setEditShowAiPanel(false);
      setEditLinkedResponseId('');
      showToast('تم تعديل المنشور بنجاح', 'success');
    } catch (err) {
      console.error('Failed to edit news:', err);
      setSavePhase('');
      showToast('فشل تعديل المنشور', 'error');
    } finally {
      setSaving(false);
      setSavePhase('');
      setUploadProgress(null);
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
      await loadNews();
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
      await loadNews();
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
      await loadNews();
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
      await loadNews();
      showToast('تم حذف جميع المنشورات بنجاح', 'success');
    } catch (err) {
      console.error('Failed to delete all news:', err);
      showToast('فشل حذف جميع المنشورات', 'error');
    } finally {
      setDeletingAll(false);
    }
  };

  const openEditModal = (item) => {
    setEditItem(item);
    setEditIsPublished(!!item.published);
    setEditForm({ 
      content: item.content, 
      as_document: item.as_document || false,
    });
    const channels = item.targetChannels || item.target_channels;
    try {
      setEditSelectedChannels(channels ? (typeof channels === 'string' ? JSON.parse(channels) : channels) : []);
    } catch { setEditSelectedChannels([]); }
    setEditUploadFile(null);
    setEditUploadFiles([]);
    setEditWizardStep(item.published ? 1 : 1);
    setEditAiKeywords([]);
    setEditAiQuestions([]);
    setEditSelectedKeywords(item.selectedKeywords ? (typeof item.selectedKeywords === 'string' ? JSON.parse(item.selectedKeywords) : item.selectedKeywords) : []);
    setEditSelectedQuestions(item.selectedQuestions ? (typeof item.selectedQuestions === 'string' ? JSON.parse(item.selectedQuestions) : item.selectedQuestions) : []);
    setEditShowAiPanel(false);
    setEditLinkedResponseId(item.linked_response_id || '');
    if (item.published) {
      setEditExistingFiles([]);
      setEditFileCaptions({});
      setEditPerFileContent(false);
      setEditRemovedExisting([]);
    } else {
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
    }
    setShowEditModal(true);
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
            <button className="btn btn-primary" onClick={() => { setForm({ content: '', as_document: false }); setUploadFiles([]); setSelectedChannels([]); setAddWizardStep(1); setShowModal(true); }}>
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
                    <span className={`status-badge ${item.channelMessageId ? 'active' : 'inactive'}`}>
                      {item.channelMessageId ? 'منشور' : 'مسودة'}
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
                      <button className="btn btn-secondary btn-sm" onClick={() => openEditModal(item)} title="تعديل">
                        تعديل
                      </button>
                      {!item.channelMessageId && (
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
                <span className={`status-badge ${item.channelMessageId ? 'active' : 'inactive'}`}>
                  {item.channelMessageId ? 'منشور' : 'مسودة'}
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
                <button className="btn btn-secondary btn-sm" onClick={() => openEditModal(item)}>
                  تعديل
                </button>
                {!item.channelMessageId && (
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
        <div className="modal-overlay" onClick={() => { setShowModal(false); setPerFileContent(false); setFileCaptions({}); setAddWizardStep(1); }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>إضافة منشور جديد</h3>
              <button className="modal-close" onClick={() => { setShowModal(false); setPerFileContent(false); setFileCaptions({}); setAddWizardStep(1); }}>✕</button>
            </div>
            <div className="modal-body">
              <div className="wizard-steps">
                {[
                  { num: 1, label: 'الملفات' },
                  { num: 2, label: 'المحتوى' },
                  { num: 3, label: 'الكلمات' },
                  { num: 4, label: 'النشر' },
                ].map((step, i) => (
                  <React.Fragment key={step.num}>
                    <div className={`wizard-step ${addWizardStep === step.num ? 'active' : ''} ${addWizardStep > step.num ? 'completed' : ''}`}>
                      <div className="wizard-step-circle">{addWizardStep > step.num ? '✓' : step.num}</div>
                      <div className="wizard-step-label">{step.label}</div>
                    </div>
                    {i < 3 && <div className={`wizard-connector ${addWizardStep > step.num ? 'completed' : ''}`} />}
                  </React.Fragment>
                ))}
              </div>

              <div className="wizard-content">
                {addWizardStep === 1 && (
                  <>
                    <FileUpload
                      files={uploadFiles}
                      setFiles={(newFiles) => setUploadFiles(newFiles)}
                      asDocument={form.as_document}
                      setAsDocument={(val) => setForm({ ...form, as_document: val })}
                    />
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
                    <div style={{ fontSize: 12, color: 'var(--gray-500)', textAlign: 'center', marginTop: 8 }}>
                      يمكنك تخطي هذه الخطوة لإنشاء منشور نصي فقط
                    </div>
                  </>
                )}

                {addWizardStep === 2 && (
                  <>
                    {perFileContent && uploadFiles.length > 0 ? (
                      uploadFiles.map((f, idx) => (
                        <div key={idx} className="file-content-item">
                          <label>{f.name}</label>
                          <textarea
                            className="form-input"
                            placeholder={`محتوى ${f.name}...`}
                            value={fileCaptions[idx] || ''}
                            onChange={(e) => setFileCaptions({ ...fileCaptions, [idx]: e.target.value })}
                            style={{ minHeight: 80 }}
                          />
                        </div>
                      ))
                    ) : (
                      <div className="form-group">
                        <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          المحتوى
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={handleEnhance}
                            disabled={enhancingContent || !form.content}
                            style={{ fontSize: 12, padding: '4px 12px' }}
                          >
                            {enhancingContent ? 'جاري التحسين...' : 'تحسين بالذكاء الاصطناعي'}
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
                    )}
                  </>
                )}

                {addWizardStep === 3 && (
                  <>
                    <div className="form-group">
                      <button
                        className="btn btn-secondary"
                        onClick={handleGenerateAI}
                        disabled={generating || !form.content}
                        style={{ width: '100%' }}
                      >
                        {generating ? (
                          <span>جاري التوليد...</span>
                        ) : (
                          <span>توليد بالذكاء الاصطناعي</span>
                        )}
                      </button>
                    </div>
                    {showAiPanel && (
                      <div style={{ background: 'var(--gray-50)', padding: 12, borderRadius: 8, border: '1px solid var(--gray-200)' }}>
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
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
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
                    <div className="form-group" style={{ marginTop: 12 }}>
                      <label style={{ display: 'block', marginBottom: 6, fontWeight: 600, fontSize: 13 }}>
                        ربط بقاموس ردود (اختياري)
                      </label>
                      <select
                        className="form-input"
                        value={linkedResponseId}
                        onChange={(e) => setLinkedResponseId(e.target.value)}
                        style={{ fontSize: 13 }}
                      >
                        <option value="">— بدون ربط —</option>
                        {availableResponses.map((r) => (
                          <option key={r.id} value={r.id}>{r.keyword}</option>
                        ))}
                      </select>
                      {linkedResponseId && (
                        <div style={{ fontSize: 12, color: 'var(--primary)', marginTop: 4 }}>
                          سيتم ربط المنشور بالقاموس المحدد
                        </div>
                      )}
                    </div>
                  </>
                )}

                {addWizardStep === 4 && (
                  <>
                    <div className="form-group">
                      <ChannelGroupSelector
                        selected={selectedChannels}
                        onChange={setSelectedChannels}
                      />
                    </div>
                    <div className="wizard-summary">
                      <div className="wizard-summary-row">
                        <span>عدد الملفات</span>
                        <span>{uploadFiles.length}</span>
                      </div>
                      <div className="wizard-summary-row">
                        <span>المحتوى</span>
                        <span>{form.content ? (form.content.length > 60 ? form.content.substring(0, 60) + '...' : form.content) : '—'}</span>
                      </div>
                      <div className="wizard-summary-row">
                        <span>الكلمات المفتاحية</span>
                        <span>{selectedKeywords.length}</span>
                      </div>
                    </div>
                    {uploadProgress !== null && (
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                        <svg width="80" height="80" viewBox="0 0 36 36">
                          <circle cx="18" cy="18" r="15.9" fill="none" stroke="var(--gray-200)" strokeWidth="3" />
                          <circle
                            cx="18" cy="18" r="15.9" fill="none"
                            stroke={uploadProgress === 100 ? 'var(--success)' : 'var(--primary)'}
                            strokeWidth="3"
                            strokeDasharray={`${uploadProgress} ${100 - uploadProgress}`}
                            strokeLinecap="round"
                            transform="rotate(-90 18 18)"
                            style={{ transition: 'stroke-dasharray 0.3s ease' }}
                          />
                          <text x="18" y="18" textAnchor="middle" dy=".1em" fontSize="6" fontWeight="bold" fill="var(--text-primary)">
                            {uploadProgress}%
                          </text>
                        </svg>
                        <span style={{ fontSize: 13, color: 'var(--gray-600)' }}>
                          {uploadProgress < 100 ? 'جاري رفع الملف...' : uploadProgress === 100 && savePhase === 'تم بنجاح' ? 'تم بنجاح' : 'جاري الحفظ...'}
                        </span>
                      </div>
                    )}
                  </>
                )}
              </div>

              <div className="wizard-nav">
                {addWizardStep > 1 && (
                  <button
                    className="btn btn-secondary"
                    onClick={() => setAddWizardStep(addWizardStep - 1)}
                  >
                    السابق
                  </button>
                )}
                {addWizardStep < 4 ? (
                  <button
                    className="btn btn-primary"
                    onClick={() => setAddWizardStep(addWizardStep + 1)}
                    disabled={addWizardStep === 2 && !(perFileContent && uploadFiles.length > 0 ? Object.values(fileCaptions).some(c => c && c.trim()) : form.content?.trim())}
                  >
                    التالي
                  </button>
                ) : (
                  <button
                    className="btn btn-primary"
                    onClick={handleSave}
                    disabled={saving}
                  >
                    {saving ? 'جاري الحفظ...' : 'نشر'}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {showEditModal && (
        <div className="modal-overlay" onClick={() => { setShowEditModal(false); setEditPerFileContent(false); setEditFileCaptions({}); setEditRemovedExisting([]); setEditWizardStep(1); setEditShowAiPanel(false); setEditAiKeywords([]); setEditAiQuestions([]); setEditSelectedKeywords([]); setEditSelectedQuestions([]); setEditLinkedResponseId(''); }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>تعديل المنشور</h3>
              <button className="modal-close" onClick={() => { setShowEditModal(false); setEditPerFileContent(false); setEditFileCaptions({}); setEditRemovedExisting([]); setEditWizardStep(1); setEditShowAiPanel(false); setEditAiKeywords([]); setEditAiQuestions([]); setEditSelectedKeywords([]); setEditSelectedQuestions([]); setEditLinkedResponseId(''); }}>✕</button>
            </div>
            <div className="modal-body">
              <div className="wizard-steps">
                {(editIsPublished
                  ? [{ num: 1, label: 'المحتوى' }, { num: 3, label: 'الكلمات' }]
                  : [{ num: 1, label: 'الملفات' }, { num: 2, label: 'المحتوى' }, { num: 3, label: 'الكلمات' }, { num: 4, label: 'النشر' }]
                ).map((step, i, arr) => (
                  <React.Fragment key={step.num}>
                    <div className={`wizard-step ${editWizardStep === step.num ? 'active' : ''} ${editWizardStep > step.num ? 'completed' : ''}`}>
                      <div className="wizard-step-circle">{editWizardStep > step.num ? '✓' : step.num}</div>
                      <div className="wizard-step-label">{step.label}</div>
                    </div>
                    {i < arr.length - 1 && <div className={`wizard-connector ${editWizardStep > step.num ? 'completed' : ''}`} />}
                  </React.Fragment>
                ))}
              </div>

              <div className="wizard-content">
                {((editWizardStep === 1 && editIsPublished) || (editWizardStep === 2 && !editIsPublished)) && (
                  <>
                    <div className="form-group">
                      <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        المحتوى
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={handleEditEnhance}
                          disabled={enhancingContent || !editForm.content}
                          style={{ fontSize: 12, padding: '4px 12px' }}
                        >
                          {enhancingContent ? 'جاري التحسين...' : 'تحسين بالذكاء الاصطناعي'}
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
                    {!editIsPublished && (
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
                    )}
                    {!editIsPublished && editPerFileContent && editExistingFiles.length > 0 && (
                      <>
                        <div style={{ borderTop: '1px solid var(--gray-200)', margin: '12px 0' }} />
                        <div className="form-group">
                          <label>محتوى لكل ملف</label>
                          {editExistingFiles.map((f, idx) => {
                            if (editRemovedExisting.includes(idx)) return null;
                            return (
                              <div key={idx} className="file-content-item">
                                <label>{f.name || f.url?.split('/').pop() || `ملف ${idx + 1}`} <span style={{ color: 'var(--gray-400)' }}>(حالي)</span></label>
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
                    {!editIsPublished && editPerFileContent && editUploadFiles.length > 0 && (
                      <>
                        <div style={{ borderTop: '1px solid var(--gray-200)', margin: '12px 0' }} />
                        <div className="form-group">
                          <label>محتوى للملفات الجديدة</label>
                          {editUploadFiles.map((f, idx) => (
                            <div key={`new-${idx}`} className="file-content-item">
                              <label>{f.name}</label>
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
                  </>
                )}

                {editWizardStep === 1 && !editIsPublished && (
                  <>
                    <FileUpload
                      files={editUploadFiles}
                      setFiles={(newFiles) => { setEditUploadFiles(newFiles); setEditUploadFile(newFiles[0] || null); }}
                      asDocument={editForm.as_document}
                      setAsDocument={(val) => setEditForm({ ...editForm, as_document: val })}
                      existingFiles={editExistingFiles}
                      onRemoveExisting={setEditRemovedExisting}
                    />
                  </>
                )}

                {editWizardStep === 3 && (
                  <>
                    {(editSelectedKeywords.length > 0 || editSelectedQuestions.length > 0) && (
                      <div style={{ background: 'var(--gray-50)', padding: 12, borderRadius: 8, border: '1px solid var(--gray-200)', marginBottom: 12 }}>
                        <label style={{ fontWeight: 600, marginBottom: 8, display: 'block' }}>الكلمات المحفوظة</label>
                        {editSelectedKeywords.length > 0 && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: editSelectedQuestions.length > 0 ? 10 : 0 }}>
                            {editSelectedKeywords.map((kw, i) => (
                              <span key={i} style={{ padding: '4px 10px', borderRadius: 16, fontSize: 12, background: 'var(--primary)', color: 'white' }}>
                                {kw}
                              </span>
                            ))}
                          </div>
                        )}
                        {editSelectedQuestions.length > 0 && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                            {editSelectedQuestions.map((q, i) => (
                              <span key={i} style={{ padding: '4px 10px', borderRadius: 16, fontSize: 12, background: 'var(--success, #22c55e)', color: 'white' }}>
                                {q}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                    <div className="form-group">
                      <button
                        className="btn btn-secondary"
                        onClick={handleEditGenerateAI}
                        disabled={editGenerating || !editForm.content}
                        style={{ width: '100%' }}
                      >
                        {editGenerating ? (
                          <span>جاري التوليد...</span>
                        ) : (
                          <span>توليد بالذكاء الاصطناعي</span>
                        )}
                      </button>
                    </div>
                    {editShowAiPanel && (
                      <div style={{ background: 'var(--gray-50)', padding: 12, borderRadius: 8, border: '1px solid var(--gray-200)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                          <label style={{ fontWeight: 600, margin: 0 }}>الكلمات المفتاحية المقترحة</label>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={handleEditGenerateAI}
                            disabled={editGenerating}
                            style={{ fontSize: 12, padding: '4px 12px' }}
                          >
                            {editGenerating ? 'جاري التوليد...' : 'إعادة التوليد'}
                          </button>
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
                          {editAiKeywords.map((kw, i) => (
                            <span
                              key={i}
                              onClick={() => toggleEditKeyword(kw)}
                              style={{
                                padding: '6px 12px',
                                borderRadius: 20,
                                fontSize: 13,
                                cursor: 'pointer',
                                background: editSelectedKeywords.includes(kw) ? 'var(--primary)' : 'var(--gray-200)',
                                color: editSelectedKeywords.includes(kw) ? 'white' : 'var(--gray-700)',
                                transition: 'all 0.2s',
                                border: 'none',
                              }}
                            >
                              {kw}
                            </span>
                          ))}
                          {editAiKeywords.length === 0 && (
                            <span style={{ fontSize: 13, color: 'var(--gray-400)' }}>لا توجد كلمات مفتاحية</span>
                          )}
                        </div>
                        <label style={{ fontWeight: 600, marginBottom: 8, display: 'block' }}>الأسئلة المقترحة</label>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
                          {editAiQuestions.map((q, i) => (
                            <span
                              key={i}
                              onClick={() => toggleEditQuestion(q)}
                              style={{
                                padding: '6px 12px',
                                borderRadius: 20,
                                fontSize: 13,
                                cursor: 'pointer',
                                background: editSelectedQuestions.includes(q) ? 'var(--primary)' : 'var(--gray-200)',
                                color: editSelectedQuestions.includes(q) ? 'white' : 'var(--gray-700)',
                                transition: 'all 0.2s',
                                border: 'none',
                              }}
                            >
                              {q}
                            </span>
                          ))}
                          {editAiQuestions.length === 0 && (
                            <span style={{ fontSize: 13, color: 'var(--gray-400)' }}>لا توجد أسئلة مقترحة</span>
                          )}
                        </div>
                      </div>
                    )}
                    <div className="form-group" style={{ marginTop: 12 }}>
                      <label style={{ display: 'block', marginBottom: 6, fontWeight: 600, fontSize: 13 }}>
                        ربط بقاموس ردود (اختياري)
                      </label>
                      <select
                        className="form-input"
                        value={editLinkedResponseId}
                        onChange={(e) => setEditLinkedResponseId(e.target.value)}
                        style={{ fontSize: 13 }}
                      >
                        <option value="">— بدون ربط —</option>
                        {editAvailableResponses.map((r) => (
                          <option key={r.id} value={r.id}>{r.keyword}</option>
                        ))}
                      </select>
                      {editLinkedResponseId && (
                        <div style={{ fontSize: 12, color: 'var(--primary)', marginTop: 4 }}>
                          سيتم ربط المنشور بالقاموس المحدد
                        </div>
                      )}
                    </div>
                  </>
                )}

                {editWizardStep === 4 && !editIsPublished && (
                  <>
                    <div className="form-group">
                      <ChannelGroupSelector
                        selected={editSelectedChannels}
                        onChange={setEditSelectedChannels}
                      />
                    </div>
                    <div className="wizard-summary">
                      <div className="wizard-summary-row">
                        <span>عدد الملفات</span>
                        <span>{editExistingFiles.filter((_, i) => !editRemovedExisting.includes(i)).length + editUploadFiles.length}</span>
                      </div>
                      <div className="wizard-summary-row">
                        <span>المحتوى</span>
                        <span>{editForm.content ? (editForm.content.length > 60 ? editForm.content.substring(0, 60) + '...' : editForm.content) : '—'}</span>
                      </div>
                      <div className="wizard-summary-row">
                        <span>الكلمات المفتاحية</span>
                        <span>{editSelectedKeywords.length}</span>
                      </div>
                    </div>
                  </>
                )}
              </div>

              <div className="wizard-nav">
                {editWizardStep > 1 && (
                  <button
                    className="btn btn-secondary"
                    onClick={() => {
                      if (editIsPublished && editWizardStep === 3) {
                        setEditWizardStep(1);
                      } else {
                        setEditWizardStep(editWizardStep - 1);
                      }
                    }}
                  >
                    السابق
                  </button>
                )}
                {editWizardStep < (editIsPublished ? 3 : 4) ? (
                  <button
                    className="btn btn-primary"
                    onClick={() => {
                      if (editIsPublished && editWizardStep === 1) {
                        setEditWizardStep(3);
                      } else {
                        setEditWizardStep(editWizardStep + 1);
                      }
                    }}
                    disabled={(editIsPublished ? editWizardStep === 1 : editWizardStep === 2) && !editForm.content?.trim()}
                  >
                    التالي
                  </button>
                ) : (
                  <button
                    className="btn btn-primary"
                    onClick={handleEditSave}
                    disabled={saving || (!editIsPublished && editSelectedChannels.length === 0)}
                  >
                    {saving ? 'جاري الحفظ...' : 'حفظ التعديلات'}
                  </button>
                )}
              </div>
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

      {saving && savePhase && (
        <div className="save-overlay">
          <div className="save-progress-container">
            <div className="save-circle-wrapper">
              <svg className="save-circle-bg" viewBox="0 0 128 128">
                <circle cx="64" cy="64" r="60" />
              </svg>
              <svg className="save-circle-progress" viewBox="0 0 128 128">
                <circle
                  cx="64" cy="64" r="60"
                  style={{
                    strokeDashoffset: uploadProgress !== null
                      ? 377 - (377 * uploadProgress) / 100
                      : 377
                  }}
                />
              </svg>
              {savePhase === 'تم بنجاح' ? (
                <svg className="save-success-icon" viewBox="0 0 52 52">
                  <circle cx="26" cy="26" r="25" fill="none" stroke="var(--primary)" strokeWidth="2" />
                  <path className="save-success-check" fill="none" stroke="var(--primary)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" d="M14 27l7 7 16-16" />
                </svg>
              ) : uploadProgress !== null ? (
                <div className="save-circle-percent">{Math.round(uploadProgress)}%</div>
              ) : (
                <svg className="save-circle-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
                  <polyline points="17 21 17 13 7 13 7 21" />
                  <polyline points="7 3 7 8 15 8" />
                </svg>
              )}
            </div>
            <div className="save-info">
              <div className="save-phase" key={savePhase}>{savePhase}</div>
              {uploadProgress !== null && savePhase !== 'تم بنجاح' && (
                <div className="save-detail">
                  {(() => {
                    const count = showEditModal ? editUploadFiles.length : uploadFiles.length;
                    return count > 0 ? `${count} ${count === 1 ? 'ملف' : 'ملفات'}` : null;
                  })()}
                  {uploadProgress < 100 ? ` — ${Math.round(uploadProgress)}%` : ''}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </>
  );
}
