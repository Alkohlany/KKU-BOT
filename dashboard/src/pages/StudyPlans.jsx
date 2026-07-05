import React, { useState, useEffect } from 'react';
import api from '../services/api';

export default function StudyPlans() {
  const [plans, setPlans] = useState([]);
  const [groups, setGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', college: '', level: '', file: null, group_id: '' });
  const [groupForm, setGroupForm] = useState({ title: '', description: '', group_tag: '' });
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [plansData, groupsData] = await Promise.all([
        api.getStudyPlans(),
        api.getStudyPlanGroups()
      ]);
      setPlans(plansData);
      setGroups(groupsData);
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = plans.filter(
    (p) => p.title?.includes(search) || p.college?.includes(search) || p.description?.includes(search)
  );

  const filteredGroups = groups.filter(
    (g) => g.title?.includes(search) || g.description?.includes(search)
  );

  const handleSavePlan = async () => {
    if (!form.title) return;
    setSaving(true);
    try {
      let newItem;
      if (form.file) {
        const formDataObj = new FormData();
        formDataObj.append('title', form.title);
        formDataObj.append('description', form.description);
        formDataObj.append('faculty', form.college);
        formDataObj.append('level', form.level);
        if (form.group_id) {
          formDataObj.append('group_id', form.group_id);
        }
        formDataObj.append('file', form.file);
        newItem = await api.addStudyPlanWithFile(formDataObj);
      } else {
        newItem = await api.addStudyPlan({
          title: form.title,
          description: form.description,
          faculty: form.college,
          level: form.level,
          group_id: form.group_id || null,
        });
      }
      setPlans([...plans, newItem]);
      setForm({ title: '', description: '', college: '', level: '', file: null, group_id: '' });
      setShowPlanModal(false);
    } catch (err) {
      console.error('Failed to save study plan:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveGroup = async () => {
    if (!groupForm.title) return;
    setSaving(true);
    try {
      const newGroup = await api.addStudyPlanGroup(groupForm);
      setGroups([...groups, newGroup]);
      setGroupForm({ title: '', description: '', group_tag: '' });
      setShowGroupModal(false);
    } catch (err) {
      console.error('Failed to save group:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDeletePlan = async (id) => {
    if (!window.confirm('هل أنت متأكد من حذف هذه الخطة؟')) return;
    try {
      await api.deleteStudyPlan(id);
      setPlans(plans.filter((p) => p.id !== id));
    } catch (err) {
      console.error('Failed to delete study plan:', err);
    }
  };

  const handleDeleteGroup = async (id) => {
    if (!window.confirm('هل أنت متأكد من حذف هذه المجموعة؟ سيتم حذف جميع الخطط التابعة لها.')) return;
    try {
      await api.deleteStudyPlanGroup(id);
      setGroups(groups.filter((g) => g.id !== id));
      setPlans(plans.filter((p) => p.group_id !== id));
    } catch (err) {
      console.error('Failed to delete group:', err);
    }
  };

  const handlePublishGroup = async (groupId) => {
    setPublishing(groupId);
    try {
      const result = await api.publishGroupPlans(groupId);
      alert(result.message || 'تم النشر بنجاح');
      await loadData();
    } catch (err) {
      console.error('Failed to publish group plans:', err);
      alert('حدث خطأ أثناء النشر');
    } finally {
      setPublishing(null);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 20, color: '#888' }}>
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
                placeholder="بحث في المجموعات والخطط..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button className="btn btn-secondary" onClick={() => { setGroupForm({ title: '', description: '', group_tag: '' }); setShowGroupModal(true); }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                </svg>
                إضافة مجموعة
              </button>
              <button className="btn btn-primary" onClick={() => { setForm({ title: '', description: '', college: '', level: '', file: null, group_id: '' }); setShowPlanModal(true); }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                إضافة خطة جديدة
              </button>
            </div>
          </div>

          {/* Groups Section */}
          <div style={{ marginBottom: 24, padding: '0 24px' }}>
            <h3 style={{ marginBottom: 12, color: 'var(--gray-700)' }}>📂 المجموعات</h3>
            {filteredGroups.length > 0 ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(250px, 100%), 1fr))', gap: 12 }}>
                {filteredGroups.map((group) => (
                  <div
                    key={group.id}
                    style={{
                      padding: 16,
                      borderRadius: 8,
                      border: selectedGroup === group.id ? '2px solid var(--primary)' : '1px solid var(--gray-200)',
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                    onClick={() => setSelectedGroup(selectedGroup === group.id ? null : group.id)}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <strong>{group.title}</strong>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button
                          className="btn btn-primary btn-icon"
                          style={{ padding: '4px 8px', fontSize: 11 }}
                          disabled={publishing === group.id}
                          onClick={(e) => { e.stopPropagation(); handlePublishGroup(group.id); }}
                        >
                          {publishing === group.id ? '...' : 'نشر'}
                        </button>
                        <button
                          className="btn btn-danger btn-icon"
                          style={{ padding: '4px 8px' }}
                          onClick={(e) => { e.stopPropagation(); handleDeleteGroup(group.id); }}
                        >
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                          </svg>
                        </button>
                      </div>
                    </div>
                    {group.description && (
                      <p style={{ margin: '8px 0 0', color: 'var(--gray-500)', fontSize: 13 }}>
                        {group.description}
                      </p>
                    )}
                    <span style={{ fontSize: 12, color: 'var(--gray-400)' }}>
                      {plans.filter(p => p.group_id === group.id).length} خطط
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: 'var(--gray-400)', fontSize: 14 }}>لا توجد مجموعات بعد</p>
            )}
          </div>

          {/* Plans Section */}
          <div style={{ padding: '0 24px' }}>
            <h3 style={{ marginBottom: 12, color: 'var(--gray-700)' }}>
              📋 الخطط {selectedGroup ? `- ${groups.find(g => g.id === selectedGroup)?.title || ''}` : ''}
            </h3>

            {/* Desktop Table */}
            <div className="table-container desktop-only">
              <table>
                <thead>
                  <tr>
                    <th>العنوان</th>
                    <th>الوصف</th>
                    <th>المجموعة</th>
                    <th>الكلية</th>
                    <th>المستوى</th>
                    <th>إجراءات</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered
                    .filter(p => !selectedGroup || p.group_id === selectedGroup)
                    .map((item) => (
                    <tr key={item.id}>
                      <td><strong>{item.title}</strong></td>
                      <td style={{ maxWidth: 200, fontSize: 13 }}>{item.description?.substring(0, 60)}...</td>
                      <td>
                        <span className="status-badge active">
                          {groups.find(g => g.id === item.group_id)?.title || '-'}
                        </span>
                      </td>
                      <td>{item.college || '-'}</td>
                      <td>{item.level || '-'}</td>
                      <td>
                        <button className="btn btn-danger btn-icon" onClick={() => handleDeletePlan(item.id)}>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filtered.filter(p => !selectedGroup || p.group_id === selectedGroup).length === 0 && (
                <div className="empty-state">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                    <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
                  </svg>
                  <h4>لا توجد خطط دراسية</h4>
                  <p>ابدأ بإضافة خطط دراسية للطلاب</p>
                </div>
              )}
            </div>

            {/* Mobile Cards */}
            <div className="mobile-cards">
              {filtered
                .filter(p => !selectedGroup || p.group_id === selectedGroup)
                .map((item) => (
                <div key={item.id} className="mobile-card">
                  <div className="mobile-card-header">
                    <strong>{item.title}</strong>
                    <button className="btn btn-danger btn-sm" onClick={() => handleDeletePlan(item.id)}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                    </button>
                  </div>
                  <div className="mobile-card-body">
                    {item.description && <p>{item.description.substring(0, 100)}...</p>}
                    <div className="mobile-card-meta">
                      <span>المجموعة: {groups.find(g => g.id === item.group_id)?.title || '-'}</span>
                      <span>الكلية: {item.college || '-'}</span>
                      <span>المستوى: {item.level || '-'}</span>
                    </div>
                  </div>
                </div>
              ))}
              {filtered.filter(p => !selectedGroup || p.group_id === selectedGroup).length === 0 && (
                <div className="empty-state">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                    <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
                  </svg>
                  <h4>لا توجد خطط دراسية</h4>
                  <p>ابدأ بإضافة خطط دراسية للطلاب</p>
                </div>
              )}
            </div>
          </div>
        </div>

      {/* Add Group Modal */}
      {showGroupModal && (
        <div className="modal-overlay" onClick={() => setShowGroupModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>إضافة مجموعة جديدة</h3>
              <button className="modal-close" onClick={() => setShowGroupModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>اسم المجموعة</label>
                <input
                  className="form-input"
                  placeholder="مثال: الخطط الصحية"
                  value={groupForm.title}
                  onChange={(e) => setGroupForm({ ...groupForm, title: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>الوصف</label>
                <textarea
                  className="form-input"
                  placeholder="وصف المجموعة..."
                  value={groupForm.description}
                  onChange={(e) => setGroupForm({ ...groupForm, description: e.target.value })}
                  style={{ minHeight: 80 }}
                />
              </div>
              <div className="form-group">
                <label>الهاشتاق (بدون #)</label>
                <input
                  className="form-input"
                  placeholder="مثال: صحيح"
                  value={groupForm.group_tag}
                  onChange={(e) => setGroupForm({ ...groupForm, group_tag: e.target.value })}
                />
                <small style={{ color: 'var(--gray-500)', marginTop: 4, display: 'block' }}>
                  سيظهر في المنشور كمثال: #صحي
                </small>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={handleSaveGroup} disabled={saving}>
                {saving ? 'جاري الحفظ...' : 'إضافة'}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowGroupModal(false)}>إلغاء</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Plan Modal */}
      {showPlanModal && (
        <div className="modal-overlay" onClick={() => setShowPlanModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>إضافة خطة جديدة</h3>
              <button className="modal-close" onClick={() => setShowPlanModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>المجموعة</label>
                <select
                  className="form-input"
                  value={form.group_id}
                  onChange={(e) => setForm({ ...form, group_id: e.target.value })}
                >
                  <option value="">بدون مجموعة</option>
                  {groups.map((g) => (
                    <option key={g.id} value={g.id}>{g.title}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>العنوان</label>
                <input
                  className="form-input"
                  placeholder="مثال: خطة تقنية تخدير"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>الوصف</label>
                <textarea
                  className="form-input"
                  placeholder="وصف الخطة الدراسية..."
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  style={{ minHeight: 100 }}
                />
              </div>
              <div className="form-group">
                <label>الكلية</label>
                <input
                  className="form-input"
                  placeholder="مثال: كلية الطب"
                  value={form.college}
                  onChange={(e) => setForm({ ...form, college: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>المستوى</label>
                <select
                  className="form-input"
                  value={form.level}
                  onChange={(e) => setForm({ ...form, level: e.target.value })}
                >
                  <option value="">اختر المستوى</option>
                  <option value="المستوى الأول">المستوى الأول</option>
                  <option value="المستوى الثاني">المستوى الثاني</option>
                  <option value="المستوى الثالث">المستوى الثالث</option>
                  <option value="المستوى الرابع">المستوى الرابع</option>
                  <option value="المستوى الخامس">المستوى الخامس</option>
                  <option value="الدراسات العليا">الدراسات العليا</option>
                </select>
              </div>
              <div className="form-group">
                <label>الملف المرفق (اختياري)</label>
                <input
                  type="file"
                  accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
                  className="form-input"
                  onChange={(e) => setForm({ ...form, file: e.target.files[0] || null })}
                />
                {form.file && (
                  <small style={{ color: 'var(--gray-500)', marginTop: 4, display: 'block' }}>
                    {form.file.name}
                  </small>
                )}
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={handleSavePlan} disabled={saving}>
                {saving ? 'جاري الحفظ...' : 'إضافة'}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowPlanModal(false)}>إلغاء</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
