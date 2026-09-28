import { v4 as uuidv4 } from 'uuid';
import { getDb } from '../config/database.js';
import { fastApiClient } from '../clients/fastApiClient.js';
import { logger } from '../utils/logger.js';
import { orcaEventEmitter } from '../sockets/eventEmitter.js';

// Default initial official alerts seed if no alerts are in DB
const DEFAULT_OFFICIAL_ALERTS = [
  {
    alertId: 'incois-alert-swell-01',
    severity: 'caution',
    title: 'High Swell Wave Alert - Arabian Sea Coast',
    summary: 'High waves (2.5 – 3.2 m) expected during evening spring tide along Maharashtra and Gujarat coastlines. Small motorized fiber crafts advised to exercise utmost caution.',
    issuedBy: 'INCOIS Marine Forecast Division',
    timestamp: new Date().toISOString(),
    affectedZone: 'West Coast India (Gujarat to Goa)',
    actions: ['Secure boat moorings', 'Avoid low-lying rocky jetties', 'Monitor VHF Channel 16'],
    isActive: true,
    createdAt: new Date().toISOString(),
  },
  {
    alertId: 'cwc-alert-depression-02',
    severity: 'safe',
    title: 'Seasonal Depression Notice - Central Bay of Bengal',
    summary: 'Low pressure system tracked 420 km ESE of Chennai. Current trajectory indicates no landfall threat to coastal Tamil Nadu within the next 48 hours.',
    issuedBy: 'IMD Cyclone Warning Centre',
    timestamp: new Date().toISOString(),
    affectedZone: 'Southeast Coastal Sector',
    actions: ['Standard fishing operations permitted with normal precautions', 'Verify GPS before departure'],
    isActive: true,
    createdAt: new Date().toISOString(),
  }
];

export class AlertService {
  async getActiveAlerts(latitude, longitude, severity) {
    const db = getDb();
    let dbAlerts = [];

    if (db) {
      try {
        const filter = { isActive: true };
        if (severity && severity !== 'all') {
          filter.severity = severity;
        }
        dbAlerts = await db.collection('alerts').find(filter).toArray();

        // Seed default official alerts if collection is empty
        if (dbAlerts.length === 0) {
          await db.collection('alerts').insertMany(DEFAULT_OFFICIAL_ALERTS);
          dbAlerts = DEFAULT_OFFICIAL_ALERTS;
        }
      } catch (err) {
        logger.warn({ err }, 'Error querying MongoDB alerts collection');
        dbAlerts = DEFAULT_OFFICIAL_ALERTS;
      }
    } else {
      dbAlerts = DEFAULT_OFFICIAL_ALERTS;
    }

    // Try fetching any live alerts from FastAPI marine alert provider
    try {
      const liveData = await fastApiClient.getMarineAlerts(latitude, longitude);
      if (liveData && Array.isArray(liveData.alerts) && liveData.alerts.length > 0) {
        for (const item of liveData.alerts) {
          if (!dbAlerts.some((a) => a.title === item.title)) {
            dbAlerts.unshift({
              alertId: item.id || `live-${uuidv4().slice(0, 8)}`,
              severity: item.severity || 'caution',
              title: item.title,
              summary: item.summary || item.description,
              issuedBy: item.issued_by || 'INCOIS / IMD',
              timestamp: item.timestamp || new Date().toISOString(),
              affectedZone: item.affected_zone || 'Indian Coastal Waters',
              actions: item.actions || ['Exercise caution'],
              isActive: true,
              createdAt: new Date().toISOString(),
            });
          }
        }
      }
    } catch {
      // Keep MongoDB / cached alerts
    }

    if (severity && severity !== 'all') {
      return dbAlerts.filter((a) => a.severity === severity);
    }
    return dbAlerts;
  }

  async createAlert(alertData) {
    const db = getDb();
    const doc = {
      alertId: alertData.alertId || `alert-${uuidv4()}`,
      severity: alertData.severity || 'caution',
      title: alertData.title || 'Marine Hazard Advisory',
      summary: alertData.summary || '',
      issuedBy: alertData.issuedBy || 'Maritime Safety Authority',
      timestamp: alertData.timestamp || new Date().toISOString(),
      affectedZone: alertData.affectedZone || 'Coastal Waters',
      actions: alertData.actions || ['Monitor VHF Channel 16'],
      isActive: true,
      createdAt: new Date().toISOString(),
    };

    if (db) {
      await db.collection('alerts').insertOne(doc);
    }
    return doc;
  }

  async createEmergencyAlert(emergencyData) {
    const db = getDb();
    const alertId = `sos-${uuidv4().slice(0, 8)}`;
    const lat = emergencyData.latitude !== undefined ? Number(emergencyData.latitude) : null;
    const lon = emergencyData.longitude !== undefined ? Number(emergencyData.longitude) : null;

    const locDesc = (lat !== null && lon !== null)
      ? `${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E`
      : (emergencyData.locationName || 'Indian Coastal Waters');

    const vesselDesc = emergencyData.vesselName || emergencyData.vesselRegistration || 'Coastal Craft';
    const typeLabel = emergencyData.emergencyType || 'Vessel in Distress';

    const doc = {
      alertId,
      severity: 'CRITICAL',
      type: 'EMERGENCY_SOS',
      title: `🚨 MAYDAY / DISTRESS SOS: ${vesselDesc} (${typeLabel})`,
      summary: `Emergency distress beacon activated at ${locDesc}. Nature of emergency: ${typeLabel}. Crew count: ${emergencyData.crewCount || 1}. Contact: ${emergencyData.contactPhone || 'VHF Ch 16'}. Immediate search & rescue assistance requested. Notes: ${emergencyData.notes || 'None provided'}`,
      issuedBy: emergencyData.userName ? `SOS Beacon - ${emergencyData.userName}` : 'Maritime Distress Beacon',
      timestamp: new Date().toISOString(),
      affectedZone: `${locDesc} - Sector Maritime Geofence`,
      actions: [
        'Contact Indian Coast Guard MRCC Helpline: 1554',
        'VHF Emergency Channel 16 Broadcast Active',
        'Coastal Police Emergency: 1093',
        'All vessels in vicinity instructed to maintain lookout and render assistance under SOLAS convention'
      ],
      details: {
        latitude: lat,
        longitude: lon,
        vesselName: emergencyData.vesselName || '',
        vesselRegistration: emergencyData.vesselRegistration || '',
        emergencyType: typeLabel,
        crewCount: emergencyData.crewCount || 1,
        contactPhone: emergencyData.contactPhone || '',
        notes: emergencyData.notes || '',
      },
      isActive: true,
      createdAt: new Date().toISOString(),
    };

    if (db) {
      try {
        await db.collection('alerts').insertOne(doc);
      } catch (err) {
        logger.error({ err }, 'Failed to persist emergency SOS in MongoDB');
      }
    }

    // Broadcast system-wide via WebSocket to all listening clients
    try {
      orcaEventEmitter.emitEmergencyAlert(doc);
    } catch (wsErr) {
      logger.warn({ wsErr }, 'WebSocket emission error for emergency alert');
    }

    logger.warn({ alertId, locDesc, vesselDesc }, '🚨 EMERGENCY SOS BEACON CREATED AND BROADCAST');
    return doc;
  }
}

export const alertService = new AlertService();
