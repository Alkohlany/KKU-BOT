import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useToast } from '../components/ToastContext';

export default function Settings() {
  const { showToast } = useToast();
  const [settings, setSettings] = useState({
    adminIds: '',
    welcomeMessage: true,
    antiSpam: true,
    antiFlood: true,
    floodLimit: 5,
    floodTime: 10,
    botLanguage: 'ar',
  });

  const [saving, setSaving] = useState(false);
  const [botStatus, setBotStatus] = useState('checking');

  useEffect(() => {
    loadSettings();
    checkBotStatus();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await api.getSettings();
      setSettings(data);
    } catch {
      console.error('Failed to load settings');
    }
  };

  const checkBotStatus = async () => {
    try {
      const response = await fetch(`${window.location.origin}/health`);
      if (response.ok) {
        setBotStatus('online');
      } else {
        setBotStatus('offline');
      }
    } catch {
      setBotStatus('offline');
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.updateSettings(settings);
      showToast('تم حفظ الإعدادات بنجاح!', 'success');
    } catch {
      console.error('Failed to save settings');
      showToast('فشل حفظ الإعدادات', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setSettings({
      adminIds: '',
      welcomeMessage: true,
      antiSpam: true,
      antiFlood: true,
      floodLimit: 5,
      floodTime: 10,
      botLanguage: 'ar',
    });
    showToast('تمت إعادة التعيين', 'success');
  };

  return (
    <div className="settings-page" style={{ maxWidth: 800, margin: '0 auto', padding: '0 16px' }}>
      <div className="settings-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32, paddingBottom: 16, borderBottom: '1px solid #e2e8f0' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: '#1e293b' }}>الإعدادات العامة</h2>
          <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: 14 }}>تخصيص إعدادات البوت والحماية</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            width: 10,
            height: 10,
            borderRadius: '50%',
            background: botStatus === 'online' ? '#22c55e' : botStatus === 'offline' ? '#ef4444' : '#f59e0b',
            display: 'inline-block',
          }} />
          <span style={{ fontSize: 13, color: '#64748b' }}>
            {botStatus === 'online' ? 'البوت متصل' : botStatus === 'offline' ? 'البوت غير متصل' : 'جاري التحقق...'}
          </span>
        </div>
      </div>

      <div style={{ display: 'grid', gap: 24 }}>
        {/* Section 1: Admin Management */}
        <div style={{ background: '#fff', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.08)', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 36, height: 36, borderRadius: 8, background: '#eff6ff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </div>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: '#1e293b' }}>إدارة المسؤولين</h3>
          </div>
          <div style={{ padding: 20, display: 'grid', gap: 16 }}>
            <div className="form-group">
              <label style={{ display: 'block', marginBottom: 6, fontSize: 14, fontWeight: 500, color: '#374151' }}>معرّفات المسؤولين (مفصولة بفواصل)</label>
              <input
                className="form-input"
                style={{ width: '100%', padding: '10px 14px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, boxSizing: 'border-box' }}
                value={settings.adminIds}
                onChange={(e) => setSettings({ ...settings, adminIds: e.target.value })}
                placeholder="123456789,987654321"
              />
            </div>
            <div className="form-group">
              <label style={{ display: 'block', marginBottom: 6, fontSize: 14, fontWeight: 500, color: '#374151' }}>اللغة الافتراضية</label>
              <select
                className="form-input"
                style={{ width: '100%', padding: '10px 14px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, boxSizing: 'border-box', background: '#fff' }}
                value={settings.botLanguage}
                onChange={(e) => setSettings({ ...settings, botLanguage: e.target.value })}
              >
                <option value="ar">العربية</option>
                <option value="en">English</option>
              </select>
            </div>
          </div>
        </div>

        {/* Section 2: Protection Settings */}
        <div style={{ background: '#fff', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.08)', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 36, height: 36, borderRadius: 8, background: '#f0fdf4', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
            </div>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: '#1e293b' }}>إعدادات الحماية</h3>
          </div>
          <div style={{ padding: 20 }}>
            <div className="setting-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #f1f5f9' }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500, color: '#1e293b' }}>مكافحة السبام</div>
                <div style={{ fontSize: 13, color: '#64748b', marginTop: 2 }}>منع المستخدمين من إرسال رسائل متكررة</div>
              </div>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={settings.antiSpam}
                  onChange={(e) => setSettings({ ...settings, antiSpam: e.target.checked })}
                />
                <span className="toggle-slider" />
              </label>
            </div>
            <div className="setting-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #f1f5f9' }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500, color: '#1e293b' }}>مكافحة الفيضان</div>
                <div style={{ fontSize: 13, color: '#64748b', marginTop: 2 }}>حد أقصى للرسائل في فترة زمنية</div>
              </div>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={settings.antiFlood}
                  onChange={(e) => setSettings({ ...settings, antiFlood: e.target.checked })}
                />
                <span className="toggle-slider" />
              </label>
            </div>
            <div className="setting-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0' }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500, color: '#1e293b' }}>البحث بالذكاء الاصطناعي (AI)</div>
                <div style={{ fontSize: 13, color: '#64748b', marginTop: 2 }}>تفعيل الرد بالذكاء الاصطناعي عندما لا توجد إجابة مطابقة</div>
              </div>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={settings.ai_fallback_enabled !== "false"}
                  onChange={(e) => setSettings({ ...settings, ai_fallback_enabled: e.target.checked ? "true" : "false" })}
                />
                <span className="toggle-slider" />
              </label>
            </div>
          </div>
        </div>

        {/* Section 3: Flood Settings */}
        <div style={{ background: '#fff', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.08)', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 36, height: 36, borderRadius: 8, background: '#fef3c7', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </div>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: '#1e293b' }}>إعدادات الفيضان</h3>
          </div>
          <div style={{ padding: 20, display: 'grid', gap: 16 }}>
            <div className="form-group">
              <label style={{ display: 'block', marginBottom: 6, fontSize: 14, fontWeight: 500, color: '#374151' }}>الحد الأقصى للرسائل</label>
              <input
                type="number"
                className="form-input"
                style={{ width: '100%', padding: '10px 14px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, boxSizing: 'border-box' }}
                value={settings.floodLimit}
                onChange={(e) => setSettings({ ...settings, floodLimit: parseInt(e.target.value) || 0 })}
                min="1"
                max="20"
              />
            </div>
            <div className="form-group">
              <label style={{ display: 'block', marginBottom: 6, fontSize: 14, fontWeight: 500, color: '#374151' }}>الفترة الزمنية (ثانية)</label>
              <input
                type="number"
                className="form-input"
                style={{ width: '100%', padding: '10px 14px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, boxSizing: 'border-box' }}
                value={settings.floodTime}
                onChange={(e) => setSettings({ ...settings, floodTime: parseInt(e.target.value) || 0 })}
                min="1"
                max="60"
              />
            </div>
            <div style={{ padding: '12px 16px', background: '#FFF3E0', borderRadius: 8, fontSize: 13, color: '#E65100' }}>
              <strong>ملاحظة:</strong> سيتم حظر المستخدم تلقائياً عند تجاوز الحد المحدد.
            </div>
          </div>
        </div>

        {/* Section 4: Bot Messages */}
        <div style={{ background: '#fff', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.08)', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 36, height: 36, borderRadius: 8, background: '#faf5ff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#a855f7" strokeWidth="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: '#1e293b' }}>رسائل البوت</h3>
          </div>
          <div style={{ padding: 20 }}>
            <div className="setting-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500, color: '#1e293b' }}>رسالة الترحيب</div>
                <div style={{ fontSize: 13, color: '#64748b', marginTop: 2 }}>إرسال رسالة ترحيب للأعضاء الجدد</div>
              </div>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={settings.welcomeMessage}
                  onChange={(e) => setSettings({ ...settings, welcomeMessage: e.target.checked })}
                />
                <span className="toggle-slider" />
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div style={{ marginTop: 28, display: 'flex', gap: 12, paddingBottom: 32 }}>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
            <polyline points="17 21 17 13 7 13 7 21" />
            <polyline points="7 3 7 8 15 8" />
          </svg>
          {saving ? 'جاري الحفظ...' : 'حفظ الإعدادات'}
        </button>
        <button className="btn btn-secondary" onClick={handleReset}>إعادة التعيين</button>
      </div>
    </div>
  );
}
