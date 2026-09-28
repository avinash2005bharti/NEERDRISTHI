import { User, AgentStatusTrace, LanguageCode } from '../types';
import { getStoredToken } from '../services/api/client';

export interface AppState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  language: LanguageCode;
  userLocation: { latitude: number; longitude: number; name?: string } | null;
  mapSelectedLocation: { latitude: number; longitude: number } | null;
  activeConversationId: string | null;
  activeAgents: AgentStatusTrace[];
  isAgentRunning: boolean;
  activeQueryStatusMessage: string | null;
}

type Listener = () => void;

class StateStore {
  private state: AppState;
  private listeners: Set<Listener> = new Set();

  constructor() {
    const savedUser = localStorage.getItem('orca_user');
    const savedLang = (localStorage.getItem('orca_lang') as LanguageCode) || 'en';
    const token = getStoredToken();

    this.state = {
      user: savedUser ? JSON.parse(savedUser) : null,
      token,
      isAuthenticated: !!token,
      language: savedLang,
      // Default coastal anchor: Mumbai Offshore / Arabian Sea
      userLocation: { latitude: 18.98, longitude: 72.82, name: 'Mumbai Offshore' },
      mapSelectedLocation: { latitude: 18.98, longitude: 72.82 },
      activeConversationId: null,
      activeAgents: [],
      isAgentRunning: false,
      activeQueryStatusMessage: null,
    };
  }

  public getState(): AppState {
    return this.state;
  }

  public setState(partial: Partial<AppState>): void {
    this.state = { ...this.state, ...partial };

    if (partial.user !== undefined) {
      if (partial.user) {
        localStorage.setItem('orca_user', JSON.stringify(partial.user));
      } else {
        localStorage.removeItem('orca_user');
      }
    }

    if (partial.language !== undefined) {
      localStorage.setItem('orca_lang', partial.language);
    }

    this.notify();
  }

  public setUser(user: User | null, token: string | null): void {
    this.setState({
      user,
      token,
      isAuthenticated: !!token,
      language: (user?.preferredLanguage as LanguageCode) || this.state.language,
    });
  }

  public setLanguage(language: LanguageCode): void {
    this.setState({ language });
  }

  public setUserLocation(location: { latitude: number; longitude: number; name?: string }): void {
    this.setState({
      userLocation: location,
      mapSelectedLocation: { latitude: location.latitude, longitude: location.longitude },
    });
  }

  public setMapSelectedLocation(location: { latitude: number; longitude: number }): void {
    this.setState({ mapSelectedLocation: location });
  }

  public setActiveConversationId(id: string | null): void {
    this.setState({ activeConversationId: id });
  }

  public setAgentRunning(running: boolean, message?: string | null): void {
    this.setState({
      isAgentRunning: running,
      activeQueryStatusMessage: message || null,
      activeAgents: running ? this.state.activeAgents : [],
    });
  }

  public updateAgentStatus(agentName: string, status: AgentStatusTrace['status'], details?: string): void {
    const existing = [...this.state.activeAgents];
    const index = existing.findIndex((a) => a.agent === agentName);
    const trace: AgentStatusTrace = {
      agent: agentName,
      status,
      timestamp: new Date().toISOString(),
      details,
    };

    if (index >= 0) {
      existing[index] = trace;
    } else {
      existing.push(trace);
    }

    this.setState({ activeAgents: existing });
  }

  public subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notify(): void {
    this.listeners.forEach((l) => l());
  }
}

export const appStore = new StateStore();
