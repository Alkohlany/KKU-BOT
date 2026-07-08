import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useConfirm } from '../components/ConfirmDialog';
import { useToast } from '../components/ToastContext';
import StatsCard from '../components/StatsCard';

export default function Groups() {
  const { confirm } = useConfirm();
  const { showToast } = useToast();
  const [channelGroups, setChannelGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('channels');
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [form, setForm] = useState({ chat_id: '', title: '', type: 'channel', member_count: 0, invite_link: '' });
  const [editForm, setEditForm] = useState({ title: '', member_count: 0, invite_link: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const data = await api.getChannels();
      setChannelGroups(data);
    } catch (err) {
      console.error('Failed to load channels/groups:', err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = channelGroups.filter((g) => {
    const matchesTab = activeTab === 'channels' ? g.type === 'channel' : g.type === 'group';
    const matchesSearch = g.title?.includes(search) || g.chat_id?.toString().includes(search);
    return matchesTab && matchesSearch;
  });

  const channels = channelGroups.filter((g) => g.type === 'channel');
  const groups = channelGroups.filter((g) => g.type === 'group');
  const totalMembers = channelGroups.reduce((sum, g) => sum + (g.member_count || 0), 0);
  const activeCount = channelGroups.filter((g) => g.is_active || g.isActive).length;

  const handleAdd = async () => {
    if (!form.chat_id) return;
    setSaving(true);
    try {
      await api.post('/channels', {
        chat_id: parseInt(form.chat_id),
        title: form.title || `Chat ${form.chat_id}`,
        type: form.type,
        member_count: parseInt(form.member_count) || 0,
        invite_link: form.invite_link || null
      });
      setShowModal(false);
      setForm({ chat_id: '', title: '', type: 'channel', member_count: 0, invite_link: '' });
      loadData();
      showToast('تمت الإضافة بنجاح', 'success');
    } catch (err) {
      console.error('Failed to add:', err);
      showToast('فشل الإضافة', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleEditSave = async () => {
    if (!editItem) return;
    setSaving(true);
    try {
      await api.updateChannel(editItem.id, {
        title: editForm.title,
        member_count: parseInt(editForm.member_count) || 0,
        invite_link: editForm.invite_link || null
      });
      setShowEditModal(false);
      setEditItem(null);
      loadData();
      showToast('تم التعديل بنجاح', 'success');
    } catch (err) {
      console.error('Failed to edit:', err);
      showToast('فشل التعديل', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (item) => {
    try {
      await api.toggleChannel(item.id);
      setChannelGroups(channelGroups.map((g) =>
        g.id === item.id ? { ...g, is_active: !g.is_active, isActive: !g.isActive } : g
      ));
    } catch (err) {
      console.error('Failed to toggle:', err);
      showToast('فشل التبديل', 'error');
    }
  };

  const handleDelete = async (item) => {
    const label = item.type === 'channel' ? 'القناة' : 'الجروب';
    const ok = await confirm(`هل أنت متأكد من حذف ${label} "${item.title}"؟`);
    if (!ok) return;
    try {
      await api.deleteChannel(item.id);
      setChannelGroups(channelGroups.filter((g) => g.id !== item.id));
      showToast(`تم حذف ${label} بنجاح`, 'success');
    } catch (err) {
      console.error('Failed to delete:', err);
      showToast('فشل الحذف', 'error');
    }
  };

  const openEditModal = (item) => {
    setEditItem(item);
    setEditForm({
      title: item.title || '',
      member_count: item.member_count || 0,
      invite_link: item.invite_link || ''
    });
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
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        <StatsCard icon="users" value={channels.length} label="إجمالي القنوات" color="blue" />
        <StatsCard icon="groups" value={groups.length} label="إجمالي الجروبات" color="green" />
        <StatsCard icon="chat" value={totalMembers.toLocaleString()} label="الأعضاء المتصلون" color="orange" />
        <StatsCard icon="block" value={activeCount} label="النشطة" color="red" />
      </div>

      <div className="card">
        <div className="card-header" style={{ flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', gap: 8, width: '100%', flexWrap: 'wrap' }}>
            <button
              className={`btn ${activeTab === 'channels' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('channels')}
              style={{ flex: '0 0 auto' }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                <line x1="8" y1="21" x2="16" y2="21" />
                <line x1="12" y1="17" x2="12" y2="21" />
              </svg>
              القنوات ({channels.length})
            </button>
            <button
              className={`btn ${activeTab === 'groups' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('groups')}
              style={{ flex: '0 0 auto' }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
              الجروبات ({groups.length})
            </button>
          </div>
          <div style={{ display: 'flex', gap: 12, width: '100%', alignItems: 'center', flexWrap: 'wrap' }}>
            <div className="search-box" style={{ flex: 1, minWidth: 200 }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                type="text"
                placeholder={activeTab === 'channels' ? 'بحث في القنوات...' : 'بحث في الجروبات...'}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <button
              className="btn btn-primary"
              onClick={() => { setForm({ chat_id: '', title: '', type: activeTab === 'channels' ? 'channel' : 'group', member_count: 0, invite_link: '' }); setShowModal(true); }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              {activeTab === 'channels' ? 'إضافة قناة' : 'إضافة جروب'}
            </button>
          </div>
        </div>

        {/* Desktop Table */}
        <div className="table-container desktop-only">
          <table>
            <thead>
              <tr>
                <th>{activeTab === 'channels' ? 'اسم القناة' : 'اسم الجروب'}</th>
                <th>Chat ID</th>
                <th>عدد الأعضاء</th>
                <th>رابط الدعوة</th>
                <th>الحالة</th>
                <th>إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id}>
                  <td><strong>{item.title || 'بدون عنوان'}</strong></td>
                  <td><code style={{ fontSize: 12 }}>{item.chat_id}</code></td>
                  <td>{(item.member_count || 0).toLocaleString()}</td>
                  <td>
                    {item.invite_link ? (
                      <a
                        href={item.invite_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ fontSize: 13, color: 'var(--primary)' }}
                      >
                        فتح الرابط
                      </a>
                    ) : (
                      <span style={{ color: 'var(--gray-400)', fontSize: 12 }}>-</span>
                    )}
                  </td>
                  <td>
                    <label className="toggle-switch">
                      <input
                        type="checkbox"
                        checked={item.is_active || item.isActive || false}
                        onChange={() => handleToggle(item)}
                      />
                      <span className="toggle-slider" />
                    </label>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      <button className="btn btn-secondary btn-icon" onClick={() => openEditModal(item)} title="تعديل">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
                      </button>
                      <button className="btn btn-danger btn-icon" onClick={() => handleDelete(item)} title="حذف">
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
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
              </svg>
              <h4>{activeTab === 'channels' ? 'لا توجد قنوات' : 'لا توجد جروبات'}</h4>
              <p>{activeTab === 'channels' ? 'أضف قناة يدوياً أو أرسل /registerchannel داخل القناة' : 'أضف جروب يدوياً أو أرسل /registergroup داخل الجروب'}</p>
            </div>
          )}
        </div>

        {/* Mobile Cards */}
        <div className="mobile-cards">
          {filtered.map((item) => (
            <div key={item.id} className="mobile-card">
              <div className="mobile-card-header">
                <strong style={{ fontSize: 14 }}>{item.title || 'بدون عنوان'}</strong>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={item.is_active || item.isActive || false}
                    onChange={() => handleToggle(item)}
                  />
                  <span className="toggle-slider" />
                </label>
              </div>
              <div className="mobile-card-body">
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 12, color: 'var(--gray-400)', minWidth: 70 }}>Chat ID:</span>
                    <code style={{ fontSize: 12 }}>{item.chat_id}</code>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 12, color: 'var(--gray-400)', minWidth: 70 }}>الأعضاء:</span>
                    <span style={{ fontSize: 13 }}>{(item.member_count || 0).toLocaleString()}</span>
                  </div>
                  {item.invite_link && (
                    <a
                      href={item.invite_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ fontSize: 12, color: 'var(--primary)' }}
                    >
                      فتح رابط الدعوة
                    </a>
                  )}
                </div>
              </div>
              <div className="mobile-card-meta">
                <button className="btn btn-secondary btn-sm" onClick={() => openEditModal(item)}>
                  تعديل
                </button>
                <button className="btn btn-danger btn-sm" onClick={() => handleDelete(item)}>
                  حذف
                </button>
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="empty-state">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
              </svg>
              <h4>{activeTab === 'channels' ? 'لا توجد قنوات' : 'لا توجد جروبات'}</h4>
              <p>{activeTab === 'channels' ? 'أضف قناة يدوياً أو أرسل /registerchannel داخل القناة' : 'أضف جروب يدوياً أو أرسل /registergroup داخل الجروب'}</p>
            </div>
          )}
        </div>
      </div>

      {/* Add Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{activeTab === 'channels' ? 'إضافة قناة جديدة' : 'إضافة جروب جديد'}</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Chat ID <span style={{ color: 'var(--danger)' }}>*</span></label>
                <input
                  className="form-input"
                  placeholder="مثال: -1001234567890"
                  value={form.chat_id}
                  onChange={(e) => setForm({ ...form, chat_id: e.target.value })}
                />
                <small style={{ color: 'var(--gray-500)', fontSize: 12, display: 'block', marginTop: 4 }}>
                  احصل على Chat ID من @userinfobot أو @getidsbot داخل {form.type === 'channel' ? 'القناة' : 'الجروب'}
                </small>
              </div>
              <div className="form-group">
                <label>{form.type === 'channel' ? 'اسم القناة' : 'اسم الجروب'} (اختياري)</label>
                <input
                  className="form-input"
                  placeholder={form.type === 'channel' ? 'مثال: قناة هندسة الحاسب' : 'مثال: قروب هندسة الحاسب'}
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>النوع</label>
                <div style={{ display: 'flex', gap: 16, marginTop: 4 }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 14 }}>
                    <input
                      type="radio"
                      name="type"
                      value="channel"
                      checked={form.type === 'channel'}
                      onChange={() => setForm({ ...form, type: 'channel' })}
                      style={{ width: 16, height: 16 }}
                    />
                    قناة
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 14 }}>
                    <input
                      type="radio"
                      name="type"
                      value="group"
                      checked={form.type === 'group'}
                      onChange={() => setForm({ ...form, type: 'group' })}
                      style={{ width: 16, height: 16 }}
                    />
                    جروب
                  </label>
                </div>
              </div>
              <div className="form-group">
                <label>عدد الأعضاء (اختياري)</label>
                <input
                  className="form-input"
                  type="number"
                  placeholder="0"
                  value={form.member_count}
                  onChange={(e) => setForm({ ...form, member_count: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>رابط الدعوة (اختياري)</label>
                <input
                  className="form-input"
                  placeholder="https://t.me/+..."
                  value={form.invite_link}
                  onChange={(e) => setForm({ ...form, invite_link: e.target.value })}
                />
              </div>
              <div className="form-group">
                <button
                  className="btn btn-secondary"
                  style={{ width: '100%' }}
                  disabled={!form.chat_id}
                  onClick={() => showToast('ميزة الجلب التلقائي قيد التطوير', 'info')}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                  </svg>
                  جلب المعلومات تلقائياً
                </button>
                <small style={{ color: 'var(--gray-400)', fontSize: 12, display: 'block', marginTop: 4 }}>
                  سيتم جلب اسم وعدد الأعضاء من تيليجرام (قريباً)
                </small>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={handleAdd} disabled={saving || !form.chat_id}>
                {saving ? 'جاري الإضافة...' : 'إضافة'}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>إلغاء</button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && (
        <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>تعديل {editItem?.type === 'channel' ? 'القناة' : 'الجروب'}</h3>
              <button className="modal-close" onClick={() => setShowEditModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>{editItem?.type === 'channel' ? 'اسم القناة' : 'اسم الجروب'}</label>
                <input
                  className="form-input"
                  placeholder="أدخل الاسم"
                  value={editForm.title}
                  onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>عدد الأعضاء</label>
                <input
                  className="form-input"
                  type="number"
                  placeholder="0"
                  value={editForm.member_count}
                  onChange={(e) => setEditForm({ ...editForm, member_count: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>رابط الدعوة</label>
                <input
                  className="form-input"
                  placeholder="https://t.me/+..."
                  value={editForm.invite_link}
                  onChange={(e) => setEditForm({ ...editForm, invite_link: e.target.value })}
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
    </>
  );
}
