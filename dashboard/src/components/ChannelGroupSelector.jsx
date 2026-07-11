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
    return <div className="channel-selector">جاري تحميل القنوات والجروبات...</div>;
  }

  if (channelGroups.length === 0) {
    return (
      <div className="channel-selector">
        <div className="channel-selector-label">
          <span>لا توجد قنوات أو جروبات مسجلة</span>
        </div>
      </div>
    );
  }

  return (
    <div className="channel-selector">
      <div className="channel-selector-label">
        <span>{label}</span>
        <div className="channel-selector-actions">
          <button type="button" onClick={() => onChange(channelGroups.map(g => g.chatId))}>تحديد الكل</button>
          <button type="button" onClick={() => onChange([])}>إلغاء</button>
        </div>
      </div>
      <div className="channel-selector-list">
        {channelGroups.map(group => (
          <label key={group.id} className={`channel-selector-item ${selected.includes(group.chatId) ? 'active' : ''}`}>
            <input
              type="checkbox"
              checked={selected.includes(group.chatId)}
              onChange={() => toggleItem(group.chatId)}
            />
            <span>{group.type === 'channel' ? '📢' : '👥'}</span>
            <span className="channel-selector-name">{group.title}</span>
            {selected.includes(group.chatId) && <span className="channel-selector-check">✓</span>}
          </label>
        ))}
      </div>
      {selected.length > 0 && (
        <div className="channel-selector-footer">
          {selected.length} من {channelGroups.length} محدد
        </div>
      )}
    </div>
  );
}
