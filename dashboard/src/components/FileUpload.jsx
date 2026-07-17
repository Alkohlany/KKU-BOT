import React, { useState, useEffect } from 'react';
import api from '../services/api';

function fileIcon(name) {
  if (/\.(jpg|jpeg|png|gif|webp|svg)$/i.test(name)) return '🖼️';
  if (/\.(mp4|webm|mov|avi|mkv)$/i.test(name)) return '🎬';
  if (/\.pdf$/i.test(name)) return '📕';
  if (/\.(zip|rar|7z)$/i.test(name)) return '📦';
  if (/\.(mp3|wav|ogg|m4a)$/i.test(name)) return '🎵';
  return '📄';
}

function fmtSize(b) {
  if (!b) return '0 B';
  if (b > 1048576) return (b / 1048576).toFixed(1) + ' MB';
  if (b > 1024) return (b / 1024).toFixed(0) + ' KB';
  return b + ' B';
}

function FileItem(props) {
  var file = props.file;
  var onRemove = props.onRemove;
  var tag = props.tag;
  var tagColor = props.tagColor || 'var(--primary)';
  var isCloud = file._isCloud;
  var isImage = file.type && file.type.startsWith('image/');
  return (
    <div className="fu-file-item">
      <div className="fu-file-icon">
        {isCloud ? <span>☁️</span> : isImage ? <img src={URL.createObjectURL(file)} alt="" /> : <span>{fileIcon(file.name)}</span>}
      </div>
      <div className="fu-file-info">
        <span className="fu-file-name">{file.name}</span>
        {tag && <span className="fu-file-tag" style={{ color: tagColor, background: tagColor + '15' }}>{tag}</span>}
      </div>
      <button type="button" className="fu-file-remove" onClick={onRemove}>✕</button>
    </div>
  );
}

