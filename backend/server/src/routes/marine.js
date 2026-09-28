import { Router } from 'express';
import { marineController } from '../controllers/marineController.js';
import { optionalAuthenticateJwt } from '../middleware/auth.js';

export const marineRouter = Router();

// Optional auth — marine data is accessible without login for basic advisory
marineRouter.use(optionalAuthenticateJwt);

// GET /api/v1/marine/weather?latitude=&longitude=
marineRouter.get('/weather', (req, res, next) => marineController.getWeather(req, res, next));

// GET /api/v1/marine/ocean?latitude=&longitude=
marineRouter.get('/ocean', (req, res, next) => marineController.getOceanState(req, res, next));

// GET /api/v1/marine/pfz?latitude=&longitude=
marineRouter.get('/pfz', (req, res, next) => marineController.getPFZ(req, res, next));

// GET /api/v1/marine/alerts?latitude=&longitude= (coords optional)
marineRouter.get('/alerts', (req, res, next) => marineController.getAlerts(req, res, next));

// GET /api/v1/marine/zones?latitude=&longitude=&radius_km=
marineRouter.get('/zones', (req, res, next) => marineController.getZones(req, res, next));

// POST /api/v1/marine/route-analysis
marineRouter.post('/route-analysis', (req, res, next) => marineController.getRouteAnalysis(req, res, next));

// POST /api/v1/marine/risk-analysis
marineRouter.post('/risk-analysis', (req, res, next) => marineController.getRiskAnalysis(req, res, next));

// ─── HD Marine Map & Ocean Data Layer Endpoints (SIH26176) ───
// GET /api/v1/marine/map/config
marineRouter.get('/map/config', (req, res, next) => marineController.getMapConfig(req, res, next));

// GET /api/v1/marine/sst?lat=&lon=&bbox=&zoom=
marineRouter.get('/sst', (req, res, next) => marineController.getSST(req, res, next));

// GET /api/v1/marine/chlorophyll?lat=&lon=&bbox=&zoom=
marineRouter.get('/chlorophyll', (req, res, next) => marineController.getChlorophyll(req, res, next));

// GET /api/v1/marine/waves?lat=&lon=&bbox=&zoom=
marineRouter.get('/waves', (req, res, next) => marineController.getWaves(req, res, next));

// GET /api/v1/marine/wind?lat=&lon=&bbox=&zoom=
marineRouter.get('/wind', (req, res, next) => marineController.getWind(req, res, next));

// GET /api/v1/marine/tides?lat=&lon=
marineRouter.get('/tides', (req, res, next) => marineController.getTides(req, res, next));

// GET /api/v1/marine/risk?lat=&lon=&bbox=
marineRouter.get('/risk', (req, res, next) => marineController.getRisk(req, res, next));

// GET /api/v1/marine/overview?lat=&lon=
marineRouter.get('/overview', (req, res, next) => marineController.getOverview(req, res, next));

// GET /api/v1/marine/map/pfz — GeoJSON PFZ overlay (distinct from point /pfz)
marineRouter.get('/map/pfz', (req, res, next) => marineController.getMapPfz(req, res, next));

// GET /api/v1/marine/map/zones — GeoJSON restricted zones overlay
marineRouter.get('/map/zones', (req, res, next) => marineController.getMapZones(req, res, next));

// GET /api/v1/marine/satellite?latitude=&longitude=
marineRouter.get('/satellite', (req, res, next) => marineController.getSatellite(req, res, next));

// GET /api/v1/marine/fishing-zone?latitude=&longitude=
marineRouter.get('/fishing-zone', (req, res, next) => marineController.getFishingZoneEstimate(req, res, next));
