import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';
import { useToast } from '../components/ToastContext';

var FOLDER_LABELS = {
  'kku-bot': 'الكل',
  'kku-bot/news': 'الأخبار',
  'kku-bot/plans': 'الخطط الدراسية',
  'kku-bot/scheduled': 'المنشورات المجدولة',
};

function getFileIcon(name) {
  if (/\.(jpg|jpeg|png|gif|webp|svg)$/i.test(name)) return '🖼️';
  if (/\.(mp4|webm|mov|avi|mkv)$/i.test(name)) return '🎬';
  if (/\.pdf$/i.test(name)) return '📕';
  if (/\.(doc|docx|txt|rtf)$/i.test(name)) return '📄';
  if (/\.(zip|rar|7z|tar|gz)$/i.test(name)) return '📦';
  if (/\.(mp3|wav|ogg|flac|m4a)$/i.test(name)) return '🎵';
  if (/\.(xls|xlsx|csv)$/i.test(name)) return '📊';
  if (/\.(ppt|pptx)$/i.test(name)) return '📽️';
  return '📄';
}

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  if (bytes > 1048576) return (bytes / 1048576).toFixed(1) + ' MB';
  if (bytes > 1024) return (bytes / 1024).toFixed(0) + ' KB';
  return bytes + ' B';
}

function DotsButton(props) {
  var onClick = props.onClick;
  var style = props.style;
  return (
    <button
      onClick={function(e) { e.stopPropagation(); e.preventDefault(); onClick(e); }}
      style={Object.assign({
        width: 28, height: 28, borderRadius: 6, border: 'none',
        background: 'var(--gray-100)', cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: 'var(--gray-500)', fontSize: 16, fontWeight: 700,
        lineHeight: 1, flexShrink: 0,
      }, style || {})}
    >⋮</button>
  );
}

function ActionsMenu(props) {
  var item = props.item;
  var type = props.type;
  var onRename = props.onRename;
  var onDelete = props.onDelete;
  var onMove = props.onMove;
  var onOpen = props.onOpen;
  return (
    <div style={{ position: 'absolute', top: '100%', right: 0, background: 'var(--white)', borderRadius: 10, boxShadow: '0 8px 30px rgba(0,0,0,0.18)', border: '1px solid var(--gray-100)', padding: 4, zIndex: 200, minWidth: 170 }}>
      {type === 'file' && (
        <>
          <MenuBtn icon={<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>} label="فتح" onClick={onOpen} />
          <MenuBtn icon={<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>} label="إعادة تسمية" onClick={onRename} />
          <MenuBtn icon={<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><line x1="12" y1="11" x2="12" y2="17"/></svg>} label="نقل إلى..." onClick={onMove} />
          <div style={{ height: 1, background: 'var(--gray-100)', margin: '2px 8px' }} />
          <MenuBtn icon={<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>} label="حذف" onClick={onDelete} danger />
        </>
      )}
      {type === 'folder' && (
        <>
          <MenuBtn icon={<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>} label="فتح" onClick={onOpen} />
          <MenuBtn icon={<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>} label="إعادة تسمية" onClick={onRename} />
          <div style={{ height: 1, background: 'var(--gray-100)', margin: '2px 8px' }} />
          <MenuBtn icon={<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>} label="حذف المجلد" onClick={onDelete} danger />
        </>
      )}
    </div>
  );
}

function MenuBtn(props) {
  return (
    <button onClick={props.onClick} style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%', padding: '8px 12px', borderRadius: 6, border: 'none', background: 'transparent', cursor: 'pointer', fontSize: 13, textAlign: 'right', color: props.danger ? 'var(--danger)' : 'var(--gray-700)' }}>
      {props.icon}
      {props.label}
    </button>
  );
}

