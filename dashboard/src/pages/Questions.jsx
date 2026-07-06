import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useConfirm } from '../components/ConfirmDialog';
import { useToast } from '../components/ToastContext';

export default function Questions() {
  const { confirm } = useConfirm();
  const { showToast } = useToast();
  const [questions, setQuestions] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [form, setForm] = useState({ question: '', answer: '', category: '', keywords: '', file: null, file_url: '', file_type: '', as_document: false });
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadQuestions();
  }, []);

  const loadQuestions = async () => {
    try {
      const data = await api.getQuestions();
      setQuestions(data);
    } catch (err) {
      console.error('Failed to load questions:', err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = questions.filter(
    (q) => q.question?.includes(search) || q.answer?.includes(search) || q.category?.includes(search)
  );

  const handleSave = async () => {
    if (!form.question || !form.answer) return;
    setSaving(true);
    try {
      if (editItem) {
        if (form.file) {
          const formData = new FormData();
          formData.append('question', form.question);
          formData.append('answer', form.answer);
          if (form.category) formData.append('category', form.category);
          if (form.keywords) formData.append('keywords', form.keywords);
          formData.append('file', form.file);
          formData.append('as_document', form.as_document);
          const updated = await api.updateQuestionWithFile(editItem.id, formData);
          setQuestions(questions.map((q) => q.id === editItem.id ? updated : q));
        } else {
          const payload = { question: form.question, answer: form.answer, category: form.category, keywords: form.keywords, as_document: form.as_document };
          if (form.file_url !== editItem.file_url) {
            payload.file_url = form.file_url || null;
            payload.file_type = form.file_type || null;
          }
          const updated = await api.updateQuestion(editItem.id, payload);
          setQuestions(questions.map((q) => q.id === editItem.id ? updated : q));
        }
      } else {
        if (form.file) {
          const formData = new FormData();
          formData.append('question', form.question);
          formData.append('answer', form.answer);
          if (form.category) formData.append('category', form.category);
          if (form.keywords) formData.append('keywords', form.keywords);
          formData.append('file', form.file);
          formData.append('as_document', form.as_document);
          const newItem = await api.addQuestionWithFile(formData);
          setQuestions([...questions, newItem]);
        } else {
          const newItem = await api.addQuestion(form);
          setQuestions([...questions, newItem]);
        }
      }
      setForm({ question: '', answer: '', category: '', keywords: '', file: null, file_url: '', file_type: '', as_document: false });
      setEditItem(null);
      setShowModal(false);
    } catch (err) {
      console.error('Failed to save question:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (item) => {
    setEditItem(item);
    setForm({
      question: item.question,
      answer: item.answer,
      category: item.category || '',
      keywords: item.keywords || '',
      file: null,
      file_url: item.file_url || '',
      file_type: item.file_type || '',
      as_document: item.as_document || false,
    });
    setShowModal(true);
  };

  const handleDelete = async (id) => {
    const ok = await confirm('هل أنت متأكد من حذف هذا السؤال؟');
    if (!ok) return;
    try {
      await api.deleteQuestion(id);
      setQuestions(questions.filter((q) => q.id !== id));
      showToast('تم حذف السؤال بنجاح', 'success');
    } catch (err) {
      console.error('Failed to delete question:', err);
      showToast('فشل حذف السؤال', 'error');
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
                placeholder="بحث في الأسئلة..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <button className="btn btn-primary" onClick={() => { setEditItem(null); setForm({ question: '', answer: '', category: '', keywords: '', file: null, file_url: '', file_type: '', as_document: false }); setShowModal(true); }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              إضافة سؤال جديد
            </button>
          </div>

          {/* Desktop Table */}
          <div className="table-container desktop-only">
            <table>
              <thead>
                <tr>
                  <th>السؤال</th>
                  <th>الإجابة</th>
                  <th>المرفق</th>
                  <th>طريقة الإرسال</th>
                  <th>الفئة</th>
                  <th>الكلمات المفتاحية</th>
                  <th>إجراءات</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr key={item.id}>
                    <td><strong>{item.question}</strong></td>
                    <td style={{ maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.answer?.substring(0, 80)}...
                    </td>
                    <td style={{ fontSize: 13, color: 'var(--gray-500)' }}>
                      {item.file_url ? (
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          📎 {item.file_type === 'photo' ? 'صورة' : item.file_type === 'video' ? 'فيديو' : 'ملف'}
                        </span>
                      ) : '-'}
                    </td>
                    <td style={{ fontSize: 13, color: 'var(--gray-500)' }}>
                      {item.file_url ? (item.as_document ? 'كمرفق' : 'عرض مباشر') : '-'}
                    </td>
                    <td>
                      {item.category ? (
                        <span className="status-badge active">{item.category}</span>
                      ) : (
                        <span style={{ color: 'var(--gray-400)' }}>-</span>
                      )}
                    </td>
                    <td style={{ maxWidth: 200, fontSize: 13, color: 'var(--gray-500)' }}>
                      {item.keywords || '-'}
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
                  <circle cx="12" cy="12" r="10" />
                  <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
                <h4>لا توجد أسئلة</h4>
                <p>ابدأ بإضافة أسئلة شائعة للبوت</p>
              </div>
            )}
          </div>

          {/* Mobile Cards */}
          <div className="mobile-cards">
            {filtered.map((item) => (
              <div key={item.id} className="mobile-card">
                <div className="mobile-card-header">
                  <strong>{item.question}</strong>
                  {item.category && (
                    <span className="status-badge active">{item.category}</span>
                  )}
                </div>
                <div className="mobile-card-body">
                  <p style={{ fontSize: 13, color: 'var(--gray-600)', marginBottom: 8 }}>
                    {item.answer?.substring(0, 100)}...
                  </p>
                  {item.keywords && (
                    <p style={{ fontSize: 11, color: 'var(--gray-400)' }}>
                      🔑 {item.keywords}
                    </p>
                  )}
                  {item.file_url && (
                    <p style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 4 }}>
                      📎 {item.file_type === 'photo' ? 'صورة' : item.file_type === 'video' ? 'فيديو' : 'ملف'}
                      {item.as_document ? ' (كمرفق)' : ' (عرض مباشر)'}
                    </p>
                  )}
                </div>
                <div className="mobile-card-meta">
                  <button className="btn btn-secondary btn-sm" onClick={() => handleEdit(item)}>
                    تعديل
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
                  <circle cx="12" cy="12" r="10" />
                  <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
                <h4>لا توجد أسئلة</h4>
                <p>ابدأ بإضافة أسئلة شائعة للبوت</p>
              </div>
            )}
          </div>
        </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editItem ? 'تعديل السؤال' : 'إضافة سؤال جديد'}</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>السؤال</label>
                <input
                  className="form-input"
                  placeholder="اكتب السؤال هنا..."
                  value={form.question}
                  onChange={(e) => setForm({ ...form, question: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>الإجابة</label>
                <textarea
                  className="form-input"
                  placeholder="اكتب الإجابة هنا..."
                  value={form.answer}
                  onChange={(e) => setForm({ ...form, answer: e.target.value })}
                  style={{ minHeight: 120 }}
                />
              </div>
              <div className="form-group">
                <label>الفئة</label>
                <input
                  className="form-input"
                  placeholder="مثال: أكاديمي، تسجيل، معاملات"
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>الكلمات المفتاحية</label>
                <input
                  className="form-input"
                  placeholder="مثال: تسجيل,قوائم,جدول"
                  value={form.keywords}
                  onChange={(e) => setForm({ ...form, keywords: e.target.value })}
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
