import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useConfirm } from '../components/ConfirmDialog';
import { useToast } from '../components/ToastContext';

export default function Books() {
  const { confirm } = useConfirm();
  const { showToast } = useToast();
  const [books, setBooks] = useState([]);
  const [groups, setGroups] = useState([]);
  const [view, setView] = useState('groups');
  const [activeGroup, setActiveGroup] = useState(null);
  const [showBookModal, setShowBookModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [form, setForm] = useState({ title: '', file: null, group_id: '', author: '', link: '' });
  const [groupForm, setGroupForm] = useState({ title: '', description: '', group_tag: '' });
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [publishingBook, setPublishingBook] = useState(null);
  const [editingBook, setEditingBook] = useState(null);
  const [editingGroup, setEditingGroup] = useState(null);
  const [showDeleteGroupModal, setShowDeleteGroupModal] = useState(false);
  const [deletingGroupId, setDeletingGroupId] = useState(null);
  const [showDeleteBookModal, setShowDeleteBookModal] = useState(false);
  const [deletingBookId, setDeletingBookId] = useState(null);
  const [windowWidth, setWindowWidth] = useState(window.innerWidth);

  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    loadData();
  }, [search]);

  const loadData = async () => {
    try {
      const [booksData, groupsData] = await Promise.all([
        api.getBooks({ search }),
        api.getBookGroups()
      ]);
      const bookItems = booksData.items || booksData;
      setBooks(Array.isArray(bookItems) ? bookItems : []);
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
    (g) => g.title?.includes(search) || g.group_tag?.includes(search)
  );

  const folderBooks = books.filter((b) => activeGroup && b.group_id === activeGroup.id);

  const filteredBooks = folderBooks.filter(
    (b) => b.title?.includes(search)
  );

  const getPublishStatus = (group) => {
    const totalBooks = books.filter((b) => b.group_id === group.id).length;
    const publishedBooks = books.filter((b) => b.group_id === group.id && b.channel_message_id).length;
    if (publishedBooks === 0) return { text: 'غير منشور', color: 'var(--gray-400)', bg: 'var(--gray-100)', total: totalBooks, published: publishedBooks };
    if (publishedBooks < totalBooks) return { text: `منشور جزئياً ${publishedBooks}/${totalBooks}`, color: '#b76e00', bg: '#fff3e0', total: totalBooks, published: publishedBooks };
    return { text: 'منشور كلياً', color: 'var(--primary)', bg: 'var(--primary-bg)', total: totalBooks, published: publishedBooks };
  };

  const handleSaveBook = async () => {
    if (!form.title) return;
    setSaving(true);
    try {
      if (editingBook) {
        await api.updateBook(editingBook.id, {
          title: form.title,
          group_id: form.group_id || null,
          file: form.file || null,
          author: form.author || null,
          link: form.link || null,
        });
        await loadData();
      } else {
        let newItem;
        if (form.file) {
          const formDataObj = new FormData();
          formDataObj.append('title', form.title);
          if (form.group_id) {
            formDataObj.append('group_id', form.group_id);
          }
          if (form.author) {
            formDataObj.append('author', form.author);
          }
          if (form.link) {
            formDataObj.append('link', form.link);
          }
          formDataObj.append('file', form.file);
          newItem = await api.uploadBook(formDataObj);
        } else {
          newItem = await api.addBook({
            title: form.title,
            group_id: form.group_id || null,
            author: form.author || null,
            link: form.link || null,
          });
        }
        setBooks([...books, newItem]);
      }
      setForm({ title: '', file: null, group_id: '', author: '', link: '' });
      setEditingBook(null);
      setShowBookModal(false);
    } catch (err) {
      console.error('Failed to save book:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveGroup = async () => {
    if (!groupForm.title) return;
    setSaving(true);
    try {
      if (editingGroup) {
        await api.updateBookGroup(editingGroup.id, groupForm);
        await loadData();
      } else {
        const newGroup = await api.addBookGroup(groupForm);
        setGroups([...groups, newGroup]);
      }
      setGroupForm({ title: '', description: '', group_tag: '' });
      setEditingGroup(null);
      setShowGroupModal(false);
    } catch (err) {
      console.error('Failed to save group:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteBook = async (id) => {
    setDeletingBookId(id);
    setShowDeleteBookModal(true);
  };

  const handleDeleteGroup = async (id) => {
    setDeletingGroupId(id);
    setShowDeleteGroupModal(true);
  };

  const handleGroupResetPublish = async (id) => {
    setShowDeleteGroupModal(false);
    try {
      await api.deleteBookGroup(id, 'reset');
      showToast('تم حذف المنشورات من القناة بنجاح', 'success');
      await loadData();
    } catch (err) {
      showToast('حدث خطأ أثناء حذف المنشورات', 'error');
    }
  };

  const handleGroupPermanentDelete = async (id) => {
    setShowDeleteGroupModal(false);
    const ok = await confirm('هل أنت متأكد من الحذف النهائي؟ سيتم حذف المجموعة وجميع الكتب التابعة لها نهائياً.');
    if (!ok) return;
    try {
      await api.deleteBookGroup(id, 'permanent');
      setGroups(groups.filter((g) => g.id !== id));
      setBooks(books.filter((b) => b.group_id !== id));
      if (activeGroup?.id === id) backToGroups();
      showToast('تم حذف المجموعة نهائياً', 'success');
    } catch (err) {
      showToast('حدث خطأ أثناء الحذف', 'error');
    }
  };

  const handleBookResetPublish = async (id) => {
    setShowDeleteBookModal(false);
    try {
      await api.deleteBook(id, 'reset');
      showToast('تم حذف الكتاب من القناة بنجاح', 'success');
      await loadData();
    } catch (err) {
      showToast('حدث خطأ أثناء حذف الكتاب من القناة', 'error');
    }
  };

  const handleBookPermanentDelete = async (id) => {
    setShowDeleteBookModal(false);
    const ok = await confirm('هل أنت متأكد من الحذف النهائي؟ سيتم حذف الكتاب نهائياً.');
    if (!ok) return;
    try {
      await api.deleteBook(id, 'permanent');
      setBooks(books.filter((b) => b.id !== id));
      showToast('تم حذف الكتاب نهائياً', 'success');
    } catch (err) {
      showToast('حدث خطأ أثناء الحذف', 'error');
    }
  };

  const handlePublishBook = async (bookId) => {
    setPublishingBook(bookId);
    try {
      const result = await api.publishBook(bookId);
      showToast(result.message || result.error || 'تم النشر بنجاح', result.error ? 'error' : 'success');
      await loadData();
    } catch (err) {
      console.error('Failed to publish book:', err);
      showToast('حدث خطأ أثناء نشر الكتاب', 'error');
    } finally {
      setPublishingBook(null);
    }
  };

  const openAddBookModal = () => {
    setEditingBook(null);
    setForm({ title: '', file: null, group_id: activeGroup ? String(activeGroup.id) : '', author: '', link: '' });
    setShowBookModal(true);
  };

  const openEditBookModal = (book) => {
    setEditingBook(book);
    setForm({
      title: book.title || '',
      file: null,
      group_id: book.group_id ? String(book.group_id) : '',
      author: book.author || '',
      link: book.link || '',
    });
    setShowBookModal(true);
  };

  const openAddGroupModal = () => {
    setEditingGroup(null);
    setGroupForm({ title: '', description: '', group_tag: '' });
    setShowGroupModal(true);
  };

  const openEditGroupModal = (group) => {
    setEditingGroup(group);
    setGroupForm({ title: group.title || '', description: group.description || '', group_tag: group.group_tag || '' });
    setShowGroupModal(true);
  };

  const closeModals = () => {
    setShowBookModal(false);
    setShowGroupModal(false);
    setEditingBook(null);
    setEditingGroup(null);
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
      <div className="card" style={{ overflow: 'visible' }}>
        <div className="card-header" style={{
          flexWrap: 'wrap', gap: 12,
          position: 'sticky', top: 0, zIndex: 10,
          background: 'var(--white)',
          flexDirection: 'column',
          alignItems: 'stretch',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
            <div className="search-box">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                type="text"
                placeholder={view === 'groups' ? 'بحث في المجموعات...' : 'بحث في الكتب...'}
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
              <button className="btn btn-secondary" onClick={openAddGroupModal}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                </svg>
                إضافة مجموعة
              </button>
              <button className="btn btn-primary" onClick={openAddBookModal}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                إضافة كتاب جديد
              </button>
            </div>
          </div>

          {view === 'folder' && activeGroup && (
            <div style={{
              padding: '8px 0 0',
              borderTop: '1px solid var(--gray-100)',
              fontSize: 14,
              marginTop: 4,
            }}>
              <span onClick={backToGroups} style={{ cursor: 'pointer', color: 'var(--primary)', fontWeight: 500 }}>
                الكتب
              </span>
              <span style={{ margin: '0 10px', color: 'var(--gray-400)' }}>/</span>
              <span style={{ color: 'var(--gray-700)', fontWeight: 600 }}>{activeGroup.title}</span>
            </div>
          )}
        </div>

        {view === 'groups' ? (
          <div style={{ padding: 24 }}>
            {filteredGroups.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {filteredGroups.map((group) => {
                  const bookCount = books.filter((b) => b.group_id === group.id).length;
                  const status = getPublishStatus(group);
                  return (
                    <div
                      key={group.id}
                      onClick={() => openFolder(group)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: windowWidth < 768 ? 10 : 14,
                        padding: windowWidth < 768 ? '10px 12px' : '14px 16px',
                        borderRadius: 10,
                        border: '1px solid var(--gray-200)',
                        cursor: 'pointer',
                        transition: 'all 0.15s',
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--primary)'; e.currentTarget.style.boxShadow = '0 2px 8px rgba(46,125,50,0.12)'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--gray-200)'; e.currentTarget.style.boxShadow = 'none'; }}
                    >
                      <div
                        style={{
                          width: windowWidth < 768 ? 36 : 44,
                          height: windowWidth < 768 ? 36 : 44,
                          borderRadius: 10,
                          background: 'var(--primary-bg)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: windowWidth < 768 ? 18 : 22,
                          flexShrink: 0,
                        }}
                      >
                        📁
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--gray-800)' }}>
                          {group.title}
                        </div>
                        <div style={{ display: 'flex', gap: 6, marginTop: 4, flexWrap: 'wrap', alignItems: 'center' }}>
                          {group.group_tag && (
                            <span style={{ fontSize: 11, color: 'var(--primary)', background: 'var(--primary-bg)', padding: '1px 8px', borderRadius: 10, fontWeight: 600 }}>
                              #{group.group_tag}
                            </span>
                          )}
                          <span style={{ fontSize: 12, color: 'var(--gray-500)' }}>
                            {bookCount} {bookCount === 1 ? 'كتاب' : 'كتب'}
                          </span>
                          {bookCount > 0 && (
                            <span style={{ fontSize: 11, color: status.color, background: status.bg, padding: '1px 8px', borderRadius: 10, fontWeight: 600 }}>
                              {status.text}
                            </span>
                          )}
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                        <button className="btn btn-secondary btn-icon" style={{ padding: windowWidth < 768 ? 4 : 6 }} onClick={(e) => { e.stopPropagation(); openEditGroupModal(group); }}>
                          <svg width={windowWidth < 768 ? 11 : 13} height={windowWidth < 768 ? 11 : 13} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                          </svg>
                        </button>
                        <button className="btn btn-danger btn-icon" style={{ padding: windowWidth < 768 ? 4 : 6 }} onClick={(e) => { e.stopPropagation(); handleDeleteGroup(group.id); }}>
                          <svg width={windowWidth < 768 ? 10 : 12} height={windowWidth < 768 ? 10 : 12} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
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
                <p>ابدأ بإضافة مجموعات كتب جديدة</p>
              </div>
            )}
          </div>
        ) : (
          <div style={{ padding: 24 }}>
            {filteredBooks.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {filteredBooks.map((book) => {
                  const group = groups.find((g) => g.id === book.group_id);
                  return (
                    <div
                      key={book.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: windowWidth < 768 ? 10 : 14,
                        padding: windowWidth < 768 ? '10px 12px' : '14px 16px',
                        borderRadius: 10,
                        border: '1px solid var(--gray-200)',
                        transition: 'all 0.15s',
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--gray-300)'; e.currentTarget.style.background = 'var(--gray-50)'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--gray-200)'; e.currentTarget.style.background = 'transparent'; }}
                    >
                      <div
                        style={{
                          width: windowWidth < 768 ? 32 : 40,
                          height: windowWidth < 768 ? 32 : 40,
                          borderRadius: 10,
                          background: 'var(--info-light)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: windowWidth < 768 ? 16 : 20,
                          flexShrink: 0,
                        }}
                      >
                        📚
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--gray-800)' }}>
                          {book.title}
                        </div>
                        <div style={{ display: 'flex', gap: 8, marginTop: 6, flexWrap: 'wrap' }}>
                          {group && (
                            <span className="status-badge active" style={{ fontSize: windowWidth < 768 ? 9 : 11 }}>
                              {windowWidth < 768 ? group.title.charAt(0) : group.title}
                            </span>
                          )}
                          {book.author && (
                            <span style={{ fontSize: 12, color: 'var(--gray-500)' }}>
                              {book.author}
                            </span>
                          )}
                          {book.channel_message_id && (
                            <span style={{ fontSize: 12, color: 'var(--primary)', fontWeight: 600 }}>
                              ✓ منشورة
                            </span>
                          )}
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                        <button
                          className="btn btn-primary btn-icon"
                          style={{ padding: windowWidth < 768 ? 4 : 6 }}
                          onClick={() => handlePublishBook(book.id)}
                          disabled={publishingBook === book.id}
                          title="نشر الكتاب"
                        >
                          {publishingBook === book.id ? (
                            <span className="spinner" style={{ width: 14, height: 14 }} />
                          ) : (
                            <svg width={windowWidth < 768 ? 12 : 14} height={windowWidth < 768 ? 12 : 14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M22 2L11 13" />
                              <path d="M22 2l-7 20-4-9-9-4 20-7z" />
                            </svg>
                          )}
                        </button>
                        <button
                          className="btn btn-secondary btn-icon"
                          style={{ padding: windowWidth < 768 ? 4 : 6 }}
                          onClick={() => openEditBookModal(book)}
                        >
                          <svg width={windowWidth < 768 ? 12 : 14} height={windowWidth < 768 ? 12 : 14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                          </svg>
                        </button>
                        <button
                          className="btn btn-danger btn-icon"
                          style={{ flexShrink: 0, padding: windowWidth < 768 ? 4 : 'unset' }}
                          onClick={() => handleDeleteBook(book.id)}
                        >
                          <svg width={windowWidth < 768 ? 12 : 14} height={windowWidth < 768 ? 12 : 14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
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
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                  <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
                </svg>
                <h4>لا توجد كتب</h4>
                <p>هذه المجموعة لا تحتوي على أي كتب بعد</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Add/Edit Group Modal */}
      {showGroupModal && (
        <div className="modal-overlay" onClick={() => closeModals()}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingGroup ? 'تعديل المجموعة' : 'إضافة مجموعة جديدة'}</h3>
              <button className="modal-close" onClick={() => closeModals()}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>اسم المجموعة</label>
                <input
                  className="form-input"
                  placeholder="مثال: كتب طب"
                  value={groupForm.title}
                  onChange={(e) => setGroupForm({ ...groupForm, title: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>الهاشتاق (بدون #)</label>
                <input
                  className="form-input"
                  placeholder="مثال: كتب"
                  value={groupForm.group_tag}
                  onChange={(e) => setGroupForm({ ...groupForm, group_tag: e.target.value })}
                />
                <small style={{ color: 'var(--gray-500)', marginTop: 4, display: 'block' }}>
                  سيظهر في المنشور كمثال: #كتب
                </small>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={handleSaveGroup} disabled={saving}>
                {saving ? 'جاري الحفظ...' : (editingGroup ? 'حفظ التعديلات' : 'إضافة')}
              </button>
              <button className="btn btn-secondary" onClick={() => closeModals()}>إلغاء</button>
            </div>
          </div>
        </div>
      )}

      {/* Add/Edit Book Modal */}
      {showBookModal && (
        <div className="modal-overlay" onClick={() => closeModals()}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingBook ? 'تعديل الكتاب' : 'إضافة كتاب جديد'}</h3>
              <button className="modal-close" onClick={() => closeModals()}>✕</button>
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
                  placeholder="مثال: مقدمة في البرمجة"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>المؤلف</label>
                <input
                  className="form-input"
                  placeholder="مثال: أحمد محمد"
                  value={form.author}
                  onChange={(e) => setForm({ ...form, author: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>الرابط (اختياري)</label>
                <input
                  className="form-input"
                  placeholder="t.me/kkunewbot"
                  value={form.link}
                  onChange={(e) => setForm({ ...form, link: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>الملف المرفق {editingBook ? '(اتركه فارغاً للإبقاء على الملف الحالي)' : '(اختياري)'}</label>
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
              <button className="btn btn-primary" onClick={handleSaveBook} disabled={saving}>
                {saving ? 'جاري الحفظ...' : (editingBook ? 'حفظ التعديلات' : 'إضافة')}
              </button>
              <button className="btn btn-secondary" onClick={() => closeModals()}>إلغاء</button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Group Options Modal */}
      {showDeleteGroupModal && (
        <div className="modal-overlay" onClick={() => setShowDeleteGroupModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 420 }}>
            <div className="modal-header">
              <h3>خيارات حذف المجموعة</h3>
              <button className="modal-close" onClick={() => setShowDeleteGroupModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: 14, color: 'var(--gray-600)', lineHeight: 1.6, marginBottom: 16 }}>
                ماذا تريد أن تفعل بهذه المجموعة؟
              </p>
              <button
                className="btn btn-primary"
                style={{ width: '100%', marginBottom: 10, justifyContent: 'center' }}
                onClick={() => handleGroupResetPublish(deletingGroupId)}
              >
                حذف من القناة فقط
              </button>
              <p style={{ fontSize: 12, color: 'var(--gray-500)', marginBottom: 16, textAlign: 'center' }}>
                حذف جميع المنشورات من القناة مع الاحتفاظ بالمجموعة والكتب كمسودة
              </p>
              <button
                className="btn btn-danger"
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={() => handleGroupPermanentDelete(deletingGroupId)}
              >
                حذف نهائي
              </button>
              <p style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 8, textAlign: 'center' }}>
                حذف المجموعة وجميع الكتب التابعة لها نهائياً
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Delete Book Options Modal */}
      {showDeleteBookModal && (
        <div className="modal-overlay" onClick={() => setShowDeleteBookModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 420 }}>
            <div className="modal-header">
              <h3>خيارات حذف الكتاب</h3>
              <button className="modal-close" onClick={() => setShowDeleteBookModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: 14, color: 'var(--gray-600)', lineHeight: 1.6, marginBottom: 16 }}>
                ماذا تريد أن تفعل بهذا الكتاب؟
              </p>
              <button
                className="btn btn-primary"
                style={{ width: '100%', marginBottom: 10, justifyContent: 'center' }}
                onClick={() => handleBookResetPublish(deletingBookId)}
              >
                حذف من القناة فقط
              </button>
              <p style={{ fontSize: 12, color: 'var(--gray-500)', marginBottom: 16, textAlign: 'center' }}>
                حذف منشور الكتاب من القناة مع الاحتفاظ به كمسودة
              </p>
              <button
                className="btn btn-danger"
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={() => handleBookPermanentDelete(deletingBookId)}
              >
                حذف نهائي
              </button>
              <p style={{ fontSize: 12, color: 'var(--gray-500)', marginTop: 8, textAlign: 'center' }}>
                حذف الكتاب بشكل نهائي
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
