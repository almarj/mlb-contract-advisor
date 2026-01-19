/**
 * API client for MLB Contract Advisor backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface PredictionRequest {
  name: string;
  position: string;
  age: number;
  war_3yr: number;
  wrc_plus_3yr?: number;
  avg_3yr?: number;
  obp_3yr?: number;
  slg_3yr?: number;
  hr_3yr?: number;
  era_3yr?: number;
  fip_3yr?: number;
  k_9_3yr?: number;
  bb_9_3yr?: number;
  ip_3yr?: number;
  avg_exit_velo?: number;
  barrel_rate?: number;
  max_exit_velo?: number;
  hard_hit_pct?: number;
  chase_rate?: number;
  whiff_rate?: number;
  // Pitcher Statcast metrics (percentiles 0-100)
  fb_velocity?: number;
  fb_spin?: number;
  xera?: number;
  k_percent?: number;
  bb_percent?: number;
  whiff_percent_pitcher?: number;
  chase_percent_pitcher?: number;
}

export interface ComparablePlayer {
  name: string;
  position: string;
  year_signed: number;
  age_at_signing: number;
  aav: number;
  length: number;
  war_3yr: number;
  similarity_score: number;
  is_extension: boolean;
}

export interface PredictionResponse {
  player_name: string;
  position: string;
  predicted_aav: number;
  predicted_aav_low: number;
  predicted_aav_high: number;
  predicted_length: number;
  actual_aav: number | null;
  actual_length: number | null;
  // Stats at time of signing (pre-signing 3yr averages)
  signing_war_3yr: number | null;
  signing_wrc_plus_3yr: number | null;
  signing_era_3yr: number | null;
  // Recent performance stats (last 3 years)
  recent_war_3yr: number | null;
  recent_wrc_plus_3yr: number | null;
  recent_era_3yr: number | null;
  // Prediction based on recent performance
  predicted_aav_recent: number | null;
  confidence_score: number;
  comparables: ComparablePlayer[];
  comparables_recent: ComparablePlayer[];
  feature_importance: Record<string, number>;
  model_accuracy: number;
}

export interface PlayerStats {
  name: string;
  position: string;
  // For signed players (from Contract table)
  age_at_signing: number | null;
  year_signed: number | null;
  // For prospects (from Player table)
  current_age: number | null;
  last_season: number | null;
  // Stats
  war_3yr: number | null;
  wrc_plus_3yr: number | null;
  avg_3yr: number | null;
  obp_3yr: number | null;
  slg_3yr: number | null;
  hr_3yr: number | null;
  era_3yr: number | null;
  fip_3yr: number | null;
  k_9_3yr: number | null;
  bb_9_3yr: number | null;
  ip_3yr: number | null;
  avg_exit_velo: number | null;
  barrel_rate: number | null;
  max_exit_velo: number | null;
  hard_hit_pct: number | null;
  chase_rate: number | null;
  whiff_rate: number | null;
  // Pitcher Statcast
  fb_velocity: number | null;
  fb_spin: number | null;
  xera: number | null;
  k_percent: number | null;
  bb_percent: number | null;
  whiff_percent_pitcher: number | null;
  chase_percent_pitcher: number | null;
}

export interface PlayerSearchResult {
  id: number;
  name: string;
  position: string;
  team: string | null;
  is_pitcher: boolean;
  has_contract: boolean;
  stats: PlayerStats | null;
}

export interface ContractRecord {
  id: number;
  player_name: string;
  position: string;
  year_signed: number;
  age_at_signing: number;
  aav: number;
  total_value: number;
  length: number;
  war_3yr: number | null;
}

export interface ContractListResponse {
  contracts: ContractRecord[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// Year-by-year stats types
export interface BatterYearlyStats {
  season: number;
  team: string;
  war: number | null;
  wrc_plus: number | null;
  avg: number | null;
  obp: number | null;
  slg: number | null;
  hr: number | null;
  rbi: number | null;
  sb: number | null;
  runs: number | null;
  hits: number | null;
  games: number | null;
  pa: number | null;
}

export interface PitcherYearlyStats {
  season: number;
  team: string;
  war: number | null;
  era: number | null;
  fip: number | null;
  k_9: number | null;
  bb_9: number | null;
  ip: number | null;
  games: number | null;
  wins: number | null;
  losses: number | null;
}

export interface PlayerYearlyStatsResponse {
  player_name: string;
  position: string;
  is_pitcher: boolean;
  seasons: number[];
  batter_stats: BatterYearlyStats[] | null;
  pitcher_stats: PitcherYearlyStats[] | null;
}

export interface ContractSummary {
  total_contracts: number;
  year_min: number;
  year_max: number;
  aav_min: number;
  aav_max: number;
  unique_positions: number;
}

// API Functions
export async function createPrediction(data: PredictionRequest): Promise<PredictionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/predictions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Prediction failed');
  }

  return response.json();
}

export async function searchPlayers(query: string): Promise<PlayerSearchResult[]> {
  if (query.length < 2) return [];

  const response = await fetch(`${API_BASE_URL}/api/v1/players/search?q=${encodeURIComponent(query)}`);

  if (!response.ok) {
    throw new Error('Search failed');
  }

  const data = await response.json();
  return data.results;
}

export async function getContracts(params: {
  page?: number;
  per_page?: number;
  position?: string;
  year_min?: number;
  year_max?: number;
  aav_min?: number;
  aav_max?: number;
  war_min?: number;
  war_max?: number;
  length_min?: number;
  length_max?: number;
  search?: string;
  sort_by?: string;
  sort_order?: string;
}): Promise<ContractListResponse> {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value));
    }
  });

  const response = await fetch(`${API_BASE_URL}/api/v1/contracts?${searchParams}`);

  if (!response.ok) {
    throw new Error('Failed to fetch contracts');
  }

  return response.json();
}

export async function checkHealth(): Promise<{ status: string; models_loaded: boolean }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.json();
}

export async function getContractPlayerStats(contractId: number): Promise<PlayerYearlyStatsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/contracts/${contractId}/stats`);

  if (!response.ok) {
    throw new Error('Failed to fetch player stats');
  }

  return response.json();
}

export async function getContractsSummary(): Promise<ContractSummary> {
  const response = await fetch(`${API_BASE_URL}/api/v1/contracts/summary`);

  if (!response.ok) {
    throw new Error('Failed to fetch contracts summary');
  }

  return response.json();
}

// Utility functions
export function formatCurrency(value: number): string {
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  return `$${value.toLocaleString()}`;
}

export function formatAAV(value: number): string {
  return `$${(value / 1_000_000).toFixed(1)}M`;
}

export const PITCHER_POSITIONS = ['SP', 'RP', 'P', 'CL'];

export function isPitcher(position: string): boolean {
  return PITCHER_POSITIONS.includes(position.toUpperCase());
}

export const POSITIONS = [
  { value: 'SP', label: 'Starting Pitcher' },
  { value: 'RP', label: 'Relief Pitcher' },
  { value: 'C', label: 'Catcher' },
  { value: '1B', label: 'First Base' },
  { value: '2B', label: 'Second Base' },
  { value: '3B', label: 'Third Base' },
  { value: 'SS', label: 'Shortstop' },
  { value: 'LF', label: 'Left Field' },
  { value: 'CF', label: 'Center Field' },
  { value: 'RF', label: 'Right Field' },
  { value: 'DH', label: 'Designated Hitter' },
];
