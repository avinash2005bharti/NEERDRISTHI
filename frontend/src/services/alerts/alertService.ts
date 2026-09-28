import { apiRequest } from '../api/client';
import { MarineAlert } from '../../types';

export interface EmergencyAlertPayload {
  latitude?: number;
  longitude?: number;
  locationName?: string;
  vesselName?: string;
  vesselRegistration?: string;
  emergencyType: string;
  crewCount?: number;
  contactPhone?: string;
  notes?: string;
  userName?: string;
}

export const alertService = {
  async getAlerts(latitude?: number, longitude?: number, severity?: string): Promise<MarineAlert[]> {
    const params = new URLSearchParams();
    if (latitude !== undefined) params.append('latitude', latitude.toString());
    if (longitude !== undefined) params.append('longitude', longitude.toString());
    if (severity) params.append('severity', severity);

    const query = params.toString() ? `?${params.toString()}` : '';
    const res = await apiRequest<{ success: boolean; data: MarineAlert[] }>(`/alerts${query}`);
    return res.data || [];
  },

  async getMarineAlerts(latitude?: number, longitude?: number): Promise<MarineAlert[]> {
    const params = new URLSearchParams();
    if (latitude !== undefined) params.append('latitude', latitude.toString());
    if (longitude !== undefined) params.append('longitude', longitude.toString());

    const query = params.toString() ? `?${params.toString()}` : '';
    const res = await apiRequest<{ success: boolean; data: { alerts?: MarineAlert[] } }>(`/marine/alerts${query}`);
    return res.data?.alerts || [];
  },

  /**
   * Broadcast real-time emergency SOS distress beacon
   */
  async sendEmergencyAlert(payload: EmergencyAlertPayload): Promise<MarineAlert> {
    const res = await apiRequest<{ success: boolean; data: MarineAlert; message: string }>('/alerts/emergency', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return res.data;
  },
};
