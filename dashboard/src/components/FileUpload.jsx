import { useState, useEffect } from 'react';
import api from '../services/api';

var FOLDER_MAP = {
  'kku-bot/news': 'الأخبار',
  'kku-bot/plans': 'الخطط الدراسية',
  'kku-bot/scheduled': 'المنشورات المجدولة',
};

export default function FileUpload(props) {
  var files = props.files;
  var setFiles = props.setFiles;
  var asDocument = props.asDocument;
  var setAsDocument = props.setAsDocument;
  var label = props.label || 'الملفات المرفقة';
  var existingFiles = props.existingFiles || [];
  var onRemoveExisting = props.onRemoveExisting;

  var _r = useState([]);
  var removedExisting = _r[0];
  var setRemovedExisting = _r[1];

  var _b = useState(false);
  var showBrowser = _b[0];
  var setShowBrowser = _b[1];

  var _c = useState({});
  var cloudFiles = _c[0];
  var setCloudFiles = _c[1];

  var _l = useState(false);
  var loadingCloud = _l[0];
  var setLoadingCloud = _l[1];

  var _f = useState(null);
  var activeFolder = _f[0];
  var setActiveFolder = _f[1];

  var _s = useState('');
  var searchQuery = _s[0];
  var setSearchQuery = _s[1];

  var handleFileChange = function(e) {
    var selected = Array.from(e.target.files);
    setFiles(function(prev) { return prev.concat(selected); });
  };

  var removeFile = function(index) {
    setFiles(files.filter(function(_, i) { return i !== index; }));
  };

  var loadCloudFiles = function() {
    setLoadingCloud(true);
    api.getCloudFiles(props.cloudFolder).then(function(data) {
      if (props.cloudFolder) {
        var obj = {};
        obj[props.cloudFolder] = data;
        setCloudFiles(obj);
        setActiveFolder(props.cloudFolder);
      } else {
        setCloudFiles(data);
      }
    }).catch(function(err) {
      console.error('Failed to load cloud files:', err);
    }).finally(function() {
      setLoadingCloud(false);
    });
  };

  useEffect(function() {
    if (showBrowser) {
      loadCloudFiles();
    }
  }, [showBrowser]);

  var handleSelectCloudFile = function(file) {
    var isSelected = existingFiles.some(function(f) { return f.url === file.url; }) ||
                     files.some(function(f) { return f._cloudUrl === file.url; });
    if (isSelected) return;
    var fakeFile = new File(['cloud'], file.name, { type: 'text/plain' });
    fakeFile._cloudUrl = file.url;
    fakeFile._cloudKey = file.key;
    fakeFile._isCloud = true;
    setFiles(function(prev) { return prev.concat([fakeFile]); });
    setShowBrowser(false);
  };

  var handleDeleteCloudFile = function(key, e) {
    e.stopPropagation();
    api.deleteCloudFile(key).then(function() {
      loadCloudFiles();
    }).catch(function(err) {
      console.error('Failed to delete:', err);
    });
  };

  var allFiles = [];
  if (activeFolder) {
    allFiles = cloudFiles[activeFolder] || [];
  } else {
    Object.keys(cloudFiles).forEach(function(k) {
      allFiles = allFiles.concat(cloudFiles[k] || []);
    });
  }

  var filteredFiles = allFiles.filter(function(f) {
    if (!searchQuery) return true;
    return f.name.toLowerCase().indexOf(searchQuery.toLowerCase()) !== -1;
  });

  return (
    <div style={{ border: '1px solid var(--gray-200)', borderRadius: 8, overflow: 'hidden' }}>
      <div style={{ padding: '8px 12px', background: 'var(--gray-50)', borderBottom: '1px solid var(--gray-200)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--gray-700)' }}>{label}</span>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--gray-500)', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={asDocument}
            onChange={function(e) { setAsDocument(e.target.checked); }}
            style={{ width: 14, height: 14, accentColor: 'var(--primary)' }}
          />
          إرسال كملف
        </label>
      </div>
      <div style={{ padding: 12 }}>
        {existingFiles.length > 0 && (
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 11, color: 'var(--gray-400)', marginBottom: 6 }}>الملفات الحالية:</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {existingFiles.map(function(file, originalIdx) {
                if (removedExisting.indexOf(originalIdx) !== -1) return null;
                return (
                  <div key={'existing-' + originalIdx} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '6px 10px', background: 'rgba(46,125,50,0.04)',
                    border: '1px solid rgba(46,125,50,0.15)', borderRadius: 6, fontSize: 12,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
                      {/\.(jpg|jpeg|png|gif|webp)$/i.test(file.thumbnail || file.url || '') ? (
                        <img src={file.thumbnail || file.url} alt="" style={{ width: 40, height: 40, objectFit: 'cover', borderRadius: 4, flexShrink: 0 }} />
                      ) : (
                        <span style={{ color: 'var(--primary)', flexShrink: 0 }}>📄</span>
                      )}
                      <div style={{ overflow: 'hidden' }}>
                        <span style={{ color: 'var(--gray-700)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'block' }}>{file.name}</span>
                      </div>
                      <span style={{ fontSize: 10, color: 'var(--primary)', background: 'rgba(46,125,50,0.1)', padding: '1px 6px', borderRadius: 4, flexShrink: 0 }}>حالي</span>
                    </div>
                    {onRemoveExisting && (
                      <button
                        type="button"
                        onClick={function() {
                          var newRemoved = removedExisting.concat([originalIdx]);
                          setRemovedExisting(newRemoved);
                          if (onRemoveExisting) onRemoveExisting(newRemoved);
                        }}
                        style={{ background: 'none', border: 'none', color: 'var(--danger, #dc3545)', cursor: 'pointer', fontSize: 14, padding: '0 4px', flexShrink: 0 }}
                      >✕</button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
        <div style={{ display: 'flex', gap: 8 }}>
          <label style={{
            flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
            padding: '14px', border: '2px dashed var(--gray-300)', borderRadius: 8,
            cursor: 'pointer', transition: 'all 0.2s', background: 'var(--gray-50)',
          }}>
            <span style={{ fontSize: 20, color: 'var(--gray-400)' }}>📎</span>
            <span style={{ fontSize: 12, color: 'var(--gray-500)' }}>اختيار ملفات جديدة</span>
            <input type="file" multiple onChange={handleFileChange} style={{ display: 'none' }} />
          </label>
          <button
            type="button"
            onClick={function() { setShowBrowser(true); }}
            style={{
              flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
              padding: '14px', border: '2px dashed var(--primary)', borderRadius: 8,
              cursor: 'pointer', transition: 'all 0.2s', background: 'rgba(46,125,50,0.04)',
            }}
          >
            <span style={{ fontSize: 20, color: 'var(--primary)' }}>☁️</span>
            <span style={{ fontSize: 12, color: 'var(--primary)' }}>اختيار من السحابة</span>
          </button>
        </div>
        {files.length > 0 && (
          <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ fontSize: 11, color: 'var(--gray-400)' }}>ملفات جديدة:</div>
            {files.map(function(file, i) {
              return (
                <div key={'new-' + i} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '6px 10px', background: 'var(--gray-50)', borderRadius: 6, fontSize: 12,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
                    {file._isCloud ? (
                      <span style={{ color: 'var(--primary)', flexShrink: 0 }}>☁️</span>
                    ) : file.type && file.type.startsWith('image/') ? (
                      <img src={URL.createObjectURL(file)} alt="" style={{ width: 40, height: 40, objectFit: 'cover', borderRadius: 4, flexShrink: 0 }} />
                    ) : (
                      <span style={{ color: 'var(--primary)', flexShrink: 0 }}>📄</span>
                    )}
                    <span style={{ color: 'var(--gray-700)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</span>
                  </div>
                  <button
                    type="button"
                    onClick={function() { removeFile(i); }}
                    style={{ background: 'none', border: 'none', color: 'var(--danger, #dc3545)', cursor: 'pointer', fontSize: 14, padding: '0 4px', flexShrink: 0 }}
                  >✕</button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {showBrowser && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
        }} onClick={function() { setShowBrowser(false); }}>
          <div style={{
            background: 'var(--white)', borderRadius: 12, width: '90%', maxWidth: 700,
            maxHeight: '80vh', display: 'flex', flexDirection: 'column', overflow: 'hidden',
            boxShadow: 'var(--shadow-lg)',
          }} onClick={function(e) { e.stopPropagation(); }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--gray-200)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, fontSize: 16 }}>تصفح الملفات المرفوعة</h3>
              <button onClick={function() { setShowBrowser(false); }} style={{ background: 'none', border: 'none', fontSize: 18, cursor: 'pointer', color: 'var(--gray-500)' }}>✕</button>
            </div>
            <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--gray-200)', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button
                onClick={function() { setActiveFolder(null); }}
                style={{ padding: '6px 14px', borderRadius: 20, border: '1px solid var(--gray-200)', background: !activeFolder ? 'var(--primary)' : 'var(--gray-50)', color: !activeFolder ? 'white' : 'var(--gray-600)', fontSize: 12, cursor: 'pointer' }}
              >الكل</button>
              {Object.keys(FOLDER_MAP).map(function(key) {
                return (
                  <button
                    key={key}
                    onClick={function() { setActiveFolder(key); }}
                    style={{ padding: '6px 14px', borderRadius: 20, border: '1px solid var(--gray-200)', background: activeFolder === key ? 'var(--primary)' : 'var(--gray-50)', color: activeFolder === key ? 'white' : 'var(--gray-600)', fontSize: 12, cursor: 'pointer' }}
                  >{FOLDER_MAP[key]}</button>
                );
              })}
            </div>
            <div style={{ padding: '12px 20px' }}>
              <input
                type="text"
                placeholder="بحث في الملفات..."
                value={searchQuery}
                onChange={function(e) { setSearchQuery(e.target.value); }}
                style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--gray-200)', borderRadius: 8, fontSize: 13, outline: 'none' }}
              />
            </div>
            <div style={{ flex: 1, overflow: 'auto', padding: '0 20px 20px' }}>
              {loadingCloud ? (
                <div style={{ textAlign: 'center', padding: 40, color: 'var(--gray-400)' }}>جاري التحميل...</div>
              ) : filteredFiles.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 40, color: 'var(--gray-400)' }}>لا توجد ملفات</div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 10 }}>
                  {filteredFiles.map(function(file) {
                    var isImage = /\.(jpg|jpeg|png|gif|webp)$/i.test(file.name);
                    var isSelected = existingFiles.some(function(f) { return f.url === file.url; }) || files.some(function(f) { return f._cloudUrl === file.url; });
                    return (
                      <div
                        key={file.key}
                        onClick={function() { if (!isSelected) handleSelectCloudFile(file); }}
                        style={{ border: '1px solid var(--gray-200)', borderRadius: 8, overflow: 'hidden', cursor: isSelected ? 'default' : 'pointer', opacity: isSelected ? 0.5 : 1, transition: 'all 0.2s', position: 'relative' }}
                      >
                        {isImage ? (
                          <img src={file.url} alt={file.name} style={{ width: '100%', height: 120, objectFit: 'cover' }} />
                        ) : (
                          <div style={{ width: '100%', height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--gray-50)' }}>
                            <span style={{ fontSize: 32 }}>📄</span>
                          </div>
                        )}
                        <div style={{ padding: '8px 10px' }}>
                          <div style={{ fontSize: 11, color: 'var(--gray-700)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</div>
                          <div style={{ fontSize: 10, color: 'var(--gray-400)', marginTop: 2 }}>{(file.size / 1024).toFixed(0)} KB</div>
                        </div>
                        <button
                          onClick={function(e) { handleDeleteCloudFile(file.key, e); }}
                          style={{ position: 'absolute', top: 6, left: 6, width: 24, height: 24, borderRadius: '50%', background: 'rgba(220,53,69,0.9)', color: 'white', border: 'none', cursor: 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                        >✕</button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
