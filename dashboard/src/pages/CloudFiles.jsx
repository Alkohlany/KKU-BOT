import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useToast } from '../components/ToastContext';

var FOLDER_MAP = {
  'kku-bot/news': 'الأخبار',
  'kku-bot/plans': 'الخطط الدراسية',
  'kku-bot/scheduled': 'المنشورات المجدولة',
};

export default function CloudFiles() {
  var _t = useToast();
  var showToast = _t.showToast;
  var _f = useState({});
  var files = _f[0];
  var setFiles = _f[1];
  var _l = useState(true);
  var loading = _l[0];
  var setLoading = _l[1];
  var _s = useState('');
  var search = _s[0];
  var setSearch = _s[1];
  var _a = useState(null);
  var activeFolder = _a[0];
  var setActiveFolder = _a[1];
  var _d = useState(null);
  var deleting = _d[0];
  var setDeleting = _d[1];

  var loadFiles = function() {
    setLoading(true);
    api.getCloudFiles().then(function(data) {
      setFiles(data);
    }).catch(function(err) {
      console.error('Failed to load files:', err);
      showToast('فشل تحميل الملفات', 'error');
    }).finally(function() {
      setLoading(false);
    });
  };

  useEffect(function() {
    loadFiles();
  }, []);

  var handleDelete = function(key, name) {
    setDeleting(key);
    api.deleteCloudFile(key).then(function() {
      showToast('تم حذف الملف: ' + name, 'success');
      loadFiles();
    }).catch(function(err) {
      console.error('Failed to delete:', err);
      showToast('فشل حذف الملف', 'error');
    }).finally(function() {
      setDeleting(null);
    });
  };

  var allFiles = [];
  if (activeFolder) {
    allFiles = files[activeFolder] || [];
  } else {
    Object.keys(files).forEach(function(k) {
      allFiles = allFiles.concat(files[k] || []);
    });
  }

  var filtered = allFiles.filter(function(f) {
    if (!search) return true;
    return f.name.toLowerCase().indexOf(search.toLowerCase()) !== -1;
  });

  var totalSize = allFiles.reduce(function(sum, f) { return sum + (f.size || 0); }, 0);
  var formatSize = function(bytes) {
    if (bytes > 1048576) return (bytes / 1048576).toFixed(1) + ' MB';
    if (bytes > 1024) return (bytes / 1024).toFixed(0) + ' KB';
    return bytes + ' B';
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 40, color: 'var(--gray-400)' }}>جاري تحميل الملفات...</div>;
  }

  return (
    <div className="card">
      <div className="card-header" style={{ flexWrap: 'wrap', gap: 12 }}>
        <div className="search-box">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input type="text" placeholder="بحث في الملفات..." value={search} onChange={function(e) { setSearch(e.target.value); }} />
        </div>
        <div style={{ fontSize: 13, color: 'var(--gray-500)' }}>
          {allFiles.length} ملف | {formatSize(totalSize)}
        </div>
      </div>

      <div style={{ padding: '0 20px 16px', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button
          onClick={function() { setActiveFolder(null); }}
          style={{ padding: '6px 16px', borderRadius: 20, border: '1px solid var(--gray-200)', background: !activeFolder ? 'var(--primary)' : 'var(--gray-50)', color: !activeFolder ? 'white' : 'var(--gray-600)', fontSize: 13, cursor: 'pointer', transition: 'all 0.2s' }}
        >الكل</button>
        {Object.keys(FOLDER_MAP).map(function(key) {
          var count = (files[key] || []).length;
          return (
            <button
              key={key}
              onClick={function() { setActiveFolder(key); }}
              style={{ padding: '6px 16px', borderRadius: 20, border: '1px solid var(--gray-200)', background: activeFolder === key ? 'var(--primary)' : 'var(--gray-50)', color: activeFolder === key ? 'white' : 'var(--gray-600)', fontSize: 13, cursor: 'pointer', transition: 'all 0.2s' }}
            >{FOLDER_MAP[key]} ({count})</button>
          );
        })}
      </div>

      <div className="table-container desktop-only">
        <table>
          <thead>
            <tr>
              <th>الملف</th>
              <th>المجلد</th>
              <th>الحجم</th>
              <th>إجراءات</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(function(file) {
              var isImage = /\.(jpg|jpeg|png|gif|webp)$/i.test(file.name);
              var isVideo = /\.(mp4|webm|mov|avi|mkv)$/i.test(file.name);
              var isPdf = /\.pdf$/i.test(file.name);
              return (
                <tr key={file.key}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      {isImage ? (
                        <img src={file.url} alt="" style={{ width: 40, height: 40, objectFit: 'cover', borderRadius: 6, flexShrink: 0 }} />
                      ) : isVideo ? (
                        <div style={{ width: 40, height: 40, borderRadius: 6, background: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <span style={{ color: 'white', fontSize: 14 }}>▶</span>
                        </div>
                      ) : isPdf ? (
                        <div style={{ width: 40, height: 40, borderRadius: 6, background: '#FFF3E0', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <span style={{ fontSize: 18 }}>📕</span>
                        </div>
                      ) : (
                        <div style={{ width: 40, height: 40, borderRadius: 6, background: 'var(--gray-50)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <span style={{ fontSize: 18 }}>📄</span>
                        </div>
                      )}
                      <div style={{ overflow: 'hidden' }}>
                        <div style={{ fontSize: 13, color: 'var(--gray-700)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 300 }}>{file.name}</div>
                        <a href={file.url} target="_blank" rel="noopener" style={{ fontSize: 11, color: 'var(--primary)', textDecoration: 'none' }}>فتح الرابط</a>
                      </div>
                    </div>
                  </td>
                  <td><span style={{ fontSize: 12, color: 'var(--gray-500)' }}>{FOLDER_MAP[file.folder] || file.folder}</span></td>
                  <td><span style={{ fontSize: 12, color: 'var(--gray-500)' }}>{formatSize(file.size)}</span></td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <a href={file.url} download={file.name} className="btn btn-secondary btn-sm" style={{ textDecoration: 'none' }}>تحميل</a>
                      <button
                        className="btn btn-danger btn-sm"
                        disabled={deleting === file.key}
                        onClick={function() { if (confirm('هل أنت متأكد من حذف هذا الملف؟')) handleDelete(file.key, file.name); }}
                      >{deleting === file.key ? '...' : 'حذف'}</button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ width: 48, height: 48, color: 'var(--gray-300)', marginBottom: 12 }}>
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
            <h4>لا توجد ملفات</h4>
          </div>
        )}
      </div>

      <div className="mobile-cards">
        {filtered.map(function(file) {
          var isImage = /\.(jpg|jpeg|png|gif|webp)$/i.test(file.name);
          var isVideo = /\.(mp4|webm|mov|avi|mkv)$/i.test(file.name);
          return (
            <div key={file.key} className="mobile-card">
              <div className="mobile-card-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {isImage ? (
                    <img src={file.url} alt="" style={{ width: 36, height: 36, objectFit: 'cover', borderRadius: 4 }} />
                  ) : isVideo ? (
                    <div style={{ width: 36, height: 36, borderRadius: 4, background: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <span style={{ color: 'white', fontSize: 12 }}>▶</span>
                    </div>
                  ) : (
                    <span style={{ fontSize: 20 }}>📄</span>
                  )}
                  <strong style={{ fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</strong>
                </div>
              </div>
              <div className="mobile-card-body">
                <p style={{ fontSize: 12, color: 'var(--gray-500)' }}>{FOLDER_MAP[file.folder] || file.folder} | {formatSize(file.size)}</p>
              </div>
              <div className="mobile-card-meta">
                <a href={file.url} target="_blank" rel="noopener" className="btn btn-secondary btn-sm" style={{ textDecoration: 'none' }}>فتح</a>
                <a href={file.url} download={file.name} className="btn btn-secondary btn-sm" style={{ textDecoration: 'none' }}>تحميل</a>
                <button
                  className="btn btn-danger btn-sm"
                  disabled={deleting === file.key}
                  onClick={function() { if (confirm('هل أنت متأكد من حذف هذا الملف؟')) handleDelete(file.key, file.name); }}
                >حذف</button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
