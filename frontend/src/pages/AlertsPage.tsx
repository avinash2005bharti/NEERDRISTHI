import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ShieldAlert,
  Wind,
  Waves,
  RefreshCw,
  ExternalLink,
  MapPin,
  Clock,
  Filter,
  LifeBuoy,
  PhoneCall,
} from 'lucide-react';
import { alertService } from '../services/alerts/alertService';
import { MarineAlert } from '../types';
import { useAppState } from '../hooks/useAppState';
import { getTranslation } from '../i18n/translations';
import { EmergencySosModal } from '../components/common/EmergencySosModal';

export const AlertsPage: React.FC = () => {
  const { language, userLocation } = useAppState();
  const t = (key: string) => getTranslation(language, key);

  const [alerts, setAlerts] = useState<MarineAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [sosModalOpen, setSosModalOpen] = useState(false);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const data = await alertService.getAlerts(
        userLocation?.latitude,
        userLocation?.longitude
      );
      setAlerts(data);
    } catch (err) {
      console.error('Failed to load alerts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [userLocation]);

  const filtered = alerts.filter((a) => {
    if (filterSeverity === 'ALL') return true;
    return a.severity === filterSeverity;
  });

  return (
    <div
      style={{
        maxWidth: '900px',
        margin: '0 auto',
        padding: '1.5rem',
        minHeight: 'calc(100vh - var(--nav-height))',
      }}
      className="animate-fade-in"
    >
      {/* Page Header */}
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
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <AlertTriangle size={20} color="var(--status-nogo)" />
            </div>
            <h1 style={{ fontSize: '1.4rem', color: '#ffffff' }}>
              {t('activeAlerts')}
            </h1>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.825rem', marginTop: '4px' }}>
            Real-time cyclone, severe weather, and maritime danger bulletins from GDACS & IMD.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => setSosModalOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#dc2626',
              border: '1px solid #ef4444',
              color: '#ffffff',
              fontSize: '0.8rem',
              fontWeight: 800,
              padding: '8px 14px',
              borderRadius: '8px',
              cursor: 'pointer',
              boxShadow: '0 0 15px rgba(220, 38, 38, 0.4)',
            }}
          >
            <LifeBuoy size={15} />
            <span>SEND EMERGENCY SOS</span>
          </button>

          <button
            onClick={fetchAlerts}
            className="btn-secondary"
            style={{ fontSize: '0.8rem', padding: '8px 12px' }}
          >
            <RefreshCw size={14} className={loading ? 'spin-slow' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Emergency Quick-Action Banner */}
      <div
        className="glass-panel"
        style={{
          border: '1px solid rgba(239, 68, 68, 0.4)',
          backgroundColor: 'rgba(239, 68, 68, 0.08)',
          borderRadius: '12px',
          padding: '14px 18px',
          marginBottom: '1.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              backgroundColor: 'rgba(239, 68, 68, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <LifeBuoy size={20} color="#ef4444" />
          </div>
          <div>
            <div style={{ fontWeight: 700, color: '#fca5a5', fontSize: '0.9rem' }}>
              In Immediate Danger at Sea? Send Real-Time SOS Beacon
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '2px' }}>
              Broadcasts GPS coordinates to Coast Guard MRCC (1554), Coastal Police (1093), and nearby vessels.
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <a
            href="tel:1554"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              color: '#ffffff',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '0.78rem',
              fontWeight: 700,
              textDecoration: 'none',
            }}
          >
            <PhoneCall size={14} />
            <span>Call 1554</span>
          </a>

          <button
            onClick={() => setSosModalOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#dc2626',
              color: '#ffffff',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '0.78rem',
              fontWeight: 800,
              cursor: 'pointer',
              boxShadow: '0 0 10px rgba(220, 38, 38, 0.5)',
            }}
          >
            <span>Activate SOS</span>
          </button>
        </div>
      </div>

      {/* Severity Filter Pills */}
      <div
        style={{
          display: 'flex',
          gap: '6px',
          marginBottom: '1.25rem',
          overflowX: 'auto',
          paddingBottom: '4px',
        }}
      >
        {['ALL', 'CRITICAL', 'HIGH', 'MODERATE', 'WARNING'].map((sev) => (
          <button
            key={sev}
            onClick={() => setFilterSeverity(sev)}
            style={{
              padding: '6px 12px',
              borderRadius: '20px',
              fontSize: '0.75rem',
              fontWeight: 600,
              backgroundColor: filterSeverity === sev ? 'var(--cyan-primary)' : 'rgba(255, 255, 255, 0.05)',
              color: filterSeverity === sev ? '#ffffff' : 'var(--text-muted)',
              border: filterSeverity === sev ? 'none' : '1px solid var(--border-subtle)',
            }}
          >
            {sev}
          </button>
        ))}
      </div>

      {/* Alerts Feed */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-muted)' }}>
          <RefreshCw size={24} className="spin-slow" style={{ margin: '0 auto 12px' }} />
          <div>Checking active meteorological and disaster feeds...</div>
        </div>
      ) : filtered.length === 0 ? (
        <div
          className="glass-panel"
          style={{
            textAlign: 'center',
            padding: '3rem 1.5rem',
            border: '1px solid rgba(16, 185, 129, 0.3)',
          }}
        >
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              backgroundColor: 'rgba(16, 185, 129, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1rem',
            }}
          >
            ✓
          </div>
          <h3 style={{ color: 'var(--status-go)', fontSize: '1.1rem', marginBottom: '0.5rem' }}>
            Sea Conditions Clear
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            {t('noAlerts')}
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {filtered.map((alert, idx) => {
            const isCritical = alert.severity === 'CRITICAL' || alert.severity === 'HIGH';
            return (
              <div
                key={alert.id || idx}
                className="glass-panel"
                style={{
                  padding: '16px 20px',
                  borderLeft: `4px solid ${isCritical ? 'var(--status-nogo)' : 'var(--status-caution)'}`,
                  backgroundColor: isCritical ? 'rgba(239, 68, 68, 0.06)' : 'var(--bg-card)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      style={{
                        padding: '3px 8px',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        backgroundColor: isCritical ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                        color: isCritical ? 'var(--status-nogo)' : 'var(--status-caution)',
                      }}
                    >
                      {alert.severity}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
                      {alert.category || 'Meteorological Hazard'}
                    </span>
                  </div>

                  <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Clock size={12} />
                    {new Date(alert.issued_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                  </span>
                </div>

                <h3 style={{ fontSize: '1rem', color: '#ffffff', marginBottom: '6px' }}>
                  {alert.title}
                </h3>

                {alert.description && (
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', lineHeight: '1.5', marginBottom: '10px' }}>
                    {alert.description}
                  </p>
                )}

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    borderTop: '1px solid var(--border-subtle)',
                    paddingTop: '8px',
                    fontSize: '0.75rem',
                    color: 'var(--text-dim)',
                  }}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <ExternalLink size={12} />
                    Source: {alert.source || 'GDACS Feed'}
                  </span>

                  {alert.affected_area?.name && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <MapPin size={12} color="var(--cyan-primary)" />
                      {alert.affected_area.name}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Emergency SOS Distress Beacon Modal */}
      <EmergencySosModal isOpen={sosModalOpen} onClose={() => setSosModalOpen(false)} />
    </div>
  );
};
