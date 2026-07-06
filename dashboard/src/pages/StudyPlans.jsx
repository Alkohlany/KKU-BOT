import React, { useState, useEffect } from 'react';
import api from '../services/api';

export default function StudyPlans() {
  const [plans, setPlans] = useState([]);
  const [groups, setGroups] = useState([]);
  const [view, setView] = useState('groups');
  const [activeGroup, setActiveGroup] = useState(null);
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

  const openFolder = (group) => {
    setActiveGroup(group);
    setView('folder');
    setSearch('');
  };

  const backToGroups = () => {
    setActiveGroup(null);
    setView('groups');
    setSearch('');
  };

  const filteredGroups = groups.filter(
    (g) => g.title?.includes(search) || g.description?.includes(search) || g.group_tag?.includes(search)
  );

  const folderPlans = plans.filter((p) => activeGroup && p.group_id === activeGroup.id);

  const filteredPlans = folderPlans.filter(
    (p) => p.title?.includes(search) || p.description?.includes(search) || p.college?.includes(search) || p.level?.includes(search)
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
      if (activeGroup?.id === id) backToGroups();
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
              placeholder={view === 'groups' ? 'بحث في المجموعات...' : 'بحث في الخطط...'}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {view === 'folder' && (
              <button className="btn btn-secondary" onClick={backToGroups}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M19 12H5M12 19l-7-7 7-7" />
                </svg>
                رجوع
              </button>
            )}
            <button className="btn btn-secondary" onClick={() => { setGroupForm({ title: '', description: '', group_tag: '' }); setShowGroupModal(true); }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
              </svg>
              إضافة مجموعة
            </button>
            <button className="btn btn-primary" onClick={() => {
              setForm({ title: '', description: '', college: '', level: '', file: null, group_id: activeGroup ? String(activeGroup.id) : '' });
              setShowPlanModal(true);
            }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              إضافة خطة جديدة
            </button>
          </div>
        </div>

        {view === 'folder' && activeGroup && (
          <div
            style={{
              padding: '12px 24px',
              borderBottom: '1px solid var(--gray-200)',
              background: 'var(--gray-50)',
              fontSize: 14,
            }}
          >
            <span
              onClick={backToGroups}
              style={{ cursor: 'pointer', color: 'var(--primary)', fontWeight: 500 }}
            >
              الخطط الدراسية
            </span>
            <span style={{ margin: '0 10px', color: 'var(--gray-400)' }}>/</span>
            <span style={{ color: 'var(--gray-700)', fontWeight: 600 }}>{activeGroup.title}</span>
          </div>
        )}

        {view === 'groups' ? (
          <div style={{ padding: 24 }}>
            {filteredGroups.length > 0 ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
                {filteredGroups.map((group) => {
                  const planCount = plans.filter((p) => p.group_id === group.id).length;
                  return (
                    <div
                      key={group.id}
                      onClick={() => openFolder(group)}
                      style={{
                        background: 'var(--white)',
                        border: '1px solid var(--gray-200)',
                        borderRadius: 12,
                        padding: 20,
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        textAlign: 'center',
                        gap: 8,
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--primary)'; e.currentTarget.style.boxShadow = '0 4px 16px rgba(46,125,50,0.15)'; e.currentTarget.style.transform = 'translateY(-2px)'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--gray-200)'; e.currentTarget.style.boxShadow = 'none'; e.currentTarget.style.transform = 'none'; }}
                    >
                      <div
                        style={{
                          width: 56,
                          height: 56,
                          borderRadius: 14,
                          background: 'var(--primary-bg)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: 28,
                        }}
                      >
                        📁
                      </div>
                      <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--gray-800)' }}>
                        {group.title}
                      </div>
                      {group.group_tag && (
                        <span
                          style={{
                            fontSize: 11,
                            color: 'var(--primary)',
                            background: 'var(--primary-bg)',
                            padding: '2px 10px',
                            borderRadius: 20,
                            fontWeight: 600,
                          }}
                        >
                          #{group.group_tag}
                        </span>
                      )}
                      <div style={{ fontSize: 13, color: 'var(--gray-500)' }}>
                        {planCount} {planCount === 1 ? 'خطة' : 'خطط'}
                      </div>
                      <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                        <button
                          className="btn btn-primary btn-sm"
                          style={{ fontSize: 12, padding: '6px 14px' }}
                          disabled={publishing === group.id}
                          onClick={(e) => { e.stopPropagation(); handlePublishGroup(group.id); }}
                        >
                          {publishing === group.id ? '...' : 'نشر'}
                        </button>
                        <button
                          className="btn btn-danger btn-sm"
                          style={{ padding: '6px 10px' }}
                          onClick={(e) => { e.stopPropagation(); handleDeleteGroup(group.id); }}
                        >
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                </svg>
                <h4>لا توجد مجموعات</h4>
                <p>ابدأ بإضافة مجموعات خطط دراسية جديدة</p>
              </div>
            )}
          </div>
        ) : (
          <div style={{ padding: 24 }}>
            {filteredPlans.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {filteredPlans.map((plan) => {
                  const group = groups.find((g) => g.id === plan.group_id);
                  return (
                    <div
                      key={plan.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 14,
                        padding: '14px 16px',
                        borderRadius: 10,
                        border: '1px solid var(--gray-200)',
                        transition: 'all 0.15s',
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--gray-300)'; e.currentTarget.style.background = 'var(--gray-50)'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--gray-200)'; e.currentTarget.style.background = 'transparent'; }}
                    >
                      <div
                        style={{
                          width: 40,
                          height: 40,
                          borderRadius: 10,
                          background: 'var(--info-light)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: 20,
                          flexShrink: 0,
                        }}
                      >
                        📄
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--gray-800)' }}>
                          {plan.title}
                        </div>
                        {plan.description && (
                          <div style={{ fontSize: 13, color: 'var(--gray-500)', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {plan.description}
                          </div>
                        )}
                        <div style={{ display: 'flex', gap: 8, marginTop: 6, flexWrap: 'wrap' }}>
                          {group && (
                            <span className="status-badge active" style={{ fontSize: 11 }}>
                              {group.title}
                            </span>
                          )}
                          {plan.college && (
                            <span style={{ fontSize: 12, color: 'var(--gray-500)' }}>{plan.college}</span>
                          )}
                          {plan.level && (
                            <span style={{ fontSize: 12, color: 'var(--gray-500)' }}>{plan.level}</span>
                          )}
                          {plan.channel_message_id && (
                            <span style={{ fontSize: 12, color: 'var(--primary)', fontWeight: 600 }}>
                              ✓ منشورة
                            </span>
                          )}
                        </div>
                      </div>
                      <button
                        className="btn btn-danger btn-icon"
                        style={{ flexShrink: 0 }}
                        onClick={() => handleDeletePlan(plan.id)}
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                        </svg>
                      </button>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                  <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
                </svg>
                <h4>لا توجد خطط دراسية</h4>
                <p>هذه المجموعة لا تحتوي على أي خطط دراسية بعد</p>
              </div>
            )}
          </div>
        )}
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
