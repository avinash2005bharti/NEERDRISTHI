import { fastApiClient } from '../clients/fastApiClient.js';

/**
 * Marine data controller — proxies direct marine data requests from frontend
 * through Node server to FastAPI agent core.
 * No agent execution; returns raw provider data.
 */
export class MarineController {
  /**
   * GET /api/v1/marine/weather?latitude=&longitude=
   */
  async getWeather(req, res, next) {
    try {
      const { latitude, longitude } = req.query;
      if (!latitude || !longitude) {
        res.status(400).json({ success: false, error: 'latitude and longitude are required' });
        return;
      }
      const result = await fastApiClient.getMarineWeather(
        parseFloat(latitude),
        parseFloat(longitude)
      );
      res.status(200).json({
        success: true,
        data: result,
        meta: { requestId: req.id || 'unknown', timestamp: new Date().toISOString() },
      });
    } catch (err) {
      next(err);
    }
  }

  /**
   * GET /api/v1/marine/ocean?latitude=&longitude=
   */
  async getOceanState(req, res, next) {
    try {
      const { latitude, longitude } = req.query;
      if (!latitude || !longitude) {
        res.status(400).json({ success: false, error: 'latitude and longitude are required' });
        return;
      }
      const result = await fastApiClient.getOceanState(
        parseFloat(latitude),
        parseFloat(longitude)
      );
      res.status(200).json({
        success: true,
        data: result,
        meta: { requestId: req.id || 'unknown', timestamp: new Date().toISOString() },
      });
    } catch (err) {
      next(err);
    }
  }

  /**
   * GET /api/v1/marine/pfz?latitude=&longitude=
   */
  async getPFZ(req, res, next) {
    try {
      const { latitude, longitude } = req.query;
      if (!latitude || !longitude) {
        res.status(400).json({ success: false, error: 'latitude and longitude are required' });
        return;
      }
      const result = await fastApiClient.getPFZData(
        parseFloat(latitude),
        parseFloat(longitude)
      );
      res.status(200).json({
        success: true,
        data: result,
        meta: { requestId: req.id || 'unknown', timestamp: new Date().toISOString() },
      });
    } catch (err) {
      next(err);
    }
  }

  /**
   * GET /api/v1/marine/alerts?latitude=&longitude= (optional coords)
   */
  async getAlerts(req, res, next) {
    try {
      const { latitude, longitude } = req.query;
      const lat = latitude ? parseFloat(latitude) : undefined;
      const lon = longitude ? parseFloat(longitude) : undefined;
      const result = await fastApiClient.getMarineAlerts(lat, lon);
      res.status(200).json({
        success: true,
        data: result,
        meta: { requestId: req.id || 'unknown', timestamp: new Date().toISOString() },
      });
    } catch (err) {
      next(err);
    }
  }

  /**
   * GET /api/v1/marine/zones?latitude=&longitude=&radius_km=
   */
  async getZones(req, res, next) {
    try {
      const { latitude, longitude, radius_km } = req.query;
      const lat = latitude ? parseFloat(latitude) : undefined;
      const lon = longitude ? parseFloat(longitude) : undefined;
      const radius = radius_km ? parseFloat(radius_km) : 100;
      const result = await fastApiClient.getMarineZones(lat, lon, radius);
      res.status(200).json({
        success: true,
        data: result,
        meta: { requestId: req.id || 'unknown', timestamp: new Date().toISOString() },
      });
    } catch (err) {
      next(err);
    }
  }

  /**
   * POST /api/v1/marine/route-analysis
   */
  async getRouteAnalysis(req, res, next) {
    try {
      const { waypoints, vesselClass, bufferKm } = req.body;
      if (!Array.isArray(waypoints) || waypoints.length < 2) {
        res.status(400).json({ success: false, error: 'waypoints array of at least 2 points is required' });
        return;
      }
      const result = await fastApiClient.executeRouteAnalysis(waypoints, vesselClass, bufferKm);
      res.status(200).json({
        success: true,
        data: result,
      });
    } catch (err) {
      next(err);
    }
  }

