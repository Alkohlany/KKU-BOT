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
  const [form, setForm] = useState({ question: '', answer: '', keywords: '' });
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
    (q) => q.question?.includes(search) || q.answer?.includes(search) || q.keywords?.includes(search)
  );

  const handleSave = async () => {
    if (!form.question || !form.answer) return;
    setSaving(true);
    try {
      if (editItem) {
        const payload = { question: form.question, answer: form.answer, keywords: form.keywords };
        const updated = await api.updateQuestion(editItem.id, payload);
        setQuestions(questions.map((q) => q.id === editItem.id ? updated : q));
      } else {
        const newItem = await api.addQuestion(form);
        setQuestions([...questions, newItem]);
      }
      setForm({ question: '', answer: '', keywords: '' });
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
      keywords: item.keywords || '',
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
            <button className="btn btn-primary" onClick={() => { setEditItem(null); setForm({ question: '', answer: '', keywords: '' }); setShowModal(true); }}>
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
                <label>الكلمات المفتاحية</label>
                <input
                  className="form-input"
                  placeholder="مثال: تسجيل,قوائم,جدول"
                  value={form.keywords}
                  onChange={(e) => setForm({ ...form, keywords: e.target.value })}
                />
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
