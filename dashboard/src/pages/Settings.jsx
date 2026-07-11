import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useToast } from '../components/ToastContext';

export default function Settings({ onLogout }) {
  const { showToast } = useToast();
  const [settings, setSettings] = useState({
    welcomeMessage: "مرحباً بك!",
    autoGreeting: "true",
    antiSpam: "true",
    antiFlood: "true",
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
      welcomeMessage: "مرحباً بك!",
      autoGreeting: "true",
      antiSpam: "true",
      antiFlood: "true",
      floodLimit: 5,
      floodTime: 10,
      botLanguage: 'ar',
    });
    showToast('تمت إعادة التعيين', 'success');
  };

  return (
    <>
      <div className="settings-page">
        <div className="settings-header">
          <div>
            <h2 style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>الإعدادات العامة</h2>
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

        <div className="settings-grid">
          <div className="setting-group">
            <h4>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              إعدادات الحماية
            </h4>
            <div className="setting-row">
              <div>
                <div className="label">رسالة الترحيب</div>
                <div className="desc">إرسال رسالة ترحيب للأعضاء الجدد</div>
              </div>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={settings.autoGreeting !== "false"}
                  onChange={(e) => setSettings({ ...settings, autoGreeting: e.target.checked ? "true" : "false" })}
                />
                <span className="toggle-slider" />
              </label>
            </div>
            <div className="setting-row">
              <div>
                <div className="label">مكافحة السبام</div>
                <div className="desc">منع المستخدمين من إرسال رسائل متكررة</div>
              </div>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={settings.antiSpam !== "false"}
                  onChange={(e) => setSettings({ ...settings, antiSpam: e.target.checked ? "true" : "false" })}
                />
                <span className="toggle-slider" />
              </label>
            </div>
            <div className="setting-row">
              <div>
                <div className="label">مكافحة الفيضان</div>
                <div className="desc">حد أقصى للرسائل في فترة زمنية</div>
              </div>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={settings.antiFlood !== "false"}
                  onChange={(e) => setSettings({ ...settings, antiFlood: e.target.checked ? "true" : "false" })}
                />
                <span className="toggle-slider" />
              </label>
            </div>
            <div className="setting-row">
              <div>
                <div className="label">البحث بالذكاء الاصطناعي (AI)</div>
                <div className="desc">تفعيل الرد بالذكاء الاصطناعي عندما لا توجد إجابة مطابقة</div>
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

          <div className="setting-group">
            <h4>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
              إعدادات الفيضان
            </h4>
            <div className="form-group">
              <label>الحد الأقصى للرسائل</label>
              <input
                type="number"
                className="form-input"
                value={settings.floodLimit}
                onChange={(e) => setSettings({ ...settings, floodLimit: parseInt(e.target.value) || 0 })}
                min="1"
                max="20"
              />
            </div>
            <div className="form-group">
              <label>الفترة الزمنية (ثانية)</label>
              <input
                type="number"
                className="form-input"
                value={settings.floodTime}
                onChange={(e) => setSettings({ ...settings, floodTime: parseInt(e.target.value) || 0 })}
                min="1"
                max="60"
              />
            </div>
            <div style={{ padding: '12px 16px', background: '#FFF3E0', borderRadius: 8, fontSize: 13, color: '#E65100', marginTop: 8 }}>
              <strong>ملاحظة:</strong> سيتم حظر المستخدم تلقائياً عند تجاوز الحد المحدد.
            </div>
          </div>
        </div>

        <div style={{ marginTop: 24, display: 'flex', gap: 12 }}>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
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
    </>
  );
}
