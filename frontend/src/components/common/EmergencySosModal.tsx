import React, { useState } from 'react';
import {
  AlertOctagon,
  PhoneCall,
  Radio,
  X,
  Compass,
  CheckCircle2,
  Send,
  LifeBuoy,
  Users,
  Ship,
  Phone,
  FileText,
} from 'lucide-react';
import { useAppState } from '../../hooks/useAppState';
import { alertService, EmergencyAlertPayload } from '../../services/alerts/alertService';

interface EmergencySosModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const EMERGENCY_TYPES = [
  { id: 'engine_failure', label: '⚓ Engine Failure / Drifting at Sea' },
  { id: 'sinking_ingress', label: '🌊 Water Ingress / Sinking Threat' },
  { id: 'medical_emergency', label: '🩺 Severe Medical Emergency on Board' },
  { id: 'man_overboard', label: '🏊 Man Overboard (MOB)' },
  { id: 'storm_capsize', label: '🌪️ Severe Storm / Capsize Risk' },
  { id: 'collision_grounding', label: '💥 Collision or Reef Grounding' },
  { id: 'security_piracy', label: '🛡️ Maritime Security / Boundary Issue' },
];

export const EmergencySosModal: React.FC<EmergencySosModalProps> = ({ isOpen, onClose }) => {
  const { userLocation, user } = useAppState();

  const [lat, setLat] = useState<string>(
    userLocation ? userLocation.latitude.toFixed(4) : '18.9220'
  );
  const [lon, setLon] = useState<string>(
    userLocation ? userLocation.longitude.toFixed(4) : '72.8340'
  );
  const [vesselName, setVesselName] = useState<string>('');
  const [vesselRegistration, setVesselRegistration] = useState<string>('');
  const [emergencyType, setEmergencyType] = useState<string>('engine_failure');
  const [crewCount, setCrewCount] = useState<number>(3);
  const [contactPhone, setContactPhone] = useState<string>('');
  const [notes, setNotes] = useState<string>('');

  const [submitting, setSubmitting] = useState<boolean>(false);
  const [transmittedAlert, setTransmittedAlert] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    const typeObj = EMERGENCY_TYPES.find((t) => t.id === emergencyType);

    const payload: EmergencyAlertPayload = {
      latitude: parseFloat(lat) || (userLocation ? userLocation.latitude : undefined),
      longitude: parseFloat(lon) || (userLocation ? userLocation.longitude : undefined),
      locationName: userLocation?.name || 'Coastal Coordinates',
      vesselName: vesselName || 'Coastal Craft',
      vesselRegistration: vesselRegistration || undefined,
      emergencyType: typeObj ? typeObj.label : 'Emergency Distress',
      crewCount: Number(crewCount) || 1,
      contactPhone: contactPhone || 'VHF Channel 16',
      notes: notes.trim() || undefined,
      userName: user?.name || undefined,
    };

    try {
      const res = await alertService.sendEmergencyAlert(payload);
      setTransmittedAlert(res);
    } catch (err: any) {
      console.error('Failed to broadcast SOS:', err);
      setError('Distress transmission encountered a network delay. Call Coast Guard 1554 directly.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(5, 10, 20, 0.85)',
        backdropFilter: 'blur(8px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
      }}
    >
      <div
        className="glass-panel animate-scale-up"
        style={{
          width: '100%',
          maxWidth: '540px',
          maxHeight: '92vh',
          overflowY: 'auto',
          backgroundColor: '#0c1322',
          border: '1px solid rgba(239, 68, 68, 0.6)',
          boxShadow: '0 0 40px rgba(239, 68, 68, 0.35)',
          borderRadius: '16px',
          padding: '24px',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                backgroundColor: 'rgba(239, 68, 68, 0.2)',
                border: '1px solid #ef4444',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <AlertOctagon size={26} color="#ef4444" className="pulse-danger" />
            </div>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#ffffff', margin: 0 }}>
                EMERGENCY SOS BEACON
              </h2>
              <span style={{ fontSize: '0.75rem', color: '#f87171', fontWeight: 600 }}>
                Direct Broadcast to Indian Coast Guard MRCC & Nearby Craft
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-dim)',
              cursor: 'pointer',
              padding: '4px',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Immediate Call Hotlines Banner */}
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '10px',
            padding: '12px 14px',
            marginBottom: '18px',
          }}
        >
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#fca5a5', textTransform: 'uppercase', marginBottom: '8px' }}>
            Immediate Voice Maritime Hotlines (24x7 Toll-Free)
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            <a
              href="tel:1554"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                backgroundColor: '#dc2626',
                color: '#ffffff',
                padding: '8px 12px',
                borderRadius: '6px',
                textDecoration: 'none',
                fontSize: '0.85rem',
                fontWeight: 700,
                justifyContent: 'center',
              }}
            >
              <PhoneCall size={16} />
              <span>Coast Guard: 1554</span>
            </a>
            <a
              href="tel:1093"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                backgroundColor: 'rgba(255, 255, 255, 0.08)',
                color: '#f8fafc',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                padding: '8px 12px',
                borderRadius: '6px',
                textDecoration: 'none',
                fontSize: '0.85rem',
                fontWeight: 600,
                justifyContent: 'center',
              }}
            >
              <PhoneCall size={16} />
              <span>Coastal Police: 1093</span>
            </a>
          </div>
          <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Radio size={12} color="#38bdf8" />
            <span>VHF Radio Distress Frequency: <b>Channel 16 (156.800 MHz)</b></span>
          </div>
        </div>

        {transmittedAlert ? (
          /* Transmitted State */
          <div
            style={{
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              borderRadius: '12px',
              padding: '20px',
              textAlign: 'center',
            }}
          >
            <CheckCircle2 size={48} color="#10b981" style={{ margin: '0 auto 12px' }} />
            <h3 style={{ color: '#10b981', fontSize: '1.1rem', fontWeight: 800, margin: '0 0 6px' }}>
              DISTRESS BEACON BROADCASTED
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', lineHeight: 1.4, margin: '0 0 16px' }}>
              Your distress beacon (<b>{transmittedAlert.alertId}</b>) has been logged and relayed to coastal stations and vessels.
            </p>
            <div style={{ fontSize: '0.8rem', color: '#f8fafc', backgroundColor: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '8px', textAlign: 'left', marginBottom: '16px' }}>
              <div><b>Location:</b> {lat}° N, {lon}° E</div>
              <div><b>Craft:</b> {vesselName || 'Fisherman Craft'}</div>
              <div><b>Emergency:</b> {transmittedAlert.details?.emergencyType}</div>
              <div><b>Crew:</b> {crewCount} Souls</div>
            </div>
            <p style={{ color: '#38bdf8', fontSize: '0.78rem', fontWeight: 600 }}>
              Keep VHF Channel 16 ON. Stand by with life jackets secured.
            </p>
            <button
              onClick={() => {
                setTransmittedAlert(null);
                onClose();
              }}
              style={{
                marginTop: '14px',
                padding: '10px 20px',
                backgroundColor: 'var(--cyan-primary)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              Close & Monitor Map
            </button>
          </div>
        ) : (
          /* SOS Input Form */
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {error && (
              <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.2)', border: '1px solid #ef4444', color: '#fca5a5', padding: '8px 12px', borderRadius: '8px', fontSize: '0.8rem' }}>
                {error}
              </div>
            )}

            {/* Coordinates */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: 600 }}>
                  Latitude (°N)
                </label>
                <input
                  type="text"
                  value={lat}
                  onChange={(e) => setLat(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    backgroundColor: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    padding: '8px 10px',
                    color: '#ffffff',
                    fontSize: '0.85rem',
                    fontFamily: 'var(--font-mono)',
                    outline: 'none',
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: 600 }}>
                  Longitude (°E)
                </label>
                <input
                  type="text"
                  value={lon}
                  onChange={(e) => setLon(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    backgroundColor: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    padding: '8px 10px',
                    color: '#ffffff',
                    fontSize: '0.85rem',
                    fontFamily: 'var(--font-mono)',
                    outline: 'none',
                  }}
                />
              </div>
            </div>

            {/* Emergency Nature */}
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: 600 }}>
                Nature of Maritime Distress
              </label>
              <select
                value={emergencyType}
                onChange={(e) => setEmergencyType(e.target.value)}
                style={{
                  width: '100%',
                  backgroundColor: 'rgba(15, 23, 42, 0.8)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  padding: '8px 10px',
                  color: '#ffffff',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              >
                {EMERGENCY_TYPES.map((t) => (
                  <option key={t.id} value={t.id} style={{ background: '#0f172a', color: '#f8fafc' }}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Vessel Details */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: 600 }}>
                  <Ship size={12} /> Vessel Name / Reg. No.
                </label>
                <input
                  type="text"
                  placeholder="e.g. Sagar Kanya / MH-01-440"
                  value={vesselName}
                  onChange={(e) => setVesselName(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    padding: '8px 10px',
                    color: '#ffffff',
                    fontSize: '0.85rem',
                    outline: 'none',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: 600 }}>
                  <Users size={12} /> Crew on Board
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={crewCount}
                  onChange={(e) => setCrewCount(parseInt(e.target.value) || 1)}
                  style={{
                    width: '100%',
                    backgroundColor: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    padding: '8px 10px',
                    color: '#ffffff',
                    fontSize: '0.85rem',
                    outline: 'none',
                  }}
                />
              </div>
            </div>

            {/* Contact Phone & Notes */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: 600 }}>
                  <Phone size={12} /> Contact / Sat Phone
                </label>
                <input
                  type="text"
                  placeholder="+91 98765 43210"
                  value={contactPhone}
                  onChange={(e) => setContactPhone(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    padding: '8px 10px',
                    color: '#ffffff',
                    fontSize: '0.85rem',
                    outline: 'none',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: 600 }}>
                  <FileText size={12} /> Distress Notes
                </label>
                <input
                  type="text"
                  placeholder="e.g. Taking in water, rudder broken"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    padding: '8px 10px',
                    color: '#ffffff',
                    fontSize: '0.85rem',
                    outline: 'none',
                  }}
                />
              </div>
            </div>

            {/* Transmit Button */}
            <button
              type="submit"
              disabled={submitting}
              style={{
                marginTop: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '10px',
                padding: '14px',
                backgroundColor: '#dc2626',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                fontSize: '0.95rem',
                fontWeight: 800,
                letterSpacing: '0.04em',
                cursor: submitting ? 'wait' : 'pointer',
                boxShadow: '0 0 20px rgba(220, 38, 38, 0.6)',
              }}
            >
              <LifeBuoy size={20} className={submitting ? 'spin-slow' : ''} />
              <span>{submitting ? 'TRANSMITTING BEACON...' : 'TRANSMIT EMERGENCY SOS BEACON'}</span>
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
