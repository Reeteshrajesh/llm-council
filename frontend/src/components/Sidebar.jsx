import { useState } from 'react';
import './Sidebar.css';

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onUpdateTitle,
}) {
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [menuOpenId, setMenuOpenId] = useState(null);

  const handleStartEdit = (e, conv) => {
    e.stopPropagation();
    setMenuOpenId(null);
    setEditingId(conv.id);
    setEditTitle(conv.title || 'New Conversation');
  };

  const handleSaveEdit = async (conversationId) => {
    if (editTitle.trim()) {
      await onUpdateTitle(conversationId, editTitle.trim());
    }
    setEditingId(null);
  };

  const handleKeyPress = (e, conversationId) => {
    if (e.key === 'Enter') {
      handleSaveEdit(conversationId);
    } else if (e.key === 'Escape') {
      setEditingId(null);
    }
  };

  const handleDelete = async (e, conversationId) => {
    e.stopPropagation();
    setMenuOpenId(null);
    if (window.confirm('Are you sure you want to delete this conversation?')) {
      await onDeleteConversation(conversationId);
    }
  };

  const toggleMenu = (e, conversationId) => {
    e.stopPropagation();
    setMenuOpenId(menuOpenId === conversationId ? null : conversationId);
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>LLM Council</h1>
        <button className="new-conversation-btn" onClick={onNewConversation}>
          + New Conversation
        </button>
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="no-conversations">No conversations yet</div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${
                conv.id === currentConversationId ? 'active' : ''
              }`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className="conversation-content">
                {editingId === conv.id ? (
                  <input
                    className="edit-title-input"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onBlur={() => handleSaveEdit(conv.id)}
                    onKeyDown={(e) => handleKeyPress(e, conv.id)}
                    onClick={(e) => e.stopPropagation()}
                    autoFocus
                  />
                ) : (
                  <div className="conversation-title">
                    {conv.title || 'New Conversation'}
                  </div>
                )}
                <div className="conversation-meta">
                  {conv.message_count} messages
                </div>
              </div>

              <div className="conversation-actions">
                <button
                  className="menu-btn"
                  onClick={(e) => toggleMenu(e, conv.id)}
                  title="Options"
                >
                  ⋮
                </button>
                {menuOpenId === conv.id && (
                  <div className="menu-dropdown">
                    <button
                      className="menu-item"
                      onClick={(e) => handleStartEdit(e, conv)}
                    >
                      ✏️ Edit title
                    </button>
                    <button
                      className="menu-item delete"
                      onClick={(e) => handleDelete(e, conv.id)}
                    >
                      🗑️ Delete
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
