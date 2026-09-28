import React, { useState, useEffect } from 'react';
import { Navbar } from './components/common/Navbar';
import { BottomNav } from './components/common/BottomNav';
import { HomePage } from './pages/HomePage';
import { MarineMapPage } from './pages/MarineMapPage';
import { AlertsPage } from './pages/AlertsPage';
import { HistoryPage } from './pages/HistoryPage';
import { ProfilePage } from './pages/ProfilePage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { ChatInterface } from './components/chat/ChatInterface';
import { useAppState } from './hooks/useAppState';
import { appStore } from './stores/appState';
import { authService } from './services/auth/authService';
import { useSocketEvents } from './hooks/useSocketEvents';

export const App: React.FC = () => {
  const { activeConversationId, isAuthenticated } = useAppState();
  const [activeTab, setActiveTab] = useState<string>('home');

  // Activate real-time socket events for multi-agent reasoning
  useSocketEvents(activeConversationId);

  // Restore authenticated session on mount if token exists
  useEffect(() => {
    authService.getMe().then((user) => {
      if (user) {
        appStore.setUser(user, localStorage.getItem('orca_jwt_token'));
      }
    });

    const handleUnauthorized = () => {
      appStore.setUser(null, null);
    };
    window.addEventListener('orca:auth:unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('orca:auth:unauthorized', handleUnauthorized);
    };
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: 'var(--bg-abyss)' }}>
      {/* Top Navigation */}
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Content Area */}
      <main style={{ flex: 1, paddingBottom: 'var(--bottom-nav-height)' }} className="main-content">
        {activeTab === 'home' && <HomePage onNavigateTab={setActiveTab} />}
        {activeTab === 'chat' && (
          <div style={{ height: 'calc(100vh - var(--nav-height) - var(--bottom-nav-height))' }}>
            <ChatInterface onSyncMapToCoords={(lat, lon) => {
              appStore.setMapSelectedLocation({ latitude: lat, longitude: lon });
            }} />
          </div>
        )}
        {activeTab === 'map' && (
          <MarineMapPage onAskAboutLocation={(lat, lon) => {
            setActiveTab('chat');
          }} />
        )}
        {activeTab === 'alerts' && <AlertsPage />}
        {activeTab === 'history' && (
          <HistoryPage
            onOpenConversation={(id) => {
              appStore.setActiveConversationId(id);
              setActiveTab('chat');
            }}
            onNewChat={() => {
              appStore.setActiveConversationId(null);
              setActiveTab('chat');
            }}
          />
        )}
        {activeTab === 'profile' && (
          <ProfilePage
            onLogoutSuccess={() => setActiveTab('home')}
            onNavigateLogin={() => setActiveTab('login')}
          />
        )}
        {activeTab === 'login' && (
          <LoginPage
            onSuccess={() => setActiveTab('home')}
            onNavigateRegister={() => setActiveTab('register')}
          />
        )}
        {activeTab === 'register' && (
          <RegisterPage
            onSuccess={() => setActiveTab('home')}
            onNavigateLogin={() => setActiveTab('login')}
          />
        )}
      </main>

      {/* Mobile Bottom Navigation */}
      <BottomNav activeTab={activeTab} setActiveTab={setActiveTab} />

      <style>{`
        @media (min-width: 768px) {
          .main-content {
            padding-bottom: 0 !important;
          }
        }
      `}</style>
    </div>
  );
};

export default App;
