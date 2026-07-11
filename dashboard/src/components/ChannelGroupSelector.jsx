import { useState, useEffect } from 'react';
import api from '../services/api';

export default function ChannelGroupSelector({ selected = [], onChange, label = 'اختر القنوات والجروبات' }) {
  const [channelGroups, setChannelGroups] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadChannelGroups();
  }, []);

  const loadChannelGroups = async () => {
    try {
      const data = await api.get('/channels/active');
      setChannelGroups(data);
    } catch (err) {
      console.error('Failed to load channels/groups:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleItem = (chatId) => {
    const newSelected = selected.includes(chatId)
      ? selected.filter(id => id !== chatId)
      : [...selected, chatId];
    onChange(newSelected);
  };

  if (loading) {
    return <div style={{ padding: '10px 0', fontSize: 13, color: 'var(--gray-400)', textAlign: 'center' }}>جاري التحميل...</div>;
  }

  if (channelGroups.length === 0) {
    return (
      <div style={{ padding: '10px 0', fontSize: 13, color: 'var(--gray-400)', textAlign: 'center' }}>
        لا توجد قنوات أو جروبات مسجلة
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--gray-700)' }}>{label}</span>
        <div style={{ display: 'flex', gap: 10 }}>
          <button type="button" onClick={() => onChange(channelGroups.map(g => g.chatId))} style={{ background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', fontSize: 12 }}>تحديد الكل</button>
          <button type="button" onClick={() => onChange([])} style={{ background: 'none', border: 'none', color: 'var(--gray-400)', cursor: 'pointer', fontSize: 12 }}>إلغاء</button>
        </div>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {channelGroups.map(group => {
          const isActive = selected.includes(group.chatId);
          return (
            <span
              key={group.id}
              onClick={() => toggleItem(group.chatId)}
              style={{
                padding: '6px 14px',
                borderRadius: 20,
                fontSize: 13,
                cursor: 'pointer',
                background: isActive ? 'var(--primary)' : 'var(--gray-200)',
                color: isActive ? 'white' : 'var(--gray-700)',
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                userSelect: 'none',
              }}
            >
              <span style={{ fontSize: 14 }}>{group.type === 'channel' ? '📢' : '👥'}</span>
              {group.title}
            </span>
          );
        })}
      </div>
      {selected.length > 0 && (
        <div style={{ marginTop: 8, fontSize: 11, color: 'var(--gray-400)', textAlign: 'center' }}>
          {selected.length} من {channelGroups.length} محدد
        </div>
      )}
    </div>
  );
}
