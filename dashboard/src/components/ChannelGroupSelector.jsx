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
    return <div className="channel-group-selector loading">جاري تحميل القنوات والجروبات...</div>;
  }

  if (channelGroups.length === 0) {
    return (
      <div className="channel-group-selector empty">
        <p>لا توجد قنوات أو جروبات مسجلة</p>
        <p className="hint">قم بتسجيل القنوات والجروبات من صفحة إدارة القنوات أولاً</p>
      </div>
    );
  }

  return (
    <div className="channel-group-selector">
      <div className="selector-header">
        <label>{label}</label>
        <div className="selector-actions">
          <button type="button" onClick={() => onChange(channelGroups.map(g => g.chatId))} className="btn-link">تحديد الكل</button>
          <button type="button" onClick={() => onChange([])} className="btn-link">إلغاء التحديد</button>
        </div>
      </div>
      <div className="selector-list">
        {channelGroups.map(group => (
          <label key={group.id} className={`selector-item ${selected.includes(group.chatId) ? 'selected' : ''}`}>
            <input
              type="checkbox"
              checked={selected.includes(group.chatId)}
              onChange={() => toggleItem(group.chatId)}
            />
            <span className={`type-badge ${group.type}`}>
              {group.type === 'channel' ? '📢' : '👥'}
            </span>
            <span className="item-info">
              <span className="item-title">{group.title}</span>
              <span className="item-meta">{group.memberCount || 0} عضو</span>
            </span>
          </label>
        ))}
      </div>
      {selected.length > 0 && (
        <div className="selector-summary">
          تم تحديد {selected.length} من {channelGroups.length}
        </div>
      )}
    </div>
  );
}
