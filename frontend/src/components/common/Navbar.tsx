import React, { useState } from 'react';
import {
  Compass,
  MapPin,
  Globe,
  Radio,
  User as UserIcon,
  LogIn,
  AlertTriangle,
  History,
  MessageSquare,
  Home,
  Map as MapIcon,
  ChevronDown,
} from 'lucide-react';
import { useAppState } from '../../hooks/useAppState';
import { appStore } from '../../stores/appState';
import { authService } from '../../services/auth/authService';
import { SUPPORTED_LANGUAGES, getTranslation, LanguageCode } from '../../i18n/translations';
import { useGeolocation } from '../../hooks/useGeolocation';
import { EmergencySosModal } from './EmergencySosModal';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  const { user, isAuthenticated, language, userLocation, isAgentRunning } = useAppState();
  const { requestLocation, loading: locLoading } = useGeolocation();
  const [langMenuOpen, setLangMenuOpen] = useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const [sosModalOpen, setSosModalOpen] = useState(false);

  const t = (key: string) => getTranslation(language, key);

  const handleLogout = async () => {
    await authService.logout();
    appStore.setUser(null, null);
    setProfileMenuOpen(false);
  };

  return (
    <header
      style={{
        height: 'var(--nav-height)',
        backgroundColor: 'var(--bg-card)',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 1.25rem',
        position: 'sticky',
        top: 0,
        zIndex: 1000,
      }}
    >
      {/* Brand & Live Beacon */}
      <div
        style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', cursor: 'pointer' }}
        onClick={() => setActiveTab('home')}
      >
        <div
          style={{
            width: '40px',
            height: '40px',
            borderRadius: '10px',
            overflow: 'hidden',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 16px rgba(6, 182, 212, 0.4)',
            border: '1px solid rgba(56, 189, 248, 0.35)',
            backgroundColor: '#0a1d37',
            flexShrink: 0,
          }}
        >
          <img
            src="/neerdristi.logo.png"
            alt="NEERDRISTI Logo"
            className={isAgentRunning ? 'spin-slow' : ''}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div
            style={{
              height: '42px',
              backgroundColor: 'rgba(255, 255, 255, 0.96)',
              borderRadius: '8px',
              padding: '3px 8px',
              display: 'flex',
              alignItems: 'center',
              boxShadow: '0 2px 10px rgba(0, 0, 0, 0.3)',
              border: '1px solid rgba(255, 255, 255, 0.4)',
            }}
          >
            <img
              src="/neerdristi.banner.png"
              alt="NEERDRISTI Marine Intelligence"
              style={{
                height: '36px',
                width: 'auto',
                objectFit: 'contain',
                display: 'block',
              }}
            />
          </div>
        </div>
      </div>

      {/* Desktop Navigation Links */}
      <nav
        style={{
          display: 'none',
          gap: '0.5rem',
          alignItems: 'center',
        }}
        className="desktop-nav"
      >
        {[
          { id: 'home', label: t('navHome'), icon: Home },
          { id: 'chat', label: t('navChat'), icon: MessageSquare },
          { id: 'map', label: t('navMap'), icon: MapIcon },
          { id: 'alerts', label: t('navAlerts'), icon: AlertTriangle },
          { id: 'history', label: t('navHistory'), icon: History },
        ].map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: '8px',
                backgroundColor: isActive ? 'rgba(6, 182, 212, 0.15)' : 'transparent',
                color: isActive ? 'var(--cyan-hover)' : 'var(--text-muted)',
                fontWeight: isActive ? 600 : 500,
                fontSize: '0.875rem',
                border: isActive ? '1px solid var(--border-active)' : '1px solid transparent',
              }}
            >
              <Icon size={16} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Right Controls: SOS Distress, Location, Language, User Profile */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        {/* Emergency SOS Button */}
        <button
          onClick={() => setSosModalOpen(true)}
          title="Emergency Distress SOS Beacon"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '5px 12px',
            borderRadius: '8px',
            backgroundColor: '#dc2626',
            border: '1px solid #ef4444',
            color: '#ffffff',
            fontSize: '0.78rem',
            fontWeight: 800,
            letterSpacing: '0.04em',
            cursor: 'pointer',
            boxShadow: '0 0 12px rgba(220, 38, 38, 0.5)',
          }}
        >
          <span
            style={{
              width: '7px',
              height: '7px',
              borderRadius: '50%',
              backgroundColor: '#ffffff',
              boxShadow: '0 0 6px #ffffff',
            }}
          />
          <span>SOS</span>
        </button>

        {/* Geolocation Trigger */}
        <button
          onClick={requestLocation}
          title={t('useMyLocation')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 12px',
            borderRadius: '8px',
            backgroundColor: 'rgba(15, 32, 56, 0.9)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-main)',
            fontSize: '0.75rem',
          }}
        >
          <MapPin size={14} color="var(--cyan-primary)" className={locLoading ? 'spin-slow' : ''} />
          <span className="location-name" style={{ maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {userLocation ? `${userLocation.latitude.toFixed(2)}°N, ${userLocation.longitude.toFixed(2)}°E` : t('useMyLocation')}
          </span>
        </button>

        {/* Multilingual Selector */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setLangMenuOpen(!langMenuOpen)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 10px',
              borderRadius: '8px',
              backgroundColor: 'rgba(15, 32, 56, 0.9)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-main)',
              fontSize: '0.8rem',
            }}
          >
            <Globe size={15} color="var(--teal-accent)" />
            <span>{SUPPORTED_LANGUAGES.find((l) => l.code === language)?.label || 'English'}</span>
            <ChevronDown size={14} />
          </button>

          {langMenuOpen && (
            <div
              style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                marginTop: '6px',
                width: '230px',
                maxHeight: '360px',
                overflowY: 'auto',
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-active)',
                borderRadius: '10px',
                boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
                zIndex: 1010,
                padding: '4px',
              }}
            >
              {SUPPORTED_LANGUAGES.map((lang) => (
                <div
                  key={lang.code}
                  onClick={() => {
                    appStore.setLanguage(lang.code);
                    setLangMenuOpen(false);
                  }}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: '0.825rem',
                    backgroundColor: language === lang.code ? 'rgba(6, 182, 212, 0.2)' : 'transparent',
                    color: language === lang.code ? 'var(--cyan-hover)' : 'var(--text-main)',
                  }}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>{lang.flag}</span>
                    <span>{lang.nativeLabel}</span>
                  </span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                    {lang.code.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* User Account / Profile Button */}
        <div style={{ position: 'relative' }}>
          {isAuthenticated ? (
            <button
              onClick={() => setProfileMenuOpen(!profileMenuOpen)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 12px',
                borderRadius: '8px',
                backgroundColor: 'rgba(2, 132, 199, 0.2)',
                border: '1px solid rgba(2, 132, 199, 0.4)',
                color: '#ffffff',
                fontSize: '0.8rem',
                fontWeight: 600,
              }}
            >
              <UserIcon size={15} color="var(--cyan-primary)" />
              <span>{user?.name?.split(' ')[0] || 'User'}</span>
            </button>
          ) : (
            <button
              onClick={() => setActiveTab('login')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #0284c7 0%, #06b6d4 100%)',
                color: '#ffffff',
                fontSize: '0.8rem',
                fontWeight: 600,
              }}
            >
              <LogIn size={15} />
              <span>{t('loginBtn')}</span>
            </button>
          )}

          {profileMenuOpen && isAuthenticated && (
            <div
              style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                marginTop: '6px',
                width: '200px',
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-active)',
                borderRadius: '10px',
                boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
                zIndex: 1010,
                padding: '6px',
              }}
            >
              <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border-subtle)' }}>
                <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{user?.name}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{user?.email}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--cyan-primary)', marginTop: '2px', textTransform: 'capitalize' }}>
                  Role: {user?.role || 'Fisherman'}
                </div>
              </div>
              <div
                onClick={() => {
                  setActiveTab('profile');
                  setProfileMenuOpen(false);
                }}
                style={{
                  padding: '8px 12px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <UserIcon size={14} />
                <span>{t('navProfile')}</span>
              </div>
              <div
                onClick={handleLogout}
                style={{
                  padding: '8px 12px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  color: 'var(--status-nogo)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <LogIn size={14} style={{ transform: 'rotate(180deg)' }} />
                <span>{t('logout')}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <style>{`
        @media (min-width: 768px) {
          .desktop-nav {
            display: flex !important;
          }
        }
      `}</style>

      {/* Emergency Distress Beacon Modal */}
      <EmergencySosModal isOpen={sosModalOpen} onClose={() => setSosModalOpen(false)} />
    </header>
  );
};
