import React, { useState } from 'react';
import { Compass, LogIn, AlertCircle, ArrowRight } from 'lucide-react';
import { authService } from '../services/auth/authService';
import { appStore } from '../stores/appState';
import { useAppState } from '../hooks/useAppState';
import { getTranslation } from '../i18n/translations';

interface LoginPageProps {
  onSuccess: () => void;
  onNavigateRegister: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({
  onSuccess,
  onNavigateRegister,
}) => {
  const { language } = useAppState();
  const t = (key: string) => getTranslation(language, key);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await authService.login({ email, password });
      if (res.success && res.data) {
        appStore.setUser(res.data.user, res.data.token);
        onSuccess();
      }
    } catch (err: any) {
      setError(
        err.message ||
        'Authentication failed. Please verify your credentials and try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        maxWidth: '440px',
        margin: '3rem auto',
        padding: '0 1rem',
      }}
      className="animate-fade-in"
    >
      <div className="glass-panel" style={{ padding: '2rem' }}>
        {/* Brand */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '16px',
              overflow: 'hidden',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1rem',
              boxShadow: '0 0 24px rgba(6, 182, 212, 0.45)',
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
          <h1 style={{ fontSize: '1.5rem', color: '#ffffff', marginBottom: '4px' }}>
            {t('loginTitle')}
          </h1>
          <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)' }}>
            Access real-time oceanographic advisories and vessel safety intelligence.
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

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '6px' }}>
              {t('email').toUpperCase()}
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="e.g. raman.fisherman@example.in"
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
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '6px' }}>
              {t('password').toUpperCase()}
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
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

          <button
            type="submit"
            disabled={loading}
            className="btn-primary"
            style={{ width: '100%', padding: '12px', marginTop: '6px' }}
          >
            <LogIn size={16} />
            <span>{loading ? 'Authenticating...' : t('loginBtn')}</span>
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
          Don't have an account?{' '}
          <button
            onClick={onNavigateRegister}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--cyan-hover)',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Register here
          </button>
        </div>
      </div>
    </div>
  );
};
