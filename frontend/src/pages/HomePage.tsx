import React, { useState, useEffect } from 'react';
import { ChatInterface } from '../components/chat/ChatInterface';
import { MarineMap } from '../components/map/MarineMap';
import { useAppState } from '../hooks/useAppState';
import { appStore } from '../stores/appState';
import { Map, MessageSquare, Waves } from 'lucide-react';

interface HomePageProps {
  onNavigateTab: (tab: string) => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onNavigateTab }) => {
  const { language, userLocation } = useAppState();

  const [isDesktop, setIsDesktop] = useState<boolean>(() =>
    typeof window !== 'undefined' ? window.innerWidth >= 900 : true
  );

  const [activeView, setActiveView] = useState<'both' | 'chat' | 'map'>(() =>
    typeof window !== 'undefined' && window.innerWidth >= 900 ? 'both' : 'chat'
  );

  useEffect(() => {
    const handleResize = () => {
      const desktop = window.innerWidth >= 900;
      setIsDesktop(desktop);
      if (!desktop && activeView === 'both') {
        setActiveView('chat');
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [activeView]);

  const effectiveView = !isDesktop && activeView === 'both' ? 'chat' : activeView;

  const handleSyncMap = (lat: number, lon: number) => {
    appStore.setMapSelectedLocation({ latitude: lat, longitude: lon });
  };

  const handleAskAboutPoint = (lat: number, lon: number) => {
    setActiveView('chat');
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - var(--nav-height))',
        backgroundColor: 'var(--bg-abyss)',
        overflow: 'hidden',
      }}
    >
      {/* View Switcher Bar */}
      <div
        className="mobile-view-tabs"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          padding: '8px',
          backgroundColor: 'var(--bg-surface)',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <button
          onClick={() => setActiveView('chat')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 14px',
            borderRadius: '6px',
            fontSize: '0.8rem',
            backgroundColor: effectiveView === 'chat' ? 'rgba(6, 182, 212, 0.2)' : 'transparent',
            color: effectiveView === 'chat' ? 'var(--cyan-hover)' : 'var(--text-muted)',
            border: effectiveView === 'chat' ? '1px solid var(--border-active)' : 'none',
          }}
        >
          <MessageSquare size={14} />
          <span>Conversational AI</span>
        </button>

        <button
          onClick={() => setActiveView('map')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 14px',
            borderRadius: '6px',
            fontSize: '0.8rem',
            backgroundColor: effectiveView === 'map' ? 'rgba(6, 182, 212, 0.2)' : 'transparent',
            color: effectiveView === 'map' ? 'var(--cyan-hover)' : 'var(--text-muted)',
            border: effectiveView === 'map' ? '1px solid var(--border-active)' : 'none',
          }}
        >
          <Map size={14} />
          <span>Live Ocean Map</span>
        </button>

        {/* Split HUD View — ONLY displayed on Desktop mode (>= 900px) */}
        {isDesktop && (
          <button
            onClick={() => setActiveView('both')}
            className="desktop-split-btn"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '0.8rem',
              backgroundColor: effectiveView === 'both' ? 'rgba(6, 182, 212, 0.2)' : 'transparent',
              color: effectiveView === 'both' ? 'var(--cyan-hover)' : 'var(--text-muted)',
              border: effectiveView === 'both' ? '1px solid var(--border-active)' : 'none',
            }}
          >
            <Waves size={14} />
            <span>Split HUD View</span>
          </button>
        )}
      </div>

      {/* Main Work Area */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        {/* Left Column: Conversational AI Reasoning Engine */}
        <div
          className={`home-chat-col ${effectiveView === 'map' ? 'hidden-on-mobile' : ''}`}
          style={{
            flex: effectiveView === 'both' ? '0 0 48%' : '1 1 100%',
            height: '100%',
            borderRight: effectiveView === 'both' ? '1px solid var(--border-subtle)' : 'none',
            display: effectiveView === 'map' ? 'none' : 'flex',
            flexDirection: 'column',
          }}
        >
          <ChatInterface onSyncMapToCoords={handleSyncMap} />
        </div>

        {/* Right Column: Interactive Real-Time Marine Map */}
        <div
          className={`home-map-col ${effectiveView === 'chat' ? 'hidden-on-mobile' : ''}`}
          style={{
            flex: effectiveView === 'both' ? '0 0 52%' : '1 1 100%',
            height: '100%',
            display: effectiveView === 'chat' ? 'none' : 'block',
            position: 'relative',
          }}
        >
          <MarineMap onAskAboutLocation={handleAskAboutPoint} />
        </div>
      </div>

      <style>{`
        @media (max-width: 900px) {
          .desktop-split-btn {
            display: none !important;
          }
          .home-chat-col {
            flex: 1 1 100% !important;
            width: 100% !important;
            border-right: none !important;
          }
          .home-map-col {
            flex: 1 1 100% !important;
            width: 100% !important;
          }
        }
      `}</style>
    </div>
  );
};
