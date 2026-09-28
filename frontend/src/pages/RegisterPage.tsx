import React, { useState } from 'react';
import { Compass, UserPlus, AlertCircle } from 'lucide-react';
import { authService } from '../services/auth/authService';
import { appStore } from '../stores/appState';
import { useAppState } from '../hooks/useAppState';
import { SUPPORTED_LANGUAGES, getTranslation, LanguageCode } from '../i18n/translations';

interface RegisterPageProps {
  onSuccess: () => void;
  onNavigateLogin: () => void;
}

export const RegisterPage: React.FC<RegisterPageProps> = ({
  onSuccess,
  onNavigateLogin,
}) => {
  const { language } = useAppState();
  const t = (key: string) => getTranslation(language, key);

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('fisherman');
  const [vesselClass, setVesselClass] = useState('motorized_fiberglass');
  const [prefLang, setPrefLang] = useState<LanguageCode>(language);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await authService.register({
        name,
        email,
        password,
        role,
        vesselClass,
        preferredLanguage: prefLang,
      });

      if (res.success && res.data) {
        appStore.setUser(res.data.user, res.data.token);
        appStore.setLanguage(prefLang);
        onSuccess();
      }
    } catch (err: any) {
      setError(
        err.message || 'Registration failed. Please check the provided information.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        maxWidth: '480px',
        margin: '2rem auto',
        padding: '0 1rem',
      }}
      className="animate-fade-in"
    >
      <div className="glass-panel" style={{ padding: '2rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
          <div
            style={{
              width: '58px',
              height: '58px',
              borderRadius: '14px',
              overflow: 'hidden',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 0.75rem',
              boxShadow: '0 0 20px rgba(6, 182, 212, 0.45)',
              border: '1.5px solid rgba(56, 189, 248, 0.4)',
              backgroundColor: '#0a1d37',
            }}
          >
            <img
              src="/neerdristi.logo.png"
              alt="NEERDRISTI Logo"
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
              }}
            />
          </div>
          <h1 style={{ fontSize: '1.4rem', color: '#ffffff', marginBottom: '4px' }}>
            {t('registerTitle')}
          </h1>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Join India's AI-powered collaborative marine reasoning platform.
          </p>
        </div>

        {error && (
          <div
            style={{
              padding: '10px 14px',
              borderRadius: '8px',
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#fca5a5',
              fontSize: '0.825rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              marginBottom: '1.25rem',
            }}
          >
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '4px' }}>
              {t('fullName').toUpperCase()}
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="e.g. Raman K"
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

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '4px' }}>
              {t('email').toUpperCase()}
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="e.g. raman@example.in"
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

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '4px' }}>
              {t('password').toUpperCase()} (MIN 6 CHARACTERS)
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              placeholder="••••••••"
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

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '4px' }}>
              {t('role').toUpperCase()}
            </label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
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

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '4px' }}>
              {t('vesselClass').toUpperCase()}
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
              <option value="traditional_unmotorized">Traditional Unmotorized (Max 1.2m Waves)</option>
              <option value="motorized_fiberglass">Motorized Fiberglass (Max 2.0m Waves)</option>
              <option value="mechanized_trawler">Mechanized Trawler (Max 3.0m Waves)</option>
              <option value="deep_sea_vessel">Deep Sea Commercial Vessel (Max 4.5m Waves)</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '4px' }}>
              PREFERRED LANGUAGE
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

          <button
            type="submit"
            disabled={loading}
            className="btn-primary"
            style={{ width: '100%', padding: '12px', marginTop: '8px' }}
          >
            <UserPlus size={16} />
            <span>{loading ? 'Creating Account...' : t('registerBtn')}</span>
          </button>
        </form>

        <div
          style={{
            marginTop: '1.5rem',
            textAlign: 'center',
            fontSize: '0.825rem',
            color: 'var(--text-muted)',
            borderTop: '1px solid var(--border-subtle)',
            paddingTop: '1rem',
          }}
        >
          Already have an account?{' '}
          <button
            onClick={onNavigateLogin}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--cyan-hover)',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Sign In
          </button>
        </div>
      </div>
    </div>
  );
};
