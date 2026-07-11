export default function FileUpload({ files, setFiles, asDocument, setAsDocument, label = 'الملفات المرفقة' }) {
  const handleFileChange = (e) => {
    const selected = Array.from(e.target.files);
    setFiles(prev => [...prev, ...selected]);
  };

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  return (
    <div style={{ border: '1px solid var(--gray-200)', borderRadius: 8, overflow: 'hidden' }}>
      <div style={{ padding: '8px 12px', background: 'var(--gray-50)', borderBottom: '1px solid var(--gray-200)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--gray-700)' }}>{label}</span>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--gray-500)', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={asDocument}
            onChange={(e) => setAsDocument(e.target.checked)}
            style={{ width: 14, height: 14, accentColor: 'var(--primary)' }}
          />
          إرسال كملف
        </label>
      </div>
      <div style={{ padding: 12 }}>
        <label style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 6,
          padding: '16px',
          border: '2px dashed var(--gray-300)',
          borderRadius: 8,
          cursor: 'pointer',
          transition: 'all 0.2s',
          background: 'var(--gray-50)',
        }}>
          <span style={{ fontSize: 24, color: 'var(--gray-400)' }}>📎</span>
          <span style={{ fontSize: 13, color: 'var(--gray-500)' }}>اضغط لاختيار ملفات</span>
          <span style={{ fontSize: 11, color: 'var(--gray-400)' }}>يدعم صور وفيديو وملفات</span>
          <input
            type="file"
            multiple
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
        </label>
        {files.length > 0 && (
          <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {files.map((file, i) => (
              <div key={i} style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 10px',
                background: 'var(--gray-50)',
                borderRadius: 6,
                fontSize: 12,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
                  <span style={{ color: 'var(--primary)', flexShrink: 0 }}>📄</span>
                  <span style={{ color: 'var(--gray-700)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</span>
                  <span style={{ color: 'var(--gray-400)', flexShrink: 0 }}>({(file.size / 1024).toFixed(0)} KB)</span>
                </div>
                <button
                  type="button"
                  onClick={() => removeFile(i)}
                  style={{ background: 'none', border: 'none', color: 'var(--danger, #dc3545)', cursor: 'pointer', fontSize: 14, padding: '0 4px', flexShrink: 0 }}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
