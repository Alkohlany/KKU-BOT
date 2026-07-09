import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useConfirm } from '../components/ConfirmDialog';
import { useToast } from '../components/ToastContext';

export default function ReplyDictionary() {
  const { confirm } = useConfirm();
  const { showToast } = useToast();
  const [responses, setResponses] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [news, setNews] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [editType, setEditType] = useState('keyword');
  const [formType, setFormType] = useState('keyword');
  const [form, setForm] = useState({ keyword: '', question: '', keywords: '', news_id: '' });
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    try {
      const [resData, qData, nData] = await Promise.all([
        api.getResponses(),
        api.getQuestions(),
        api.getNews(),
      ]);
      setResponses(resData || []);
      setQuestions(qData || []);
      setNews(nData || []);
    } catch (err) {
      console.error('Failed to load data:', err);
      showToast('فشل تحميل البيانات', 'error');
    } finally {
      setLoading(false);
    }
  };

  const unified = [
    ...responses.map((r) => ({ ...r, _type: 'keyword' })),
    ...questions.map((q) => ({ ...q, _type: 'question' })),
  ];

  const filtered = unified.filter((item) => {
    if (!search) return true;
    if (item._type === 'keyword') {
      return item.keyword?.includes(search);
    }
    return item.question?.includes(search) || item.keywords?.includes(search);
  });

  const handleOpenAdd = () => {
    setEditItem(null);
    setEditType('keyword');
    setFormType('keyword');
    setForm({ keyword: '', question: '', keywords: '', news_id: '' });
    setShowModal(true);
  };

  const handleEdit = (item) => {
    setEditItem(item);
    setEditType(item._type);
    setFormType(item._type);
    if (item._type === 'keyword') {
      setForm({ keyword: item.keyword || '', question: '', keywords: '', news_id: item.news_id || '' });
    } else {
      setForm({ keyword: '', question: item.question || '', keywords: item.keywords || '', news_id: item.news_id || '' });
    }
    setShowModal(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editItem) {
        if (editType === 'keyword') {
          const payload = { keyword: form.keyword, news_id: form.news_id || null };
          const updated = await api.updateResponse(editItem.id, payload);
          setResponses(responses.map((r) => r.id === editItem.id ? updated : r));
        } else {
          const payload = { question: form.question, answer: 'تم الرد عبر المنشور', keywords: form.keywords, news_id: form.news_id || null };
          const updated = await api.updateQuestion(editItem.id, payload);
          setQuestions(questions.map((q) => q.id === editItem.id ? updated : q));
        }
        showToast('تم التعديل بنجاح', 'success');
      } else {
        if (formType === 'keyword') {
          if (!form.keyword) { setSaving(false); return; }
          const payload = { keyword: form.keyword, response: '', news_id: form.news_id || null };
          const newItem = await api.addResponse(payload);
          setResponses([...responses, newItem]);
        } else {
          if (!form.question) { setSaving(false); return; }
          const payload = { question: form.question, answer: 'تم الرد عبر المنشور', keywords: form.keywords, news_id: form.news_id || null };
          const newItem = await api.addQuestion(payload);
          setQuestions([...questions, newItem]);
        }
        showToast('تمت الإضافة بنجاح', 'success');
      }
      setForm({ keyword: '', question: '', keywords: '', news_id: '' });
      setEditItem(null);
      setShowModal(false);
    } catch (err) {
      console.error('Failed to save:', err);
      showToast('فشل الحفظ', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (item) => {
    const label = item._type === 'keyword' ? 'هذا الكلمة المفتاحية' : 'هذا السؤال';
    const ok = await confirm(`هل أنت متأكد من حذف ${label}؟`);
    if (!ok) return;
    try {
      if (item._type === 'keyword') {
        await api.deleteResponse(item.id);
        setResponses(responses.filter((r) => r.id !== item.id));
      } else {
        await api.deleteQuestion(item.id);
        setQuestions(questions.filter((q) => q.id !== item.id));
      }
      showToast('تم الحذف بنجاح', 'success');
    } catch (err) {
      console.error('Failed to delete:', err);
      showToast('فشل الحذف', 'error');
    }
  };

  const getNewsTitle = (newsId) => {
    if (!newsId) return null;
    const found = news.find((n) => n.id === newsId);
    return found ? (found.content || '').substring(0, 50) : null;
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
              placeholder="بحث في القاموس..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button className="btn btn-primary" onClick={handleOpenAdd}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            إضافة جديد
          </button>
        </div>

        {/* Desktop Table */}
        <div className="table-container desktop-only">
          <table>
            <thead>
              <tr>
                <th>النوع</th>
                <th>الكلمة المفتاحية / السؤال</th>
                <th>المنشور المرتبط</th>
                <th>الحالة</th>
                <th>إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={`${item._type}-${item.id}`}>
                  <td>
                    <span className={`status-badge ${item._type === 'keyword' ? 'active' : 'inactive'}`}>
                      {item._type === 'keyword' ? 'كلمة مفتاحية' : 'سؤال'}
                    </span>
                  </td>
                  <td>
                    <strong>
                      {item._type === 'keyword' ? item.keyword : item.question}
                    </strong>
                    {item._type === 'question' && item.keywords && (
                      <div style={{ fontSize: 12, color: 'var(--gray-400)', marginTop: 2 }}>
                        🔑 {item.keywords}
                      </div>
                    )}
                  </td>
                  <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {getNewsTitle(item.news_id) || <span style={{ color: 'var(--gray-400)' }}>-</span>}
                  </td>
                  <td>
                    {item._type === 'keyword' ? (
                      <span className={`status-badge ${item.enabled ? 'active' : 'inactive'}`}>
                        {item.enabled ? 'مفعّل' : 'معطّل'}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--gray-400)', fontSize: 13 }}>-</span>
                    )}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button className="btn btn-secondary btn-icon" onClick={() => handleEdit(item)}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
                      </button>
                      <button className="btn btn-danger btn-icon" onClick={() => handleDelete(item)}>
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
              <h4>لا توجد عناصر</h4>
              <p>اضغط على "إضافة جديد" لإضافة كلمة مفتاحية أو سؤال</p>
            </div>
          )}
        </div>

        {/* Mobile Cards */}
        <div className="mobile-cards">
          {filtered.map((item) => (
            <div key={`${item._type}-${item.id}`} className="mobile-card">
              <div className="mobile-card-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span className={`status-badge ${item._type === 'keyword' ? 'active' : 'inactive'}`}>
                    {item._type === 'keyword' ? 'كلمة مفتاحية' : 'سؤال'}
                  </span>
                  <strong style={{ fontSize: 14 }}>
                    {item._type === 'keyword' ? item.keyword : item.question}
                  </strong>
                </div>
                {item._type === 'keyword' && (
                  <span className={`status-badge ${item.enabled ? 'active' : 'inactive'}`}>
                    {item.enabled ? 'مفعّل' : 'معطّل'}
                  </span>
                )}
              </div>
              <div className="mobile-card-body">
                {item._type === 'question' && item.keywords && (
                  <p style={{ fontSize: 12, color: 'var(--gray-400)', marginBottom: 4 }}>
                    🔑 {item.keywords}
                  </p>
                )}
                {getNewsTitle(item.news_id) && (
                  <p style={{ fontSize: 12, color: 'var(--gray-500)', margin: 0 }}>
                   {getNewsTitle(item.news_id)}
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
                <button className="btn btn-danger btn-sm" onClick={() => handleDelete(item)}>
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
              <h4>لا توجد عناصر</h4>
              <p>اضغط على "إضافة جديد" لإضافة كلمة مفتاحية أو سؤال</p>
            </div>
          )}
        </div>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editItem ? 'تعديل' : 'إضافة جديد'}</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              {/* Type Radio */}
              <div className="form-group">
                <label>النوع</label>
                <div style={{ display: 'flex', gap: 16, marginTop: 4 }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 14 }}>
                    <input
                      type="radio"
                      name="formType"
                      value="keyword"
                      checked={formType === 'keyword'}
                      onChange={() => setFormType('keyword')}
                      disabled={!!editItem}
                      style={{ width: 16, height: 16 }}
                    />
                    كلمة مفتاحية
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 14 }}>
                    <input
                      type="radio"
                      name="formType"
                      value="question"
                      checked={formType === 'question'}
                      onChange={() => setFormType('question')}
                      disabled={!!editItem}
                      style={{ width: 16, height: 16 }}
                    />
                    سؤال
                  </label>
                </div>
              </div>

              {/* Keyword Input */}
              {formType === 'keyword' && (
                <div className="form-group">
                  <label>الكلمة المفتاحية</label>
                  <input
                    className="form-input"
                    placeholder="مثال: مواعيد, جدول, امتحانات..."
                    value={form.keyword}
                    onChange={(e) => setForm({ ...form, keyword: e.target.value })}
                  />
                </div>
              )}

              {/* Question Inputs */}
              {formType === 'question' && (
                <>
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
                    <label>الكلمات المفتاحية (مفصولة بفاصلة)</label>
                    <input
                      className="form-input"
                      placeholder="مثال: تسجيل, قوائم, جدول"
                      value={form.keywords}
                      onChange={(e) => setForm({ ...form, keywords: e.target.value })}
                    />
                  </div>
                </>
              )}

              {/* News Dropdown */}
              <div className="form-group">
                <label>المنشور المرتبط (اختياري)</label>
                <select
                  className="form-input"
                  value={form.news_id}
                  onChange={(e) => setForm({ ...form, news_id: e.target.value })}
                >
                  <option value="">— بدون منشور —</option>
                  {news.map((n) => (
                    <option key={n.id} value={n.id}>{(n.content || '').substring(0, 60)}</option>
                  ))}
                </select>
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
