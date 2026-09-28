import React from 'react';
import {
  Thermometer,
  Waves,
  Wind,
  Droplets,
  ShieldCheck,
  ShieldAlert,
  Clock,
  ExternalLink,
  MessageSquare,
  X,
  Compass,
} from 'lucide-react';
import { SpotOverview } from '../../types';

interface OceanDataPanelProps {
  data: SpotOverview | null;
  loading: boolean;
  onClose: () => void;
  onAskAboutLocation: (lat: number, lon: number) => void;
}

export const OceanDataPanel: React.FC<OceanDataPanelProps> = ({
  data,
  loading,
  onClose,
  onAskAboutLocation,
}) => {
  if (loading) {
    return (
      <div
        className="glass-panel"
        style={{
          position: 'absolute',
          bottom: '80px',
          right: '16px',
          width: '320px',
          padding: '16px',
          zIndex: 1000,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Compass size={18} color="var(--cyan-primary)" className="spin-slow" />
          <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>
            Querying Marine Telemetry...
          </span>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const lat = data.coordinates?.latitude || 0;
  const lon = data.coordinates?.longitude || 0;

  const isSafe = data.safety?.recommendation === 'SAFE_TO_FISH' || data.safety?.risk_level === 'LOWER' || data.safety?.risk_level === 'LOW';

  return (
    <div
      className="glass-panel-glow animate-fade-in"
      style={{
        position: 'absolute',
        bottom: '80px',
        right: '16px',
        width: '340px',
        maxWidth: 'calc(100vw - 32px)',
        padding: '16px',
        zIndex: 1000,
        maxHeight: 'calc(100vh - 160px)',
        overflowY: 'auto',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid var(--border-subtle)',
          paddingBottom: '10px',
          marginBottom: '12px',
        }}
      >
        <div>
          <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--cyan-primary)', fontWeight: 700 }}>
            Ocean Telemetry Spot
          </span>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', fontWeight: 600 }}>
            {lat.toFixed(4)}° N, {lon.toFixed(4)}° E
          </div>
        </div>
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', color: 'var(--text-dim)' }}
        >
          <X size={18} />
        </button>
      </div>

      {/* Grid of Telemetry Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '12px' }}>
        {/* SST */}
        <div
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.03)',
            borderRadius: '8px',
            padding: '8px 10px',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', fontSize: '0.7rem' }}>
            <Thermometer size={14} color="#f97316" />
            <span>SST</span>
          </div>
          <div style={{ fontSize: '1.1rem', fontWeight: 700, marginTop: '2px', color: '#fed7aa' }}>
            {data.marine?.sea_surface_temp_c ? `${data.marine.sea_surface_temp_c}°C` : 'N/A'}
          </div>
        </div>

        {/* Chlorophyll */}
        <div
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.03)',
            borderRadius: '8px',
            padding: '8px 10px',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', fontSize: '0.7rem' }}>
            <Droplets size={14} color="var(--teal-accent)" />
            <span>Chlorophyll</span>
          </div>
          <div style={{ fontSize: '1.1rem', fontWeight: 700, marginTop: '2px', color: '#99f6e4' }}>
            {data.marine?.chlorophyll_mg_m3 ? `${data.marine.chlorophyll_mg_m3} mg/m³` : 'N/A'}
          </div>
        </div>

        {/* Wave Height */}
        <div
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.03)',
            borderRadius: '8px',
            padding: '8px 10px',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', fontSize: '0.7rem' }}>
            <Waves size={14} color="var(--cyan-primary)" />
            <span>Waves / Swell</span>
          </div>
          <div style={{ fontSize: '1.1rem', fontWeight: 700, marginTop: '2px', color: '#bae6fd' }}>
            {data.marine?.significant_wave_height_m ? `${data.marine.significant_wave_height_m} m` : 'N/A'}
          </div>
        </div>

        {/* Wind */}
        <div
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.03)',
            borderRadius: '8px',
            padding: '8px 10px',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', fontSize: '0.7rem' }}>
            <Wind size={14} color="#a855f7" />
            <span>Wind Speed</span>
          </div>
          <div style={{ fontSize: '1.1rem', fontWeight: 700, marginTop: '2px', color: '#e9d5ff' }}>
            {data.weather?.wind_speed_knots ? `${data.weather.wind_speed_knots} kts` : 'N/A'}
          </div>
        </div>
      </div>

      {/* Safety & Tide Status */}
      <div
        style={{
          padding: '8px 10px',
          borderRadius: '8px',
          backgroundColor: isSafe ? 'var(--status-go-bg)' : 'var(--status-caution-bg)',
          border: `1px solid ${isSafe ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isSafe ? <ShieldCheck size={18} color="var(--status-go)" /> : <ShieldAlert size={18} color="var(--status-caution)" />}
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: isSafe ? 'var(--status-go)' : 'var(--status-caution)' }}>
              {data.safety?.recommendation || 'CONDITIONS MONITORED'}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              Nearest PFZ: {data.safety?.nearest_pfz_km || 0} km
            </div>
          </div>
        </div>
        {data.marine?.tide_height_m !== undefined && (
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 700 }}>
              {data.marine.tide_height_m}m
            </div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)' }}>
              Tide: {data.marine.tide_state || 'Station'}
            </div>
          </div>
        )}
      </div>

      {/* Attribution & Provenance */}
      <div
        style={{
          borderTop: '1px solid var(--border-subtle)',
          paddingTop: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.7rem',
          color: 'var(--text-dim)',
          marginBottom: '12px',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <ExternalLink size={11} />
          {data.source || 'INCOIS / Open-Meteo'}
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Clock size={11} />
          {data.status || (data.is_live ? 'LIVE' : 'DEMO')}
        </span>
      </div>

      {/* Ask AI Action */}
      <button
        className="btn-primary"
        style={{ width: '100%', fontSize: '0.8rem', padding: '8px 12px' }}
        onClick={() => onAskAboutLocation(lat, lon)}
      >
        <MessageSquare size={15} />
        <span>Ask NEERDRISTI About This Point</span>
      </button>
    </div>
  );
};
