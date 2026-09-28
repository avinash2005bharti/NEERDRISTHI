import React, { useEffect, useState } from 'react';
import {
  User as UserIcon,
  Mail,
  Anchor,
  Globe,
  Save,
  LogOut,
  MapPin,
  CheckCircle2,
  Shield,
} from 'lucide-react';
import { useAppState } from '../hooks/useAppState';
import { appStore } from '../stores/appState';
import { authService } from '../services/auth/authService';
import { SUPPORTED_LANGUAGES, getTranslation, LanguageCode } from '../i18n/translations';

interface ProfilePageProps {
  onLogoutSuccess?: () => void;
  onNavigateLogin?: () => void;
}

export const ProfilePage: React.FC<ProfilePageProps> = ({
  onLogoutSuccess,
  onNavigateLogin,
}) => {
  const { user, isAuthenticated, language } = useAppState();
  const t = (key: string) => getTranslation(language, key);

  const [name, setName] = useState(user?.name || '');
  const [role, setRole] = useState(user?.role || 'fisherman');
  const [vesselClass, setVesselClass] = useState(
    user?.vesselClass || 'motorized_fiberglass'
  );
  const [prefLang, setPrefLang] = useState<LanguageCode>(
    (user?.preferredLanguage as LanguageCode) || language
  );
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    if (user) {
      setName(user.name || '');
      setRole(user.role || 'fisherman');
      setVesselClass(user.vesselClass || 'motorized_fiberglass');
      setPrefLang((user.preferredLanguage as LanguageCode) || language);
    }
  }, [user]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSavedSuccess(false);
    try {
      const updated = await authService.updateProfile({
        name,
        role: role as any,
        vesselClass,
        preferredLanguage: prefLang,
      });
      appStore.setUser(updated, appStore.getState().token);
      appStore.setLanguage(prefLang);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to update profile:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = async () => {
    await authService.logout();
    appStore.setUser(null, null);
    if (onLogoutSuccess) {
      onLogoutSuccess();
    }
  };

  if (!isAuthenticated) {
    return (
      <div
        style={{
          maxWidth: '500px',
          margin: '3rem auto',
          padding: '2rem',
          textAlign: 'center',
        }}
        className="glass-panel animate-fade-in"
      >
        <UserIcon size={44} color="var(--cyan-primary)" style={{ margin: '0 auto 1rem' }} />
        <h2 style={{ color: '#ffffff', marginBottom: '0.5rem' }}>Guest Session</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
          Sign in or create an account to save vessel configurations, persistent locations, and maritime audit history.
        </p>
        <button
          onClick={onNavigateLogin}
          className="btn-primary"
          style={{ width: '100%' }}
        >
          Sign In to Your Coastal Account
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        maxWidth: '680px',
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
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '12px',
              backgroundColor: 'rgba(6, 182, 212, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <UserIcon size={22} color="var(--cyan-primary)" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.4rem', color: '#ffffff' }}>Coastal Profile</h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
              Account telemetry and deterministic vessel safety policy parameters.
            </p>
          </div>
        </div>

        <button
          onClick={handleLogout}
          className="btn-secondary"
          style={{ color: 'var(--status-nogo)', borderColor: 'rgba(239, 68, 68, 0.3)', fontSize: '0.8rem', padding: '8px 12px' }}
        >
          <LogOut size={14} />
          <span>{t('logout')}</span>
        </button>
      </div>

      {savedSuccess && (
        <div
          style={{
            padding: '10px 14px',
            borderRadius: '8px',
            backgroundColor: 'var(--status-go-bg)',
            border: '1px solid rgba(16, 185, 129, 0.4)',
            color: 'var(--status-go)',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '1.25rem',
          }}
        >
          <CheckCircle2 size={16} />
          <span>Profile configuration successfully saved to MongoDB.</span>
        </div>
      )}

      {/* Profile Form */}
      <form onSubmit={handleSave} className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Email (Readonly) */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '6px' }}>
              AUTHENTICATED EMAIL
            </label>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                padding: '10px 14px',
                borderRadius: '8px',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-muted)',
                fontSize: '0.9rem',
              }}
            >
              <Mail size={16} color="var(--text-dim)" />
              <span>{user?.email}</span>
            </div>
          </div>

          {/* Full Name */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '6px' }}>
              FULL NAME
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              style={{
                width: '100%',
                backgroundColor: 'var(--bg-abyss)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '10px 14px',
                color: '#ffffff',
                fontSize: '0.9rem',
                outline: 'none',
              }}
            />
          </div>

          {/* User Role */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '6px' }}>
              ROLE & PERMISSION LEVEL
            </label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as any)}
              style={{
                width: '100%',
                backgroundColor: 'var(--bg-abyss)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '10px 14px',
                color: '#ffffff',
                fontSize: '0.9rem',
                outline: 'none',
              }}
            >
              <option value="fisherman">Artisanal Fisherman / Fisherwoman</option>
              <option value="authority">Maritime Authority (Coast Guard / Port Trust)</option>
              <option value="disaster_manager">Disaster Management Officer</option>
              <option value="admin">Administrator</option>
            </select>
          </div>

          {/* Vessel Classification */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '6px' }}>
              VESSEL CLASSIFICATION (Used for physical wave & wind safety limits)
            </label>
            <select
              value={vesselClass}
              onChange={(e) => setVesselClass(e.target.value)}
              style={{
                width: '100%',
                backgroundColor: 'var(--bg-abyss)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '10px 14px',
                color: '#ffffff',
                fontSize: '0.9rem',
                outline: 'none',
              }}
            >
              <option value="traditional_unmotorized">Traditional Unmotorized (Canoe / Catamaran - Max 1.2m Waves)</option>
              <option value="motorized_fiberglass">Motorized Fiberglass (OBM 9.9HP - Max 2.0m Waves)</option>
              <option value="mechanized_trawler">Mechanized Trawler (Inboard Diesel - Max 3.0m Waves)</option>
              <option value="deep_sea_vessel">Deep Sea Commercial Vessel (Max 4.5m Waves)</option>
            </select>
          </div>

          {/* Preferred Language */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '6px' }}>
              PREFERRED AI REASONING LANGUAGE
            </label>
            <select
              value={prefLang}
              onChange={(e) => setPrefLang(e.target.value as LanguageCode)}
              style={{
                width: '100%',
                backgroundColor: 'var(--bg-abyss)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '10px 14px',
                color: '#ffffff',
                fontSize: '0.9rem',
                outline: 'none',
              }}
            >
              {SUPPORTED_LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.flag} {lang.nativeLabel} ({lang.label})
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginTop: '8px' }}>
            <button
              type="submit"
              disabled={saving}
              className="btn-primary"
              style={{ width: '100%', padding: '12px' }}
            >
              <Save size={16} />
              <span>{saving ? 'Saving Changes...' : 'Save Profile Changes'}</span>
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};