  /**
   * POST /api/v1/marine/risk-analysis
   */
  async getRiskAnalysis(req, res, next) {
    try {
      const { vesselClass, latitude, longitude } = req.body;
      if (latitude === undefined || longitude === undefined) {
        res.status(400).json({ success: false, error: 'latitude and longitude are required' });
        return;
      }
      const result = await fastApiClient.executeRiskAnalysis(
        vesselClass || 'motorized_fiberglass',
        parseFloat(latitude),
        parseFloat(longitude)
      );
      res.status(200).json({
        success: true,
        data: result,
      });
    } catch (err) {
      next(err);
    }
  }

  async getMapConfig(req, res, next) {
    try {
      const result = await fastApiClient.getMarineMapConfig();
      res.status(200).json({ success: true, data: result });
    } catch (err) { next(err); }
  }

  async getSST(req, res, next) {
    try {
      const result = await fastApiClient.getMarineLayer('sst', req.query);
      res.status(200).json(result);
    } catch (err) { next(err); }
  }

  async getChlorophyll(req, res, next) {
    try {
      const result = await fastApiClient.getMarineLayer('chlorophyll', req.query);
      res.status(200).json(result);
    } catch (err) { next(err); }
  }

  async getWaves(req, res, next) {
    try {
      const result = await fastApiClient.getMarineLayer('waves', req.query);
      res.status(200).json(result);
    } catch (err) { next(err); }
  }

  async getWind(req, res, next) {
    try {
      const result = await fastApiClient.getMarineLayer('wind', req.query);
      res.status(200).json(result);
    } catch (err) { next(err); }
  }

  async getTides(req, res, next) {
    try {
      const result = await fastApiClient.getMarineLayer('tides', req.query);
      res.status(200).json(result);
    } catch (err) { next(err); }
  }

  async getRisk(req, res, next) {
    try {
      const result = await fastApiClient.getMarineLayer('risk', req.query);
      res.status(200).json(result);
    } catch (err) { next(err); }
  }

  async getOverview(req, res, next) {
    try {
      const result = await fastApiClient.getMarineLayer('overview', req.query);
      res.status(200).json(result);
    } catch (err) { next(err); }
  }

  async getMapPfz(req, res, next) {
    try {
      const result = await fastApiClient.getMarineLayer('pfz', req.query);
      res.status(200).json(result);
    } catch (err) { next(err); }
  }

  async getMapZones(req, res, next) {
    try {
      const result = await fastApiClient.getMarineLayer('zones', req.query);
      res.status(200).json(result);
    } catch (err) { next(err); }
  }

  async getSatellite(req, res, next) {
    try {
      const { latitude, longitude } = req.query;
      if (!latitude || !longitude) {
        res.status(400).json({ success: false, error: 'latitude and longitude are required' });
        return;
      }
      const result = await fastApiClient.getSatelliteObservations(
        parseFloat(latitude),
        parseFloat(longitude)
      );
      res.status(200).json({
        success: true,
        data: result,
        meta: { requestId: req.id || 'unknown', timestamp: new Date().toISOString() },
      });
    } catch (err) { next(err); }
  }

  async getFishingZoneEstimate(req, res, next) {
    try {
      const { latitude, longitude } = req.query;
      if (!latitude || !longitude) {
        res.status(400).json({ success: false, error: 'latitude and longitude are required' });
        return;
      }
      const result = await fastApiClient.getFishingZoneEstimate(
        parseFloat(latitude),
        parseFloat(longitude)
      );
      res.status(200).json({
        success: true,
        data: result,
        meta: { requestId: req.id || 'unknown', timestamp: new Date().toISOString() },
      });
    } catch (err) { next(err); }
  }
}

export const marineController = new MarineController();