export default function CloudFiles() {
  var _t = useToast();
  var showToast = _t.showToast;
  var _f = useState({});
  var files = _f[0];
  var setFiles = _f[1];
  var _l = useState(true);
  var loading = _l[0];
  var setLoading = _l[1];
  var _p = useState('kku-bot');
  var currentPath = _p[0];
  var setCurrentPath = _p[1];
  var _s = useState('');
  var search = _s[0];
  var setSearch = _s[1];
  var _v = useState('grid');
  var viewMode = _v[0];
  var setViewMode = _v[1];
  var _rn = useState(null);
  var renaming = _rn[0];
  var setRenaming = _rn[1];
  var _rnVal = useState('');
  var renameValue = _rnVal[0];
  var setRenameValue = _rnVal[1];
  var _cf = useState(false);
  var showCreateFolder = _cf[0];
  var setShowCreateFolder = _cf[1];
  var _cfv = useState('');
  var createFolderValue = _cfv[0];
  var setCreateFolderValue = _cfv[1];
  var _ul = useState(false);
  var uploading = _ul[0];
  var setUploading = _ul[1];
  var _dp = useState(false);
  var isDragOver = _dp[0];
  var setIsDragOver = _dp[1];
  var _mv = useState(null);
  var movingItem = _mv[0];
  var setMovingItem = _mv[1];
  var _am = useState(null);
  var activeMenu = _am[0];
  var setActiveMenu = _am[1];
  var fileInputRef = useRef(null);

  var loadAll = useCallback(function() {
    setLoading(true);
    api.getCloudFiles().then(function(data) {
      setFiles(data);
    }).catch(function(err) {
      console.error('Failed to load:', err);
      showToast('فشل تحميل الملفات', 'error');
    }).finally(function() {
      setLoading(false);
    });
  }, []);

  useEffect(function() {
    loadAll();
  }, []);

  useEffect(function() {
    var close = function() { setActiveMenu(null); };
    if (activeMenu) {
      setTimeout(function() { document.addEventListener('click', close); }, 0);
      return function() { document.removeEventListener('click', close); };
    }
  }, [activeMenu]);

  var currentData = files[currentPath] || { files: [], subfolders: [] };
  var currentFiles = currentData.files || [];
  var currentSubfolders = currentData.subfolders || [];

  if (currentPath !== 'kku-bot' && files[currentPath] && !files[currentPath].files) {
    currentFiles = [];
    currentSubfolders = [];
  }

  var breadcrumbs = currentPath.split('/').map(function(part, i, arr) {
    return { name: FOLDER_LABELS[arr.slice(0, i + 1).join('/')] || part, path: arr.slice(0, i + 1).join('/') };
  });

  var filtered = currentFiles.filter(function(f) {
    if (!search) return true;
    return f.name.toLowerCase().indexOf(search.toLowerCase()) !== -1;
  });

  var filteredSubfolders = currentSubfolders.filter(function(sf) {
    if (!search) return true;
    return sf.name.toLowerCase().indexOf(search.toLowerCase()) !== -1;
  });

  var totalSize = currentFiles.reduce(function(sum, f) { return sum + (f.size || 0); }, 0);

  var navigateTo = function(path) {
    setCurrentPath(path);
    setSearch('');
    setActiveMenu(null);
    setRenaming(null);
    setLoading(true);
    api.getCloudFiles(path).then(function(data) {
      setFiles(function(prev) {
        var next = Object.assign({}, prev);
        next[path] = data;
        return next;
      });
    }).finally(function() {
      setLoading(false);
    });
  };

  var goUp = function() {
    var parts = currentPath.split('/');
    if (parts.length > 1) {
      parts.pop();
      navigateTo(parts.join('/'));
    }
  };

  var handleCreateFolder = function() {
    if (!createFolderValue.trim()) return;
    var path = currentPath + '/' + createFolderValue.trim();
    api.createCloudFolder(path).then(function() {
      showToast('تم إنشاء المجلد', 'success');
      setShowCreateFolder(false);
      setCreateFolderValue('');
      loadAll();
    }).catch(function() {
      showToast('فشل إنشاء المجلد', 'error');
    });
  };

  var handleDeleteFolder = function(path, name) {
    setActiveMenu(null);
    if (!confirm('هل أنت متأكد من حذف المجلد "' + name + '" وكل محتوياته؟')) return;
    api.deleteCloudFolder(path).then(function() {
      showToast('تم حذف المجلد: ' + name, 'success');
      if (currentPath === path) goUp();
      loadAll();
    }).catch(function() {
      showToast('فشل حذف المجلد', 'error');
    });
  };

  var handleDeleteFile = function(key, name) {
    setActiveMenu(null);
    if (!confirm('هل أنت متأكد من حذف "' + name + '"؟')) return;
    api.deleteCloudFile(key).then(function() {
      showToast('تم حذف الملف: ' + name, 'success');
      loadAll();
    }).catch(function() {
      showToast('فشل حذف الملف', 'error');
    });
  };

  var handleRename = function(key, currentName) {
    setActiveMenu(null);
    setRenaming(key);
    setRenameValue(currentName);
  };

  var confirmRename = function() {
    if (!renameValue.trim() || !renaming) return;
    api.renameCloudFile(renaming, renameValue.trim()).then(function() {
      showToast('تمت إعادة التسمية', 'success');
      setRenaming(null);
      setRenameValue('');
      loadAll();
    }).catch(function() {
      showToast('فشل إعادة التسمية', 'error');
    });
  };

  var handleUpload = function(selectedFiles) {
    if (!selectedFiles || selectedFiles.length === 0) return;
    setUploading(true);
    var total = selectedFiles.length;
    var done = 0;
    var errors = 0;
    Array.from(selectedFiles).forEach(function(file) {
      api.uploadCloudFile(file, currentPath).then(function() {
        done++;
      }).catch(function() {
        errors++;
      }).finally(function() {
        if (done + errors === total) {
          setUploading(false);
          showToast('تم رفع ' + done + ' ملف' + (errors > 0 ? ' (' + errors + ' فشل)' : ''), errors > 0 ? 'warning' : 'success');
          loadAll();
        }
      });
    });
  };

  var handleDrop = function(e) {
    e.preventDefault();
    setIsDragOver(false);
    handleUpload(e.dataTransfer.files);
  };

  var handleDragOver = function(e) {
    e.preventDefault();
    setIsDragOver(true);
  };

  var handleDragLeave = function() {
    setIsDragOver(false);
  };

  var handleMove = function(key) {
    setActiveMenu(null);
    setMovingItem(key);
  };

  var confirmMove = function(destFolder) {
    if (!movingItem) return;
    api.moveCloudFile(movingItem, destFolder).then(function() {
      showToast('تم نقل الملف', 'success');
      setMovingItem(null);
      loadAll();
    }).catch(function() {
      showToast('فشل نقل الملف', 'error');
    });
  };

  if (loading && Object.keys(files).length === 0) {
    return <div style={{ textAlign: 'center', padding: 60, color: 'var(--gray-400)' }}>
      <div style={{ fontSize: 24, marginBottom: 8 }}>⏳</div>
      <div>جاري تحميل الملفات...</div>
    </div>;
  }

  var menuKey = activeMenu ? activeMenu.key : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)' }}>
      {/* Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', background: 'var(--white)', borderRadius: '12px 12px 0 0', borderBottom: '1px solid var(--gray-100)', flexWrap: 'wrap' }}>
        <button onClick={goUp} disabled={currentPath === 'kku-bot'} style={{ width: 32, height: 32, borderRadius: 8, border: '1px solid var(--gray-200)', background: currentPath === 'kku-bot' ? 'var(--gray-50)' : 'var(--white)', cursor: currentPath === 'kku-bot' ? 'default' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: currentPath === 'kku-bot' ? 0.4 : 1, flexShrink: 0 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
            {breadcrumbs.map(function(bc, i) {
              return (
                <React.Fragment key={bc.path}>
                  {i > 0 && <span style={{ color: 'var(--gray-400)', fontSize: 12 }}>/</span>}
                  <button
                    onClick={function() { navigateTo(bc.path); }}
                    style={{ padding: '2px 6px', borderRadius: 6, border: 'none', background: i === breadcrumbs.length - 1 ? 'var(--primary-bg)' : 'transparent', color: i === breadcrumbs.length - 1 ? 'var(--primary)' : 'var(--gray-600)', fontSize: 12, fontWeight: i === breadcrumbs.length - 1 ? 600 : 400, cursor: 'pointer' }}
                  >{bc.name}</button>
                </React.Fragment>
              );
            })}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative' }}>
            <input type="text" placeholder="بحث..." value={search} onChange={function(e) { setSearch(e.target.value); }}
              style={{ width: 140, padding: '6px 10px 6px 28px', borderRadius: 8, border: '1px solid var(--gray-200)', fontSize: 13, outline: 'none' }} />
            <svg style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', width: 14, height: 14, color: 'var(--gray-400)' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          </div>
          <button onClick={function() { setShowCreateFolder(true); }} style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid var(--gray-200)', background: 'var(--white)', fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, whiteSpace: 'nowrap' }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><line x1="12" y1="11" x2="12" y2="17"/><line x1="9" y1="14" x2="15" y2="14"/></svg>
            مجلد
          </button>
          <button onClick={function() { fileInputRef.current.click(); }} disabled={uploading} style={{ padding: '6px 10px', borderRadius: 8, border: 'none', background: 'var(--primary)', color: 'white', fontSize: 12, cursor: uploading ? 'default' : 'pointer', display: 'flex', alignItems: 'center', gap: 4, opacity: uploading ? 0.6 : 1, whiteSpace: 'nowrap' }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            {uploading ? '...' : 'رفع'}
          </button>
          <input ref={fileInputRef} type="file" multiple style={{ display: 'none' }} onChange={function(e) { handleUpload(e.target.files); e.target.value = ''; }} />
          <div style={{ display: 'flex', gap: 2, background: 'var(--gray-100)', borderRadius: 6, padding: 2, flexShrink: 0 }}>
            <button onClick={function() { setViewMode('grid'); }} style={{ width: 26, height: 26, borderRadius: 4, border: 'none', background: viewMode === 'grid' ? 'var(--white)' : 'transparent', boxShadow: viewMode === 'grid' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
            </button>
            <button onClick={function() { setViewMode('list'); }} style={{ width: 26, height: 26, borderRadius: 4, border: 'none', background: viewMode === 'list' ? 'var(--white)' : 'transparent', boxShadow: viewMode === 'list' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
            </button>
          </div>
          <span style={{ fontSize: 11, color: 'var(--gray-500)', whiteSpace: 'nowrap' }}>{currentFiles.length} ملف</span>
        </div>
      </div>

      {/* Content */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        style={{ flex: 1, overflow: 'auto', background: 'var(--white)', borderRadius: '0 0 12px 12px', padding: 12, border: isDragOver ? '2px dashed var(--primary)' : '2px dashed transparent', transition: 'border 0.2s', position: 'relative' }}
      >
        {isDragOver && (
          <div style={{ position: 'absolute', inset: 0, background: 'rgba(59,130,246,0.05)', borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10, pointerEvents: 'none' }}>
            <div style={{ textAlign: 'center', color: 'var(--primary)' }}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: '0 auto 8px' }}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
              <div style={{ fontSize: 16, fontWeight: 600 }}>أفلت الملفات هنا</div>
            </div>
          </div>
        )}

        {/* Create Folder Modal */}
        {showCreateFolder && (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }} onClick={function() { setShowCreateFolder(false); }}>
            <div style={{ background: 'var(--white)', borderRadius: 12, padding: 24, width: '90%', maxWidth: 360, boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }} onClick={function(e) { e.stopPropagation(); }}>
              <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 600 }}>مجلد جديد</h3>
              <input autoFocus type="text" placeholder="اسم المجلد" value={createFolderValue}
                onChange={function(e) { setCreateFolderValue(e.target.value); }}
                onKeyDown={function(e) { if (e.key === 'Enter') handleCreateFolder(); }}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid var(--gray-200)', fontSize: 14, outline: 'none', boxSizing: 'border-box' }} />
              <div style={{ display: 'flex', gap: 8, marginTop: 16, justifyContent: 'flex-end' }}>
                <button onClick={function() { setShowCreateFolder(false); }} style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid var(--gray-200)', background: 'var(--white)', fontSize: 13, cursor: 'pointer' }}>إلغاء</button>
                <button onClick={handleCreateFolder} style={{ padding: '8px 16px', borderRadius: 8, border: 'none', background: 'var(--primary)', color: 'white', fontSize: 13, cursor: 'pointer' }}>إنشاء</button>
              </div>
            </div>
          </div>
        )}

        {/* Rename Modal */}
        {renaming && (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }} onClick={function() { setRenaming(null); }}>
            <div style={{ background: 'var(--white)', borderRadius: 12, padding: 24, width: '90%', maxWidth: 360, boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }} onClick={function(e) { e.stopPropagation(); }}>
              <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 600 }}>إعادة تسمية</h3>
              <input autoFocus type="text" value={renameValue}
                onChange={function(e) { setRenameValue(e.target.value); }}
                onKeyDown={function(e) { if (e.key === 'Enter') confirmRename(); }}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid var(--gray-200)', fontSize: 14, outline: 'none', boxSizing: 'border-box' }} />
              <div style={{ display: 'flex', gap: 8, marginTop: 16, justifyContent: 'flex-end' }}>
                <button onClick={function() { setRenaming(null); }} style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid var(--gray-200)', background: 'var(--white)', fontSize: 13, cursor: 'pointer' }}>إلغاء</button>
                <button onClick={confirmRename} style={{ padding: '8px 16px', borderRadius: 8, border: 'none', background: 'var(--primary)', color: 'white', fontSize: 13, cursor: 'pointer' }}>حفظ</button>
              </div>
            </div>
          </div>
        )}

        {/* Move Modal */}
        {movingItem && (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }} onClick={function() { setMovingItem(null); }}>
            <div style={{ background: 'var(--white)', borderRadius: 12, padding: 24, width: '90%', maxWidth: 360, maxHeight: 400, overflow: 'auto', boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }} onClick={function(e) { e.stopPropagation(); }}>
              <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 600 }}>نقل إلى</h3>
              {Object.keys(FOLDER_LABELS).map(function(path) {
                return (
                  <button key={path} onClick={function() { confirmMove(path); }}
                    style={{ display: 'block', width: '100%', textAlign: 'right', padding: '10px 12px', borderRadius: 8, border: '1px solid var(--gray-100)', background: path === currentPath ? 'var(--primary-bg)' : 'var(--white)', cursor: 'pointer', marginBottom: 6, fontSize: 13 }}
                  >{FOLDER_LABELS[path]}</button>
                );
              })}
              <button onClick={function() { setMovingItem(null); }} style={{ width: '100%', padding: '8px 16px', borderRadius: 8, border: '1px solid var(--gray-200)', background: 'var(--white)', fontSize: 13, cursor: 'pointer', marginTop: 8 }}>إلغاء</button>
            </div>
          </div>
        )}

        {/* Empty state */}
        {filteredSubfolders.length === 0 && filtered.length === 0 && !search && (
          <div style={{ textAlign: 'center', padding: 60, color: 'var(--gray-400)' }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ width: 56, height: 56, margin: '0 auto 12px', color: 'var(--gray-300)' }}>
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
            <h4 style={{ margin: '0 0 4px', color: 'var(--gray-600)' }}>مجلد فارغ</h4>
            <p style={{ fontSize: 13 }}>اسحب ملفات هنا أو اضغط "رفع"</p>
          </div>
        )}

        {search && filteredSubfolders.length === 0 && filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: 60, color: 'var(--gray-400)' }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ width: 48, height: 48, margin: '0 auto 12px', color: 'var(--gray-300)' }}>
              <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <h4 style={{ margin: '0 0 4px', color: 'var(--gray-600)' }}>لا نتائج</h4>
            <p style={{ fontSize: 13 }}>لا توجد ملفات تطابق "{search}"</p>
          </div>
        )}

        {/* Grid View */}
        {viewMode === 'grid' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: 10 }}>
            {filteredSubfolders.map(function(sf) {
              var count = (files[sf.path] && files[sf.path].files) ? files[sf.path].files.length : 0;
              var isOpen = activeMenu && activeMenu.item && activeMenu.item.path === sf.path;
              return (
                <div key={sf.path} onClick={function() { navigateTo(sf.path); }}
                  style={{ padding: 12, borderRadius: 10, border: '1px solid var(--gray-100)', background: 'var(--white)', cursor: 'pointer', transition: 'all 0.15s', textAlign: 'center', position: 'relative' }}
                  onMouseEnter={function(e) { e.currentTarget.style.borderColor = 'var(--primary)'; e.currentTarget.style.background = 'var(--primary-bg)'; }}
                  onMouseLeave={function(e) { e.currentTarget.style.borderColor = 'var(--gray-100)'; e.currentTarget.style.background = 'var(--white)'; }}
                >
                  <div style={{ position: 'absolute', top: 6, left: 6 }}>
                    <DotsButton onClick={function(e) { setActiveMenu(isOpen ? null : { key: sf.path, item: sf, type: 'folder' }); }} />
                    {isOpen && <ActionsMenu item={sf} type="folder"
                      onOpen={function() { navigateTo(sf.path); }}
                      onRename={function() { handleRename(sf.path, sf.name); }}
                      onDelete={function() { handleDeleteFolder(sf.path, sf.name); }} />}
                  </div>
                  <div style={{ fontSize: 32, marginBottom: 4 }}>📁</div>
                  <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--gray-700)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{sf.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--gray-400)', marginTop: 2 }}>{count} ملف</div>
                </div>
              );
            })}
            {filtered.map(function(file) {
              var isImg = /\.(jpg|jpeg|png|gif|webp)$/i.test(file.name);
              var isVid = /\.(mp4|webm|mov|avi|mkv)$/i.test(file.name);
              var isOpen = activeMenu && activeMenu.item && activeMenu.item.key === file.key;
              return (
                <div key={file.key}
                  onClick={function() { window.open(file.url, '_blank'); }}
                  style={{ padding: 10, borderRadius: 10, border: '1px solid var(--gray-100)', background: 'var(--white)', cursor: 'pointer', transition: 'all 0.15s', textAlign: 'center', position: 'relative' }}
                  onMouseEnter={function(e) { e.currentTarget.style.borderColor = 'var(--primary-light)'; }}
                  onMouseLeave={function(e) { e.currentTarget.style.borderColor = 'var(--gray-100)'; }}
                >
                  <div style={{ position: 'absolute', top: 6, left: 6 }}>
                    <DotsButton onClick={function(e) { setActiveMenu(isOpen ? null : { key: file.key, item: file, type: 'file' }); }} />
                    {isOpen && <ActionsMenu item={file} type="file"
                      onOpen={function() { window.open(file.url, '_blank'); }}
                      onRename={function() { handleRename(file.key, file.name); }}
                      onMove={function() { handleMove(file.key); }}
                      onDelete={function() { handleDeleteFile(file.key, file.name); }} />}
                  </div>
                  {isImg ? (
                    <img src={file.url} alt="" style={{ width: '100%', height: 70, objectFit: 'cover', borderRadius: 6, marginBottom: 6 }} />
                  ) : isVid ? (
                    <div style={{ width: '100%', height: 70, borderRadius: 6, background: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 6 }}>
                      <span style={{ color: 'white', fontSize: 22 }}>▶</span>
                    </div>
                  ) : (
                    <div style={{ width: '100%', height: 70, borderRadius: 6, background: 'var(--gray-50)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 6 }}>
                      <span style={{ fontSize: 28 }}>{getFileIcon(file.name)}</span>
                    </div>
                  )}
                  <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--gray-700)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</div>
                  <div style={{ fontSize: 10, color: 'var(--gray-400)', marginTop: 2 }}>{formatSize(file.size)}</div>
                </div>
              );
            })}
          </div>
        )}

        {/* List View */}
        {viewMode === 'list' && (
          <div style={{ borderRadius: 8, border: '1px solid var(--gray-100)', overflow: 'hidden' }}>
            {/* Desktop header */}
            <div className="desktop-only" style={{ display: 'grid', gridTemplateColumns: '1fr 80px 80px 100px', padding: '8px 12px', background: 'var(--gray-50)', fontSize: 12, fontWeight: 600, color: 'var(--gray-500)', borderBottom: '1px solid var(--gray-100)' }}>
              <span>الاسم</span>
              <span>النوع</span>
              <span>الحجم</span>
              <span>إجراءات</span>
            </div>
            {filteredSubfolders.map(function(sf) {
              var isOpen = activeMenu && activeMenu.item && activeMenu.item.path === sf.path;
              return (
                <div key={sf.path} onClick={function() { navigateTo(sf.path); }}
                  style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', fontSize: 13, borderBottom: '1px solid var(--gray-50)', cursor: 'pointer', transition: 'background 0.1s' }}
                  onMouseEnter={function(e) { e.currentTarget.style.background = 'var(--gray-50)'; }}
                  onMouseLeave={function(e) { e.currentTarget.style.background = 'transparent'; }}
                >
                  <span style={{ fontSize: 18, flexShrink: 0 }}>📁</span>
                  <span style={{ flex: 1, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{sf.name}</span>
                  <span className="desktop-only" style={{ color: 'var(--gray-400)', fontSize: 12 }}>مجلد</span>
                  <span className="desktop-only" style={{ color: 'var(--gray-400)', fontSize: 12 }}>—</span>
                  <div style={{ position: 'relative', flexShrink: 0 }}>
                    <DotsButton onClick={function(e) { setActiveMenu(isOpen ? null : { key: sf.path, item: sf, type: 'folder' }); }} />
                    {isOpen && <ActionsMenu item={sf} type="folder"
                      onOpen={function() { navigateTo(sf.path); }}
                      onRename={function() { handleRename(sf.path, sf.name); }}
                      onDelete={function() { handleDeleteFolder(sf.path, sf.name); }} />}
                  </div>
                </div>
              );
            })}
            {filtered.map(function(file) {
              var ext = file.name.split('.').pop().toUpperCase();
              var isOpen = activeMenu && activeMenu.item && activeMenu.item.key === file.key;
              return (
                <div key={file.key}
                  onClick={function() { window.open(file.url, '_blank'); }}
                  style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', fontSize: 13, borderBottom: '1px solid var(--gray-50)', cursor: 'pointer', transition: 'background 0.1s' }}
                  onMouseEnter={function(e) { e.currentTarget.style.background = 'var(--gray-50)'; }}
                  onMouseLeave={function(e) { e.currentTarget.style.background = 'transparent'; }}
                >
                  <span style={{ fontSize: 18, flexShrink: 0 }}>{getFileIcon(file.name)}</span>
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</span>
                  <span className="desktop-only" style={{ color: 'var(--gray-400)', fontSize: 11, flexShrink: 0 }}>{ext}</span>
                  <span className="desktop-only" style={{ color: 'var(--gray-400)', fontSize: 12, flexShrink: 0 }}>{formatSize(file.size)}</span>
                  <div style={{ position: 'relative', flexShrink: 0 }}>
                    <DotsButton onClick={function(e) { setActiveMenu(isOpen ? null : { key: file.key, item: file, type: 'file' }); }} />
                    {isOpen && <ActionsMenu item={file} type="file"
                      onOpen={function() { window.open(file.url, '_blank'); }}
                      onRename={function() { handleRename(file.key, file.name); }}
                      onMove={function() { handleMove(file.key); }}
                      onDelete={function() { handleDeleteFile(file.key, file.name); }} />}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
