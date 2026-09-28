export type { LanguageCode } from '../i18n/translations';

export type UserRole = 'fisherman' | 'authority' | 'disaster_manager' | 'admin';

export type VesselClass =
  | 'traditional_unmotorized'
  | 'motorized_fiberglass'
  | 'mechanized_trawler'
  | 'deep_sea_vessel';

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  vesselClass?: string;
  homePort?: string;
  registrationNumber?: string;
  preferredLanguage: string;
  preferences?: Record<string, unknown>;
  savedLocations?: SavedLocation[];
  createdAt?: string;
}

export interface SavedLocation {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  isFavorite?: boolean;
}

export interface AuthResponse {
  success: boolean;
  data: {
    user: User;
    token: string;
    expiresIn: string;
  };
  meta?: {
    requestId: string;
    timestamp: string;
  };
}

export type QueryIntent =
  | 'safety_check'
  | 'find_pfz'
  | 'route_safety'
  | 'marine_status'
  | 'authority_monitoring';

export type ResponseStatus =
  | 'completed'
  | 'partial'
  | 'clarification_required'
  | 'failed';

export type SafetyRecommendation =
  | 'GO'
  | 'GO_WITH_CAUTION'
  | 'NO_GO'
  | 'INSUFFICIENT_DATA';

export type RiskLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL' | 'UNKNOWN';

export interface LocationInput {
  name?: string;
  latitude?: number;
  longitude?: number;
}

export interface TimeWindowInput {
  start?: string;
  end?: string;
  label?: string;
}

export interface UserProfileInput {
  role?: UserRole;
  vesselClass?: string;
  language?: string;
}

export interface GeoJsonLineString {
  type: 'LineString';
  coordinates: [number, number][]; // [lon, lat]
}

export interface OrcaQueryRequest {
  conversationId?: string;
  query: string;
  intent?: QueryIntent;
  location?: LocationInput;
  timeWindow?: TimeWindowInput;
  userProfile?: UserProfileInput;
  route?: GeoJsonLineString;
}

export interface DataAvailability {
  marine: 'available' | 'unavailable' | 'stale' | 'not_requested';
  weather: 'available' | 'unavailable' | 'stale' | 'not_requested';
  tide: 'available' | 'unavailable' | 'stale' | 'not_requested';
  geospatial: 'available' | 'unavailable' | 'stale' | 'not_requested';
  semanticMemory: 'available' | 'unavailable' | 'not_requested';
}

export interface EvidenceItem {
  category: 'marine' | 'weather' | 'tide' | 'geospatial' | 'memory' | 'safety';
  name: string;
  value: unknown;
  unit?: string | null;
  observedAt?: string | null;
  validUntil?: string | null;
  retrievedAt: string;
  sourceName: string;
  sourceUrl?: string | null;
  freshness: 'fresh' | 'stale' | 'unknown' | 'cached';
}

export interface SafetyAssessment {
  triggeredRules: string[];
  missingData: string[];
  requiredNextAction: string;
}

export interface AgentStatusTrace {
  agent: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  timestamp: string;
  details?: string | null;
}

export interface OrcaTrace {
  requestId: string;
  agentStatuses: AgentStatusTrace[];
  startedAt: string;
  completedAt: string;
}

export interface OrcaQueryResponse {
  requestId: string;
  conversationId: string;
  status: ResponseStatus;
  recommendation?: SafetyRecommendation | null;
  riskLevel: RiskLevel;
  riskScore: number;
  confidenceScore: number;
  answer: string;
  language: string;
  clarificationQuestion?: string | null;
  dataAvailability: DataAvailability;
  evidence: EvidenceItem[];
  safety: SafetyAssessment;
  trace: OrcaTrace;
}

export interface Conversation {
  conversationId: string;
  userId?: string | null;
  title?: string;
  lastQueryAt?: string;
  createdAt?: string;
  messages?: ChatMessage[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  orcaResponse?: OrcaQueryResponse;
}

// Socket.IO Events
export interface SocketAgentStarted {
  requestId: string;
  conversationId: string;
  timestamp: string;
  agent: string;
  agentLabel: string;
  intent: string;
}

export interface SocketAgentProgress {
  requestId: string;
  conversationId: string;
  timestamp: string;
  agent: string;
  stage: string;
  message: string;
}

export interface SocketAgentCompleted {
  requestId: string;
  conversationId: string;
  timestamp: string;
  agent: string;
  status: string;
  summary: string;
}

export interface SocketDataUnavailable {
  requestId: string;
  conversationId: string;
  timestamp: string;
  category: string;
  providerName: string;
  reason: string;
  impactOnRecommendation: string;
}

export interface SocketClarificationRequired {
  requestId: string;
  conversationId: string;
  timestamp: string;
  question: string;
}

// Marine Map & Geospatial Types
export interface BaseMapDefinition {
  id: string;
  name: string;
  type: string;
  url?: string;
  attribution: string;
  max_zoom?: number;
  requires_token?: boolean;
}

export interface MarineLayerDefinition {
  id: string;
  name: string;
  default: boolean;
  category: string;
}

export interface MarineMapConfig {
  service: string;
  version: string;
  timestamp: string;
  demo_mode: boolean;
  default_center: [number, number]; // [lat, lon]
  default_zoom: number;
  base_maps: BaseMapDefinition[];
  marine_layers: MarineLayerDefinition[];
  providers_status?: Record<string, string>;
}

export interface GeoJsonGeometry {
  type: 'Point' | 'LineString' | 'Polygon' | 'MultiPolygon';
  coordinates: any;
}

export interface GeoJsonFeature {
  type: 'Feature';
  geometry: GeoJsonGeometry;
  properties: Record<string, any>;
}

export interface GeoJsonFeatureCollection {
  type: 'FeatureCollection';
  metadata?: {
    layer?: string;
    center?: { latitude: number; longitude: number };
    status?: string;
    is_live?: boolean;
    source?: string;
    timestamp?: string;
    [key: string]: any;
  };
  features: GeoJsonFeature[];
  status?: string;
  is_live?: boolean;
  reason?: string;
}

export interface SpotOverview {
  status: string;
  is_live: boolean;
  source: string;
  coordinates: { latitude: number; longitude: number };
  weather: {
    temperature_c: number;
    wind_speed_knots: number;
    wind_direction_deg: number;
    visibility_km: number;
    condition: string;
  };
  marine: {
    significant_wave_height_m: number;
    dominant_period_s: number;
    sea_surface_temp_c: number;
    chlorophyll_mg_m3: number;
    tide_height_m: number;
    tide_state: string;
  };
  safety: {
    risk_level: string;
    recommendation: string;
    nearest_pfz_km: number;
  };
  timestamp: string;
}

export interface MarineAlert {
  id?: string;
  title: string;
  description?: string;
  severity: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW' | 'WARNING';
  category: string;
  source: string;
  issued_at: string;
  valid_until?: string;
  affected_area?: {
    name?: string;
    latitude?: number;
    longitude?: number;
    radius_km?: number;
  };
}

export interface RouteAnalysisResult {
  status: string;
  route_summary: {
    total_distance_km: number;
    waypoint_count: number;
    leg_count: number;
    buffer_km: number;
  };
  legs: Array<{
    leg_index: number;
    from_coord: [number, number];
    to_coord: [number, number];
    distance_km: number;
    bearing_deg: number;
  }>;
  hazard_intersections: any[];
  is_safe: boolean;
  recommendation: 'GO' | 'NO_GO';
  timestamp: string;
}
