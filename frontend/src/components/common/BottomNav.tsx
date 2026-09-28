import React from 'react';
import { Home, MessageSquare, Map as MapIcon, AlertTriangle, History, User as UserIcon } from 'lucide-react';
import { useAppState } from '../../hooks/useAppState';
import { getTranslation } from '../../i18n/translations';

interface BottomNavProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const BottomNav: React.FC<BottomNavProps> = ({ activeTab, setActiveTab }) => {
  const { language } = useAppState();
  const t = (key: string) => getTranslation(language, key);

  const navItems = [
    { id: 'home', label: t('navHome'), icon: Home },
    { id: 'chat', label: t('navChat'), icon: MessageSquare },
    { id: 'map', label: t('navMap'), icon: MapIcon },
    { id: 'alerts', label: t('navAlerts'), icon: AlertTriangle },
    { id: 'history', label: t('navHistory'), icon: History },
    { id: 'profile', label: t('navProfile'), icon: UserIcon },
  ];

  return (
    <nav
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: 'var(--bottom-nav-height)',
        backgroundColor: 'rgba(10, 22, 38, 0.95)',
        backdropFilter: 'blur(16px)',
        borderTop: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-around',
        zIndex: 1000,
        padding: '0 4px',
      }}
      className="mobile-bottom-nav"
    >
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = activeTab === item.id;
        return (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'transparent',
              border: 'none',
              padding: '6px 4px',
              color: isActive ? 'var(--cyan-hover)' : 'var(--text-dim)',
              transition: 'all 0.15s ease',
              width: '16.6%',
            }}
          >
            <div
              style={{
                padding: '4px 10px',
                borderRadius: '12px',
                backgroundColor: isActive ? 'rgba(6, 182, 212, 0.18)' : 'transparent',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '2px',
              }}
            >
              <Icon size={19} color={isActive ? 'var(--cyan-primary)' : 'currentColor'} />
            </div>
            <span
              style={{
                fontSize: '0.65rem',
                fontWeight: isActive ? 600 : 500,
                letterSpacing: '-0.01em',
              }}
            >
              {item.label}
            </span>
          </button>
        );
      })}

      <style>{`
        @media (min-width: 768px) {
          .mobile-bottom-nav {
            display: none !important;
          }
        }
      `}</style>
    </nav>
  );
};
