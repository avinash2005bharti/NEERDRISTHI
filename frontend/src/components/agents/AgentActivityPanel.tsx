import React from 'react';
import {
  Brain,
  CheckCircle2,
  Clock,
  AlertCircle,
  Minimize2,
  Maximize2,
  Layers,
} from 'lucide-react';
import { AgentStatusTrace } from '../../types';

interface AgentActivityPanelProps {
  traces: AgentStatusTrace[];
  isRunning: boolean;
  statusMessage?: string | null;
}

const AGENT_CATALOG: Record<
  string,
  { label: string; icon: string; description: string }
> = {
  planner: {
    label: 'Query Intake & Planner',
    icon: '🧭',
    description: 'Validates nautical intent, coordinates, and vessel class',
  },
  geospatial: {
    label: 'Geospatial & Boundary Agent',
    icon: '🗺️',
    description: 'Resolves coastal coordinates & evaluates 2dsphere marine boundaries',
  },
  marine_pfz: {
    label: 'Marine & PFZ Agent',
    icon: '🐟',
    description: 'Fetches oceanographic telemetry, thermal fronts & PFZ coordinates',
  },
  weather_sea_state: {
    label: 'Weather & Sea-State Agent',
    icon: '🌊',
    description: 'Retrieves Open-Meteo atmospheric wind, waves, gusts & swell',
  },
  semantic_memory: {
    label: 'Semantic Memory Agent',
    icon: '🧠',
    description: 'Queries vector database for historical coastal advisories',
  },
  safety_risk_engine: {
    label: 'Deterministic Safety Engine',
    icon: '⚖️',
    description: 'Executes physical policy rules (cyclones, vessel thresholds, gaps)',
  },
  synthesis: {
    label: 'Grounded Synthesis Agent',
    icon: '✨',
    description: 'Produces multilingual grounded explanation preserving verdict',
  },
};

export const AgentActivityPanel: React.FC<AgentActivityPanelProps> = ({
  traces,
  isRunning,
  statusMessage,
}) => {
  const [collapsed, setCollapsed] = React.useState(false);

  // If no traces and not running, do not render an empty box
  if (!isRunning && (!traces || traces.length === 0)) {
    return null;
  }

  // Map known agents in logical order
  const order = [
    'planner',
    'geospatial',
    'marine_pfz',
    'weather_sea_state',
    'semantic_memory',
    'safety_risk_engine',
    'synthesis',
  ];

  return (
    <div
      style={{
        backgroundColor: 'rgba(10, 22, 38, 0.95)',
        border: '1px solid var(--border-active)',
        borderRadius: '12px',
        padding: '12px 16px',
        margin: '12px 0',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)',
      }}
      className="animate-fade-in"
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
        }}
        onClick={() => setCollapsed(!collapsed)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Brain size={18} color="var(--cyan-primary)" className={isRunning ? 'spin-slow' : ''} />
          <span style={{ fontWeight: 600, fontSize: '0.85rem', color: '#ffffff' }}>
            NEERDRISTI Multi-Agent Orchestration
          </span>
          {isRunning ? (
            <span
              style={{
                fontSize: '0.7rem',
                backgroundColor: 'rgba(6, 182, 212, 0.2)',
                color: 'var(--cyan-hover)',
                padding: '2px 8px',
                borderRadius: '10px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span className="pulse-dot live" style={{ width: '6px', height: '6px' }} />
              Reasoning Active
            </span>
          ) : (
            <span
              style={{
                fontSize: '0.7rem',
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                color: 'var(--status-go)',
                padding: '2px 8px',
                borderRadius: '10px',
              }}
            >
              ✓ Consensus Reached
            </span>
          )}
        </div>

        <button
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-dim)',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          {collapsed ? <Maximize2 size={15} /> : <Minimize2 size={15} />}
        </button>
      </div>

      {statusMessage && !collapsed && (
        <div
          style={{
            fontSize: '0.75rem',
            color: 'var(--cyan-primary)',
            marginTop: '8px',
            padding: '4px 8px',
            backgroundColor: 'rgba(6, 182, 212, 0.08)',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <Layers size={13} />
          <span>{statusMessage}</span>
        </div>
      )}

      {!collapsed && (
        <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {order.map((key) => {
            const catalog = AGENT_CATALOG[key];
            const trace = traces.find((t) => t.agent === key);
            const status = trace?.status || (isRunning ? 'pending' : 'skipped');

            let statusIcon = <Clock size={14} color="var(--text-dim)" />;
            let statusLabel = 'Queued';
            let statusColor = 'var(--text-dim)';

            if (status === 'completed') {
              statusIcon = <CheckCircle2 size={14} color="var(--status-go)" />;
              statusLabel = 'Done';
              statusColor = 'var(--status-go)';
            } else if (status === 'running') {
              statusIcon = <div className="pulse-dot live" style={{ width: '8px', height: '8px' }} />;
              statusLabel = 'Executing...';
              statusColor = 'var(--cyan-hover)';
            } else if (status === 'failed') {
              statusIcon = <AlertCircle size={14} color="var(--status-nogo)" />;
              statusLabel = 'Failed / Gapped';
              statusColor = 'var(--status-nogo)';
            } else if (status === 'skipped') {
              statusLabel = 'Skipped / Unused';
            }

            return (
              <div
                key={key}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 10px',
                  borderRadius: '6px',
                  backgroundColor: status === 'running' ? 'rgba(6, 182, 212, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                  border: status === 'running' ? '1px solid rgba(6, 182, 212, 0.25)' : '1px solid transparent',
                  fontSize: '0.75rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>{catalog.icon}</span>
                  <div>
                    <span style={{ fontWeight: 600, color: status === 'running' ? '#ffffff' : 'var(--text-main)' }}>
                      {catalog.label}
                    </span>
                    {trace?.details && (
                      <span style={{ marginLeft: '6px', color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                        — {trace.details}
                      </span>
                    )}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: statusColor, fontWeight: 500 }}>
                  {statusIcon}
                  <span>{statusLabel}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
