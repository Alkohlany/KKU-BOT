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
  const [showEditModal, setShowEditModal] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [editForm, setEditForm] = useState({ title: '' });
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
    const matchesSearch = g.title?.includes(search) || g.chatId?.toString().includes(search);
    return matchesTab && matchesSearch;
  });

  const channels = channelGroups.filter((g) => g.type === 'channel');
  const groups = channelGroups.filter((g) => g.type === 'group');
  const totalMembers = channelGroups.reduce((sum, g) => sum + (g.memberCount || 0), 0);
  const activeCount = channelGroups.filter((g) => g.is_active || g.isActive).length;

  const handleEditSave = async () => {
    if (!editItem) return;
    setSaving(true);
    try {
      await api.updateChannel(editItem.id, {
        title: editForm.title
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

  const handleSetOfficial = async (item) => {
    try {
      await api.setOfficialChannel(item.id);
      setChannelGroups(channelGroups.map((g) =>
        g.type === 'channel' ? { ...g, isOfficial: g.id === item.id } : g
      ));
      showToast('تم تعيين القناة كرسمية', 'success');
    } catch (err) {
      console.error('Failed to set official channel:', err);
      if (err.status === 400) {
        showToast('يمكن تعيين القنوات فقط كقناة رسمية', 'error');
      } else if (err.status === 404) {
        showToast('القناة غير موجودة', 'error');
      } else {
        showToast('فشل تعيين القناة الرسمية', 'error');
      }
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
      title: item.title || ''
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
                <th>المنشورات</th>
                <th>الرابط</th>
                <th>الحالة</th>
                <th>إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id}>
                  <td>
                    <strong>{item.title || 'بدون عنوان'}</strong>
                    {item.type === 'channel' && (
                      <span
                        onClick={() => handleSetOfficial(item)}
                        style={{ cursor: 'pointer', marginRight: 8, fontSize: 16, color: item.isOfficial ? '#f59e0b' : 'var(--gray-300)', transition: 'color 0.2s' }}
                        title={item.isOfficial ? 'قناة رسمية' : 'تعيين كقناة رسمية'}
                      >
                        {item.isOfficial ? '★' : '☆'}
                      </span>
                    )}
                  </td>
                  <td><code style={{ fontSize: 12 }}>{item.chatId}</code></td>
                  <td>{(item.memberCount || 0).toLocaleString()}</td>
                  <td>{(item.postCount || 0).toLocaleString()}</td>
                  <td>
                    {item.inviteLink ? (
                      <a
                        href={item.inviteLink}
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
                 <span style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                   <strong style={{ fontSize: 14 }}>{item.title || 'بدون عنوان'}</strong>
                   {item.type === 'channel' && (
                     <span
                       onClick={() => handleSetOfficial(item)}
                       style={{ cursor: 'pointer', fontSize: 16, color: item.isOfficial ? '#f59e0b' : 'var(--gray-300)', transition: 'color 0.2s' }}
                       title={item.isOfficial ? 'قناة رسمية' : 'تعيين كقناة رسمية'}
                     >
                       {item.isOfficial ? '★' : '☆'}
                     </span>
                   )}
                 </span>
                 <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                   <label className="toggle-switch">
                     <input
                       type="checkbox"
                       checked={item.is_active || item.isActive || false}
                       onChange={() => handleToggle(item)}
                     />
                     <span className="toggle-slider" />
                   </label>
                 </span>
               </div>
              <div className="mobile-card-body">
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 12, color: 'var(--gray-400)', minWidth: 70 }}>Chat ID:</span>
                    <code style={{ fontSize: 12 }}>{item.chatId}</code>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 12, color: 'var(--gray-400)', minWidth: 70 }}>الأعضاء:</span>
                    <span style={{ fontSize: 13 }}>{(item.memberCount || 0).toLocaleString()}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 12, color: 'var(--gray-400)', minWidth: 70 }}>المنشورات:</span>
                    <span style={{ fontSize: 13 }}>{(item.postCount || 0).toLocaleString()}</span>
                  </div>
                  {item.inviteLink && (
                    <a
                      href={item.inviteLink}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ fontSize: 12, color: 'var(--primary)' }}
                    >
                      فتح الرابط
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
