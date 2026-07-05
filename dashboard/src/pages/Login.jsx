import React, { useState } from 'react';
import api from '../services/api';

export default function Login({ onLogin }) {
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await api.login(form);
      localStorage.setItem('token', data.token);
      localStorage.setItem('isLoggedIn', 'true');
      onLogin();
    } catch {
      setError('اسم المستخدم أو كلمة المرور غير صحيحة');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 50%, #A5D6A7 100%)',
      fontFamily: "'Tajawal', sans-serif",
      direction: 'rtl'
    }}>
      <div style={{
        width: '100%',
        maxWidth: 420,
        margin: 20,
        background: '#fff',
        borderRadius: 16,
        border: '1px solid #E0E0E0',
        boxShadow: '0 10px 40px rgba(0,0,0,0.1)',
        padding: 48,
        position: 'relative',
        zIndex: 1
      }}>
        {/* الشعار */}
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{
            width: 80,
            height: 80,
            borderRadius: 20,
            background: 'linear-gradient(135deg, #2E7D32 0%, #4CAF50 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 20px',
            boxShadow: '0 10px 30px rgba(46,125,50,0.3)'
          }}>
            <span style={{ fontSize: 40 }}>🤖</span>
          </div>
          <h2 style={{
            color: '#1B5E20',
            margin: 0,
            fontSize: 28,
            fontWeight: 700
          }}>KKU Bot</h2>
          <p style={{
            color: '#666',
            margin: '8px 0 0',
            fontSize: 14
          }}>لوحة التحكم</p>
        </div>

        {/* النموذج */}
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 20 }}>
            <label style={{
              display: 'block',
              color: '#333',
              fontSize: 13,
              marginBottom: 8,
              fontWeight: 500
            }}>اسم المستخدم</label>
            <input
              type="text"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              placeholder="admin"
              required
              style={{
                width: '100%',
                padding: '14px 16px',
                background: '#F5F5F5',
                border: '1px solid #E0E0E0',
                borderRadius: 12,
                color: '#333',
                fontSize: 15,
                outline: 'none',
                transition: 'all 0.3s',
                boxSizing: 'border-box',
                fontFamily: "'Tajawal', sans-serif"
              }}
              onFocus={(e) => {
                e.target.style.borderColor = '#4CAF50';
                e.target.style.background = '#fff';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = '#E0E0E0';
                e.target.style.background = '#F5F5F5';
              }}
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label style={{
              display: 'block',
              color: '#333',
              fontSize: 13,
              marginBottom: 8,
              fontWeight: 500
            }}>كلمة المرور</label>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="••••••••"
              required
              style={{
                width: '100%',
                padding: '14px 16px',
                background: '#F5F5F5',
                border: '1px solid #E0E0E0',
                borderRadius: 12,
                color: '#333',
                fontSize: 15,
                outline: 'none',
                transition: 'all 0.3s',
                boxSizing: 'border-box',
                fontFamily: "'Tajawal', sans-serif"
              }}
              onFocus={(e) => {
                e.target.style.borderColor = '#4CAF50';
                e.target.style.background = '#fff';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = '#E0E0E0';
                e.target.style.background = '#F5F5F5';
              }}
            />
          </div>

          {error && (
            <div style={{
              background: '#FFEBEE',
              border: '1px solid #FFCDD2',
              borderRadius: 10,
              padding: '12px 16px',
              marginBottom: 20,
              display: 'flex',
              alignItems: 'center',
              gap: 8
            }}>
              <span style={{ fontSize: 18 }}>⚠️</span>
              <span style={{ color: '#D32F2F', fontSize: 14 }}>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '14px 24px',
              background: loading ? '#A5D6A7' : 'linear-gradient(135deg, #2E7D32 0%, #4CAF50 100%)',
              border: 'none',
              borderRadius: 12,
              color: '#fff',
              fontSize: 16,
              fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'all 0.3s',
              boxShadow: loading ? 'none' : '0 4px 15px rgba(46,125,50,0.3)',
              marginTop: 8,
              fontFamily: "'Tajawal', sans-serif"
            }}
          >
            {loading ? 'جاري تسجيل الدخول...' : 'تسجيل الدخول'}
          </button>
        </form>

        {/* Footer */}
        <div style={{
          textAlign: 'center',
          marginTop: 32,
          paddingTop: 24,
          borderTop: '1px solid #E0E0E0'
        }}>
          <p style={{
            color: '#999',
            fontSize: 12,
            margin: 0
          }}>KKU Bot Dashboard v2.0</p>
        </div>
      </div>
    </div>
  );
}
