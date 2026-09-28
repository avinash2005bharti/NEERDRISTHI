import { useState, useCallback } from 'react';
import { appStore } from '../stores/appState';

export interface GeolocationState {
  loading: boolean;
  error: string | null;
  latitude: number;
  longitude: number;
}

export function useGeolocation() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requestLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser');
      return;
    }

    setLoading(true);
    setError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLoading(false);
        const lat = parseFloat(position.coords.latitude.toFixed(4));
        const lon = parseFloat(position.coords.longitude.toFixed(4));

        appStore.setUserLocation({
          latitude: lat,
          longitude: lon,
          name: 'My GPS Location',
        });
      },
      (err) => {
        setLoading(false);
        let message = 'Could not retrieve your location.';
        if (err.code === err.PERMISSION_DENIED) {
          message = 'Location permission was denied. Defaulting to coastal anchor.';
        } else if (err.code === err.POSITION_UNAVAILABLE) {
          message = 'Location information is currently unavailable.';
        } else if (err.code === err.TIMEOUT) {
          message = 'Location request timed out.';
        }
        setError(message);
        // Fallback default coordinates
        appStore.setUserLocation({
          latitude: 18.98,
          longitude: 72.82,
          name: 'Mumbai Coastal Anchor (Default)',
        });
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000,
      }
    );
  }, []);

  return { requestLocation, loading, error };
}
