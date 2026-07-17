import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';
import { useToast } from '../components/ToastContext';

var FOLDER_META = {
  'kku-bot': { label: 'الكل', icon: '📂' },
  'kku-bot/news': { label: 'الأخبار', icon: '📰' },
  'kku-bot/plans': { label: 'الخطط الدراسية', icon: '📚' },
  'kku-bot/scheduled': { label: 'المنشورات المجدولة', icon: '📅' },
};

function fileIcon(name) {
  if (/\.(jpg|jpeg|png|gif|webp|svg)$/i.test(name)) return '🖼️';
  if (/\.(mp4|webm|mov|avi|mkv)$/i.test(name)) return '🎬';
  if (/\.pdf$/i.test(name)) return '📕';
  if (/\.(zip|rar|7z|tar|gz)$/i.test(name)) return '📦';
  if (/\.(mp3|wav|ogg|flac|m4a)$/i.test(name)) return '🎵';
  if (/\.(xls|xlsx|csv)$/i.test(name)) return '📊';
  if (/\.(ppt|pptx)$/i.test(name)) return '📽️';
  return '📄';
}

function fmtSize(b) {
  if (!b) return '0 B';
  if (b > 1048576) return (b / 1048576).toFixed(1) + ' MB';
  if (b > 1024) return (b / 1024).toFixed(0) + ' KB';
  return b + ' B';
}