export default function FileUpload(props) {
  var files = props.files;
  var setFiles = props.setFiles;
  var asDocument = props.asDocument;
  var setAsDocument = props.setAsDocument;
  var label = props.label || 'الملفات المرفقة';
  var existingFiles = props.existingFiles || [];
  var onRemoveExisting = props.onRemoveExisting;

  var _r = useState([]);
  var removedExisting = _r[0], setRemovedExisting = _r[1];
  var _b = useState(false);
  var showBrowser = _b[0], setShowBrowser = _b[1];
  var _cloud = useState({});
  var cloudData = _cloud[0], setCloudData = _cloud[1];
  var _loading = useState(false);
  var loadingCloud = _loading[0], setLoadingCloud = _loading[1];
  var _path = useState('kku-bot');
  var cloudPath = _path[0], setCloudPath = _path[1];
  var _search = useState('');
  var search = _search[0], setSearch = _search[1];
  var _selected = useState([]);
  var selected = _selected[0], setSelected = _selected[1];

  function loadCloud(path) {
    setLoadingCloud(true);
    var q = path === 'kku-bot' ? '' : path;
    api.getCloudFiles(q).then(function(d) {
      setCloudData(function(prev) {
        var next = Object.assign({}, prev);
        if (path === 'kku-bot') { Object.keys(d).forEach(function(k) { next[k] = d[k]; }); }
        else { next[path] = d; }
        return next;
      });
    }).catch(function() {}).finally(function() { setLoadingCloud(false); });
  }

  useEffect(function() {
    if (showBrowser) {
      setSelected([]);
      setCloudPath('kku-bot');
      loadCloud('kku-bot');
    }
  }, [showBrowser]);

  function navCloud(path) {
    setCloudPath(path);
    setSearch('');
    loadCloud(path);
  }

  var currentCloud = cloudData[cloudPath] || { files: [], subfolders: [] };
  var cFiles = (currentCloud.files || []).filter(function(f) { return !search || f.name.toLowerCase().includes(search.toLowerCase()); });
  var cFolders = (currentCloud.subfolders || []).filter(function(s) { return !search || s.name.toLowerCase().includes(search.toLowerCase()); });

  var breadcrumbs = cloudPath.split('/').map(function(_, i, arr) {
    var p = arr.slice(0, i + 1).join('/');
    return { label: arr[i], path: p };
  });

  function isAlreadySelected(url) {
    return existingFiles.some(function(f) { return f.url === url; }) || files.some(function(f) { return f._cloudUrl === url; });
  }

  function toggleSelect(file) {
    if (isAlreadySelected(file.url)) return;
    setSelected(function(prev) {
      var exists = prev.some(function(f) { return f.url === file.url; });
      if (exists) return prev.filter(function(f) { return f.url !== file.url; });
      return prev.concat([file]);
    });
  }

  function confirmCloudSelect() {
    var newFiles = selected.map(function(f) {
      var fake = new File(['cloud'], f.name, { type: 'text/plain' });
      fake._cloudUrl = f.url;
      fake._cloudKey = f.key;
      fake._isCloud = true;
      return fake;
    });
    setFiles(function(prev) { return prev.concat(newFiles); });
    setShowBrowser(false);
  }

  function handleLocalFiles(e) {
    var selected = Array.from(e.target.files);
    setFiles(function(prev) { return prev.concat(selected); });
  }

  function removeFile(index) {
    setFiles(files.filter(function(_, i) { return i !== index; }));
  }

  return (
    <div className="fu-container">
      {/* Header */}
      <div className="fu-header">
        <span className="fu-label">{label}</span>
        <label className="fu-doc-toggle">
          <input type="checkbox" checked={asDocument} onChange={function(e) { setAsDocument(e.target.checked); }} />
          <span>إرسال كملف</span>
        </label>
      </div>

      <div className="fu-body">
        {/* Existing Files */}
        {existingFiles.length > 0 && (
          <div className="fu-section">
            <div className="fu-section-title">الملفات الحالية</div>
            {existingFiles.map(function(file, idx) {
              if (removedExisting.indexOf(idx) !== -1) return null;
              return (
                <FileItem key={'ex-' + idx} file={file} tag="حالي" tagColor="var(--success)"
                  onRemove={function() {
                    var next = removedExisting.concat([idx]);
                    setRemovedExisting(next);
                    if (onRemoveExisting) onRemoveExisting(next);
                  }} />
              );
            })}
          </div>
        )}

        {/* New Files */}
        {files.length > 0 && (
          <div className="fu-section">
            <div className="fu-section-title">ملفات جديدة</div>
            {files.map(function(file, i) {
              return (
                <FileItem key={'new-' + i} file={file}
                  tag={file._isCloud ? 'سحابة' : null} tagColor="var(--info)"
                  onRemove={function() { removeFile(i); }} />
              );
            })}
          </div>
        )}

        {/* Add Buttons */}
        <div className="fu-add-row">
          <label className="fu-add-btn">
            <span className="fu-add-icon">📎</span>
            <span>ملفات جديدة</span>
            <input type="file" multiple hidden onChange={handleLocalFiles} />
          </label>
          <button type="button" className="fu-add-btn fu-add-cloud" onClick={function() { setShowBrowser(true); }}>
            <span className="fu-add-icon">☁️</span>
            <span>اختيار من السحابة</span>
          </button>
        </div>
      </div>

      {/* Cloud Browser Modal */}
      {showBrowser && (
        <div className="fu-overlay" onClick={function() { setShowBrowser(false); }}>
          <div className="fu-browser" onClick={function(e) { e.stopPropagation(); }}>
            {/* Browser Header */}
            <div className="fu-browser-header">
              <h3>اختيار من السحابة</h3>
              <button className="fu-browser-close" onClick={function() { setShowBrowser(false); }}>✕</button>
            </div>

            {/* Breadcrumbs */}
            <div className="fu-browser-nav">
              <div className="fu-browser-breadcrumbs">
                {breadcrumbs.map(function(bc, i) {
                  return (
                    <React.Fragment key={bc.path}>
                      {i > 0 && <span>/</span>}
                      <button className={i === breadcrumbs.length - 1 ? 'active' : ''} onClick={function() { navCloud(bc.path); }}>{bc.label}</button>
                    </React.Fragment>
                  );
                })}
              </div>
              <div className="fu-browser-search">
                <input type="text" placeholder="بحث..." value={search} onChange={function(e) { setSearch(e.target.value); }} />
              </div>
            </div>

            {/* Content */}
            <div className="fu-browser-content">
              {loadingCloud ? (
                <div className="fu-browser-empty">جاري التحميل...</div>
              ) : !cFolders.length && !cFiles.length ? (
                <div className="fu-browser-empty">لا توجد ملفات</div>
              ) : (
                <div className="fu-browser-grid">
                  {cFolders.map(function(sf) {
                    return (
                      <div key={sf.path} className="fu-browser-folder" onClick={function() { navCloud(sf.path); }}>
                        <span>📁</span>
                        <span className="fu-browser-folder-name">{sf.name}</span>
                      </div>
                    );
                  })}
                  {cFiles.map(function(f) {
                    var isImg = /\.(jpg|jpeg|png|gif|webp)$/i.test(f.name);
                    var isVid = /\.(mp4|webm|mov|avi|mkv)$/i.test(f.name);
                    var done = isAlreadySelected(f.url);
                    var sel = selected.some(function(s) { return s.url === f.url; });
                    return (
                      <div key={f.key} className={'fu-browser-file' + (done ? ' disabled' : '') + (sel ? ' selected' : '')} onClick={function() { toggleSelect(f); }}>
                        <div className="fu-browser-check">{sel ? '✓' : ''}</div>
                        {isImg ? <img src={f.url} alt="" className="fu-browser-thumb" /> : isVid ? <div className="fu-browser-thumb fu-browser-video"><span>▶</span></div> : <div className="fu-browser-thumb fu-browser-icon"><span>{fileIcon(f.name)}</span></div>}
                        <div className="fu-browser-file-name">{f.name}</div>
                        <div className="fu-browser-file-size">{fmtSize(f.size)}</div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="fu-browser-footer">
              <span className="fu-browser-count">{selected.length} ملف محدد</span>
              <div className="fu-browser-actions">
                <button className="cf-btn cf-btn-outline" onClick={function() { setShowBrowser(false); }}>إلغاء</button>
                <button className="cf-btn cf-btn-primary" disabled={!selected.length} onClick={confirmCloudSelect}>اختيار ({selected.length})</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
