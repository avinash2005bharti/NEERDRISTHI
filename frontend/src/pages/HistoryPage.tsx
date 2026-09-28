import React, { useEffect, useState } from 'react';
import {
  History,
  MessageSquare,
  Trash2,
  ExternalLink,
  Plus,
  RefreshCw,
  Clock,
  Compass,
} from 'lucide-react';
import { chatService } from '../services/chat/chatService';
import { Conversation } from '../types';
import { appStore } from '../stores/appState';
import { useAppState } from '../hooks/useAppState';
import { getTranslation } from '../i18n/translations';

interface HistoryPageProps {
  onOpenConversation: (conversationId: string) => void;
  onNewChat: () => void;
}

export const HistoryPage: React.FC<HistoryPageProps> = ({
  onOpenConversation,
  onNewChat,
}) => {
  const { language } = useAppState();
  const t = (key: string) => getTranslation(language, key);

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const data = await chatService.listConversations();
      setConversations(data);
    } catch (err) {
      console.warn('Could not retrieve conversation history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this conversation audit history?')) {
      return;
    }
    try {
      await chatService.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.conversationId !== id));
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  return (
    <div
      style={{
        maxWidth: '800px',
        margin: '0 auto',
        padding: '1.5rem',
        minHeight: 'calc(100vh - var(--nav-height))',
      }}
      className="animate-fade-in"
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '1.5rem',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              backgroundColor: 'rgba(6, 182, 212, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <History size={20} color="var(--cyan-primary)" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.4rem', color: '#ffffff' }}>
              {t('navHistory')}
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
              Persisted multi-agent reasoning sessions and audit records.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={fetchHistory}
            className="btn-secondary"
            style={{ padding: '8px 12px', fontSize: '0.8rem' }}
          >
            <RefreshCw size={14} className={loading ? 'spin-slow' : ''} />
          </button>
          <button
            onClick={onNewChat}
            className="btn-primary"
            style={{ padding: '8px 14px', fontSize: '0.8rem' }}
          >
            <Plus size={16} />
            <span>{t('newChat')}</span>
          </button>
        </div>
      </div>

      {/* History List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-muted)' }}>
          <RefreshCw size={24} className="spin-slow" style={{ margin: '0 auto 12px' }} />
          <div>Retrieving conversation sessions from MongoDB...</div>
        </div>
      ) : conversations.length === 0 ? (
        <div
          className="glass-panel"
          style={{
            textAlign: 'center',
            padding: '3rem 1.5rem',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div
            style={{
              width: '52px',
              height: '52px',
              borderRadius: '13px',
              overflow: 'hidden',
              margin: '0 auto 1rem',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              backgroundColor: '#0a1d37',
              boxShadow: '0 0 16px rgba(6, 182, 212, 0.25)',
            }}
          >
            <img
              src="/neerdristi.logo.png"
              alt="NEERDRISTI"
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          </div>
          <h3 style={{ color: '#ffffff', fontSize: '1rem', marginBottom: '0.5rem' }}>
            No Previous Sessions Found
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
            Start a conversational inquiry with NEERDRISTI to record spatial and weather advisories.
          </p>
          <button onClick={onNewChat} className="btn-primary">
            <Plus size={16} />
            <span>Start First Query</span>
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {conversations.map((conv) => (
            <div
              key={conv.conversationId}
              onClick={() => onOpenConversation(conv.conversationId)}
              className="glass-panel"
              style={{
                padding: '14px 18px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--cyan-primary)';
                e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-subtle)';
                e.currentTarget.style.backgroundColor = 'var(--bg-card)';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <MessageSquare size={18} color="var(--cyan-primary)" />
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#ffffff' }}>
                    {conv.title || `Session ${conv.conversationId.slice(0, 8)}`}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Clock size={11} />
                    <span>Last active: {conv.lastQueryAt ? new Date(conv.lastQueryAt).toLocaleString() : 'Recent'}</span>
                  </div>
                </div>
              </div>

              <button
                onClick={(e) => handleDelete(conv.conversationId, e)}
                title="Delete session"
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-dim)',
                  padding: '6px',
                  borderRadius: '6px',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--status-nogo)')}
                onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-dim)')}
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