function SvgIcon(props) {
  return <svg width={props.s || 16} height={props.s || 16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{props.children}</svg>;
}

function BackIcon() { return <SvgIcon><path d="M15 18l-6-6 6-6"/></SvgIcon>; }
function SearchIcon() { return <SvgIcon s={14}><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></SvgIcon>; }
function FolderPlusIcon() { return <SvgIcon s={14}><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><line x1="12" y1="11" x2="12" y2="17"/><line x1="9" y1="14" x2="15" y2="14"/></SvgIcon>; }
function UploadIcon() { return <SvgIcon s={14}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></SvgIcon>; }
function GridIcon() { return <SvgIcon s={13}><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></SvgIcon>; }
function ListIcon() { return <SvgIcon s={13}><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></SvgIcon>; }
function OpenIcon() { return <SvgIcon s={16}><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></SvgIcon>; }
function EditIcon() { return <SvgIcon s={16}><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></SvgIcon>; }
function MoveIcon() { return <SvgIcon s={16}><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><line x1="12" y1="11" x2="12" y2="17"/></SvgIcon>; }
function TrashIcon() { return <SvgIcon s={16}><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></SvgIcon>; }
function DotsIcon() { return <SvgIcon s={18}><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></SvgIcon>; }

/* ── Bottom Sheet Actions Menu ── */
function ActionsSheet(props) {
  var onClose = props.onClose;
  var items = props.items;
  return (
    <div className="cf-sheet-overlay" onClick={onClose}>
      <div className="cf-sheet" onClick={function(e) { e.stopPropagation(); }}>
        <div className="cf-sheet-handle" />
        {items.map(function(item, i) {
          return (
            <button key={i} className={'cf-sheet-btn' + (item.danger ? ' danger' : '')} onClick={item.onClick}>
              {item.icon}
              <span>{item.label}</span>
            </button>
          );
        })}
        <button className="cf-sheet-btn cancel" onClick={onClose}>إلغاء</button>
      </div>
    </div>
  );
}

/* ── Modal Base ── */
function Modal(props) {
  return (
    <div className="cf-sheet-overlay" onClick={props.onClose}>
      <div className="cf-modal" onClick={function(e) { e.stopPropagation(); }}>
        <h3 className="cf-modal-title">{props.title}</h3>
        {props.children}
      </div>
    </div>
  );
}

/* ── Main Component ── */
export default function CloudFiles() {
  var toast = useToast().showToast;
  var _data = useState({});
  var data = _data[0], setData = _data[1];
  var _loading = useState(true);
  var loading = _loading[0], setLoading = _loading[1];
  var _path = useState('kku-bot');
  var curPath = _path[0], setCurPath = _path[1];
  var _search = useState('');
  var search = _search[0], setSearch = _search[1];
  var _view = useState('grid');
  var view = _view[0], setView = _view[1];
  var _sheet = useState(null);
  var sheet = _sheet[0], setSheet = _sheet[1];
  var _rename = useState(null);
  var rename = _rename[0], setRename = _rename[1];
  var _renameVal = useState('');
  var renameVal = _renameVal[0], setRenameVal = _renameVal[1];
  var _newFolder = useState(false);
  var showNewFolder = _newFolder[0], setShowNewFolder = _newFolder[1];
  var _folderName = useState('');
  var folderName = _folderName[0], setFolderName = _folderName[1];
  var _uploading = useState(false);
  var uploading = _uploading[0], setUploading = _uploading[1];
  var _moving = useState(null);
  var moving = _moving[0], setMoving = _moving[1];
  var fileRef = useRef(null);

  var load = useCallback(function() {
    setLoading(true);
    api.getCloudFiles().then(function(d) { setData(d); }).catch(function() { toast('فشل تحميل الملفات', 'error'); }).finally(function() { setLoading(false); });
  }, []);

  useEffect(function() { load(); }, []);

  var current = data[curPath] || { files: [], subfolders: [] };
  var files = current.files || [];
  var subfolders = current.subfolders || [];

  var breadcrumbs = curPath.split('/').map(function(_, i, arr) {
    var p = arr.slice(0, i + 1).join('/');
    return { label: (FOLDER_META[p] || {}).label || arr[i], path: p };
  });

  var fFiles = files.filter(function(f) { return !search || f.name.toLowerCase().includes(search.toLowerCase()); });
  var fFolders = subfolders.filter(function(s) { return !search || s.name.toLowerCase().includes(search.toLowerCase()); });

  function nav(path) {
    setCurPath(path);
    setSearch('');
    setSheet(null);
    setLoading(true);
    var q = path === 'kku-bot' ? '' : path;
    api.getCloudFiles(q).then(function(d) {
      setData(function(prev) {
        var next = Object.assign({}, prev);
        if (path === 'kku-bot') { Object.keys(d).forEach(function(k) { next[k] = d[k]; }); }
        else { next[path] = d; }
        return next;
      });
    }).finally(function() { setLoading(false); });
  }

  function goUp() {
    var p = curPath.split('/');
    if (p.length > 1) { p.pop(); nav(p.join('/')); }
  }

  function createFolder() {
    if (!folderName.trim()) return;
    api.createCloudFolder(curPath + '/' + folderName.trim()).then(function() {
      toast('تم إنشاء المجلد', 'success');
      setShowNewFolder(false);
      setFolderName('');
      load();
    }).catch(function() { toast('فشل إنشاء المجلد', 'error'); });
  }

  function delFolder(path, name) {
    setSheet(null);
    if (!confirm('حذف المجلد "' + name + '" وكل محتوياته؟')) return;
    api.deleteCloudFolder(path).then(function() {
      toast('تم حذف: ' + name, 'success');
      if (curPath === path) goUp(); else load();
    }).catch(function() { toast('فشل الحذف', 'error'); });
  }

  function delFile(key, name) {
    setSheet(null);
    if (!confirm('حذف "' + name + '"؟')) return;
    api.deleteCloudFile(key).then(function() {
      toast('تم حذف: ' + name, 'success');
      load();
    }).catch(function() { toast('فشل الحذف', 'error'); });
  }

  function doRename() {
    if (!renameVal.trim() || !rename) return;
    api.renameCloudFile(rename, renameVal.trim()).then(function() {
      toast('تمت إعادة التسمية', 'success');
      setRename(null);
      load();
    }).catch(function() { toast('فشل إعادة التسمية', 'error'); });
  }

  function doMove(dest) {
    if (!moving) return;
    api.moveCloudFile(moving, dest).then(function() {
      toast('تم النقل', 'success');
      setMoving(null);
      load();
    }).catch(function() { toast('فشل النقل', 'error'); });
  }

  function upload(fileList) {
    if (!fileList || !fileList.length) return;
    setUploading(true);
    var total = fileList.length, done = 0, err = 0;
    Array.from(fileList).forEach(function(f) {
      api.uploadCloudFile(f, curPath).then(function() { done++; }).catch(function() { err++; }).finally(function() {
        if (done + err === total) {
          setUploading(false);
          toast('تم رفع ' + done + ' ملف' + (err ? ' (' + err + ' فشل)' : ''), err ? 'warning' : 'success');
          load();
        }
      });
    });
  }

  function openSheet(type, item) {
    var key = type === 'folder' ? item.path : item.key;
    setSheet({ type: type, item: item, key: key,
      items: type === 'folder' ? [
        { icon: <OpenIcon />, label: 'فتح', onClick: function() { setSheet(null); nav(item.path); } },
        { icon: <EditIcon />, label: 'إعادة تسمية', onClick: function() { setSheet(null); setRename(item.path); setRenameVal(item.name); } },
        { icon: <TrashIcon />, label: 'حذف المجلد', danger: true, onClick: function() { delFolder(item.path, item.name); } },
      ] : [
        { icon: <OpenIcon />, label: 'فتح', onClick: function() { setSheet(null); window.open(item.url, '_blank'); } },
        { icon: <EditIcon />, label: 'إعادة تسمية', onClick: function() { setSheet(null); setRename(item.key); setRenameVal(item.name); } },
        { icon: <MoveIcon />, label: 'نقل إلى...', onClick: function() { setSheet(null); setMoving(item.key); } },
        { icon: <TrashIcon />, label: 'حذف', danger: true, onClick: function() { delFile(item.key, item.name); } },
      ]
    });
  }

  if (loading && !Object.keys(data).length) {
    return <div className="cf-loading"><div className="cf-spinner" /><span>جاري التحميل...</span></div>;
  }

  return (
    <div className="cf-page">
      {/* ── Toolbar ── */}
      <div className="cf-toolbar">
        <button className="cf-btn-icon" onClick={goUp} disabled={curPath === 'kku-bot'}>
          <BackIcon />
        </button>
        <div className="cf-breadcrumbs">
          {breadcrumbs.map(function(bc, i) {
            return (
              <React.Fragment key={bc.path}>
                {i > 0 && <span className="cf-bc-sep">/</span>}
                <button className={'cf-bc-btn' + (i === breadcrumbs.length - 1 ? ' active' : '')} onClick={function() { nav(bc.path); }}>{bc.label}</button>
              </React.Fragment>
            );
          })}
        </div>
        <div className="cf-toolbar-actions">
          <div className="cf-search">
            <SearchIcon />
            <input type="text" placeholder="بحث..." value={search} onChange={function(e) { setSearch(e.target.value); }} />
          </div>
          <button className="cf-btn cf-btn-outline" onClick={function() { setShowNewFolder(true); }}>
            <FolderPlusIcon /><span className="cf-btn-label">مجلد</span>
          </button>
          <button className="cf-btn cf-btn-primary" onClick={function() { fileRef.current.click(); }} disabled={uploading}>
            <UploadIcon /><span className="cf-btn-label">{uploading ? 'جاري...' : 'رفع'}</span>
          </button>
          <input ref={fileRef} type="file" multiple hidden onChange={function(e) { upload(e.target.files); e.target.value = ''; }} />
          <div className="cf-view-toggle">
            <button className={view === 'grid' ? 'active' : ''} onClick={function() { setView('grid'); }}><GridIcon /></button>
            <button className={view === 'list' ? 'active' : ''} onClick={function() { setView('list'); }}><ListIcon /></button>
          </div>
          <span className="cf-count">{files.length} ملف</span>
        </div>
      </div>

      {/* ── Content ── */}
      <div className="cf-content">
        {!fFolders.length && !fFiles.length && !search && (
          <div className="cf-empty">
            <div className="cf-empty-icon">📂</div>
            <h4>مجلد فارغ</h4>
            <p>اسحب ملفات هنا أو اضغط "رفع"</p>
          </div>
        )}
        {search && !fFolders.length && !fFiles.length && (
          <div className="cf-empty">
            <div className="cf-empty-icon">🔍</div>
            <h4>لا نتائج</h4>
            <p>"{search}"</p>
          </div>
        )}

        {/* Grid */}
        {view === 'grid' && (fFolders.length > 0 || fFiles.length > 0) && (
          <div className="cf-grid">
            {fFolders.map(function(sf) {
              var c = data[sf.path] && data[sf.path].files ? data[sf.path].files.length : 0;
              return (
                <div key={sf.path} className="cf-card cf-folder" onClick={function() { nav(sf.path); }}>
                  <button className="cf-dots" onClick={function(e) { e.stopPropagation(); openSheet('folder', sf); }}><DotsIcon /></button>
                  <div className="cf-folder-icon">📁</div>
                  <div className="cf-card-name">{sf.name}</div>
                  <div className="cf-card-meta">{c} ملف</div>
                </div>
              );
            })}
            {fFiles.map(function(f) {
              var isImg = /\.(jpg|jpeg|png|gif|webp)$/i.test(f.name);
              var isVid = /\.(mp4|webm|mov|avi|mkv)$/i.test(f.name);
              return (
                <div key={f.key} className="cf-card cf-file" onClick={function() { window.open(f.url, '_blank'); }}>
                  <button className="cf-dots" onClick={function(e) { e.stopPropagation(); openSheet('file', f); }}><DotsIcon /></button>
                  {isImg ? <img src={f.url} alt="" className="cf-thumb" /> : isVid ? <div className="cf-thumb cf-thumb-video"><span>▶</span></div> : <div className="cf-thumb cf-thumb-icon"><span>{fileIcon(f.name)}</span></div>}
                  <div className="cf-card-name">{f.name}</div>
                  <div className="cf-card-meta">{fmtSize(f.size)}</div>
                </div>
              );
            })}
          </div>
        )}

        {/* List */}
        {view === 'list' && (fFolders.length > 0 || fFiles.length > 0) && (
          <div className="cf-list">
            <div className="cf-list-header">
              <span className="cf-list-col-name">الاسم</span>
              <span className="cf-list-col-type desktop-only">النوع</span>
              <span className="cf-list-col-size desktop-only">الحجم</span>
              <span className="cf-list-col-actions"></span>
            </div>
            {fFolders.map(function(sf) {
              return (
                <div key={sf.path} className="cf-list-row" onClick={function() { nav(sf.path); }}>
                  <span className="cf-list-col-name"><span className="cf-list-icon">📁</span>{sf.name}</span>
                  <span className="cf-list-col-type desktop-only">مجلد</span>
                  <span className="cf-list-col-size desktop-only">—</span>
                  <span className="cf-list-col-actions"><button className="cf-dots-sm" onClick={function(e) { e.stopPropagation(); openSheet('folder', sf); }}><DotsIcon /></button></span>
                </div>
              );
            })}
            {fFiles.map(function(f) {
              var ext = f.name.split('.').pop().toUpperCase();
              return (
                <div key={f.key} className="cf-list-row" onClick={function() { window.open(f.url, '_blank'); }}>
                  <span className="cf-list-col-name"><span className="cf-list-icon">{fileIcon(f.name)}</span>{f.name}</span>
                  <span className="cf-list-col-type desktop-only">{ext}</span>
                  <span className="cf-list-col-size desktop-only">{fmtSize(f.size)}</span>
                  <span className="cf-list-col-actions"><button className="cf-dots-sm" onClick={function(e) { e.stopPropagation(); openSheet('file', f); }}><DotsIcon /></button></span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Actions Bottom Sheet ── */}
      {sheet && <ActionsSheet items={sheet.items} onClose={function() { setSheet(null); }} />}

      {/* ── New Folder Modal ── */}
      {showNewFolder && (
        <Modal title="مجلد جديد" onClose={function() { setShowNewFolder(false); }}>
          <input className="cf-input" autoFocus type="text" placeholder="اسم المجلد" value={folderName}
            onChange={function(e) { setFolderName(e.target.value); }}
            onKeyDown={function(e) { if (e.key === 'Enter') createFolder(); }} />
          <div className="cf-modal-actions">
            <button className="cf-btn cf-btn-outline" onClick={function() { setShowNewFolder(false); }}>إلغاء</button>
            <button className="cf-btn cf-btn-primary" onClick={createFolder}>إنشاء</button>
          </div>
        </Modal>
      )}

      {/* ── Rename Modal ── */}
      {rename && (
        <Modal title="إعادة تسمية" onClose={function() { setRename(null); }}>
          <input className="cf-input" autoFocus type="text" value={renameVal}
            onChange={function(e) { setRenameVal(e.target.value); }}
            onKeyDown={function(e) { if (e.key === 'Enter') doRename(); }} />
          <div className="cf-modal-actions">
            <button className="cf-btn cf-btn-outline" onClick={function() { setRename(null); }}>إلغاء</button>
            <button className="cf-btn cf-btn-primary" onClick={doRename}>حفظ</button>
          </div>
        </Modal>
      )}

      {/* ── Move Modal ── */}
      {moving && (
        <Modal title="نقل إلى" onClose={function() { setMoving(null); }}>
          {Object.keys(FOLDER_META).map(function(p) {
            return <button key={p} className={'cf-folder-btn' + (p === curPath ? ' active' : '')} onClick={function() { doMove(p); }}>{FOLDER_META[p].icon} {FOLDER_META[p].label}</button>;
          })}
          <button className="cf-btn cf-btn-outline" style={{ width: '100%', marginTop: 8 }} onClick={function() { setMoving(null); }}>إلغاء</button>
        </Modal>
      )}
    </div>
  );
}
