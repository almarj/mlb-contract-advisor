'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import {
  PredictionRequest,
  PredictionResponse,
  PlayerSearchResult,
  createPrediction,
  searchPlayers,
  isPitcher,
  formatAAV,
} from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface PlayerState {
  searchQuery: string;
  searchResults: PlayerSearchResult[];
  showDropdown: boolean;
  isSearching: boolean;
  selectedPlayer: PlayerSearchResult | null;
  prediction: PredictionResponse | null;
  isLoading: boolean;
  error: string | null;
  showDetails: boolean;
}

const initialPlayerState: PlayerState = {
  searchQuery: '',
  searchResults: [],
  showDropdown: false,
  isSearching: false,
  selectedPlayer: null,
  prediction: null,
  isLoading: false,
  error: null,
  showDetails: false,
};

export default function ComparePage() {
  const [player1, setPlayer1] = useState<PlayerState>(initialPlayerState);
  const [player2, setPlayer2] = useState<PlayerState>(initialPlayerState);

  const dropdown1Ref = useRef<HTMLDivElement>(null);
  const dropdown2Ref = useRef<HTMLDivElement>(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdown1Ref.current && !dropdown1Ref.current.contains(e.target as Node)) {
        setPlayer1(prev => ({ ...prev, showDropdown: false }));
      }
      if (dropdown2Ref.current && !dropdown2Ref.current.contains(e.target as Node)) {
        setPlayer2(prev => ({ ...prev, showDropdown: false }));
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced search for player 1
  useEffect(() => {
    if (player1.searchQuery.length < 2) {
      setPlayer1(prev => ({ ...prev, searchResults: [], showDropdown: false }));
      return;
    }

    const timer = setTimeout(async () => {
      setPlayer1(prev => ({ ...prev, isSearching: true }));
      try {
        const results = await searchPlayers(player1.searchQuery);
        setPlayer1(prev => ({ ...prev, searchResults: results, showDropdown: results.length > 0, isSearching: false }));
      } catch {
        setPlayer1(prev => ({ ...prev, isSearching: false }));
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [player1.searchQuery]);

  // Debounced search for player 2
  useEffect(() => {
    if (player2.searchQuery.length < 2) {
      setPlayer2(prev => ({ ...prev, searchResults: [], showDropdown: false }));
      return;
    }

    const timer = setTimeout(async () => {
      setPlayer2(prev => ({ ...prev, isSearching: true }));
      try {
        const results = await searchPlayers(player2.searchQuery);
        setPlayer2(prev => ({ ...prev, searchResults: results, showDropdown: results.length > 0, isSearching: false }));
      } catch {
        setPlayer2(prev => ({ ...prev, isSearching: false }));
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [player2.searchQuery]);

  const handlePlayerSelect = async (
    player: PlayerSearchResult,
    setPlayerState: React.Dispatch<React.SetStateAction<PlayerState>>
  ) => {
    setPlayerState(prev => ({
      ...prev,
      searchQuery: player.name,
      selectedPlayer: player,
      showDropdown: false,
      isLoading: true,
      error: null,
    }));

    // Build prediction request from player stats
    if (player.stats) {
      const stats = player.stats;
      const currentYear = new Date().getFullYear();

      let estimatedAge: number;
      if (player.has_contract && stats.age_at_signing) {
        estimatedAge = stats.age_at_signing;
      } else if (stats.current_age && stats.last_season) {
        estimatedAge = stats.current_age + (currentYear - stats.last_season);
      } else {
        estimatedAge = 28;
      }

      const request: PredictionRequest = {
        name: player.name,
        position: stats.position,
        age: Math.min(Math.max(estimatedAge, 18), 45),
        war_3yr: stats.war_3yr ?? 3.0,
        wrc_plus_3yr: stats.wrc_plus_3yr ?? undefined,
        avg_3yr: stats.avg_3yr ?? undefined,
        obp_3yr: stats.obp_3yr ?? undefined,
        slg_3yr: stats.slg_3yr ?? undefined,
        hr_3yr: stats.hr_3yr ?? undefined,
        era_3yr: stats.era_3yr ?? undefined,
        fip_3yr: stats.fip_3yr ?? undefined,
        k_9_3yr: stats.k_9_3yr ?? undefined,
        bb_9_3yr: stats.bb_9_3yr ?? undefined,
        ip_3yr: stats.ip_3yr ?? undefined,
        avg_exit_velo: stats.avg_exit_velo ?? undefined,
        barrel_rate: stats.barrel_rate ?? undefined,
        max_exit_velo: stats.max_exit_velo ?? undefined,
        hard_hit_pct: stats.hard_hit_pct ?? undefined,
        chase_rate: stats.chase_rate ?? undefined,
        whiff_rate: stats.whiff_rate ?? undefined,
        fb_velocity: stats.fb_velocity ?? undefined,
        fb_spin: stats.fb_spin ?? undefined,
        xera: stats.xera ?? undefined,
        k_percent: stats.k_percent ?? undefined,
        bb_percent: stats.bb_percent ?? undefined,
        whiff_percent_pitcher: stats.whiff_percent_pitcher ?? undefined,
        chase_percent_pitcher: stats.chase_percent_pitcher ?? undefined,
      };

      // Clean up based on position
      const playerIsPitcher = isPitcher(stats.position);
      if (playerIsPitcher) {
        delete request.wrc_plus_3yr;
        delete request.avg_3yr;
        delete request.obp_3yr;
        delete request.slg_3yr;
        delete request.hr_3yr;
        delete request.avg_exit_velo;
        delete request.barrel_rate;
        delete request.max_exit_velo;
        delete request.hard_hit_pct;
        delete request.chase_rate;
        delete request.whiff_rate;
        if (!request.era_3yr) request.era_3yr = 3.50;
        if (!request.fip_3yr) request.fip_3yr = 3.50;
        if (!request.k_9_3yr) request.k_9_3yr = 9.0;
        if (!request.bb_9_3yr) request.bb_9_3yr = 2.5;
        if (!request.ip_3yr) request.ip_3yr = 180;
      } else {
        delete request.era_3yr;
        delete request.fip_3yr;
        delete request.k_9_3yr;
        delete request.bb_9_3yr;
        delete request.ip_3yr;
        delete request.fb_velocity;
        delete request.fb_spin;
        delete request.xera;
        delete request.k_percent;
        delete request.bb_percent;
        delete request.whiff_percent_pitcher;
        delete request.chase_percent_pitcher;
      }

      try {
        const prediction = await createPrediction(request);
        setPlayerState(prev => ({ ...prev, prediction, isLoading: false }));
      } catch (err) {
        setPlayerState(prev => ({
          ...prev,
          error: err instanceof Error ? err.message : 'Prediction failed',
          isLoading: false,
        }));
      }
    } else {
      setPlayerState(prev => ({
        ...prev,
        error: 'No stats available for this player',
        isLoading: false,
      }));
    }
  };

  const clearPlayer = (setPlayerState: React.Dispatch<React.SetStateAction<PlayerState>>) => {
    setPlayerState(initialPlayerState);
  };

  // Comparison helpers
  const getComparisonClass = (value1: number | null | undefined, value2: number | null | undefined, higherIsBetter = true) => {
    if (value1 == null || value2 == null) return '';
    if (value1 === value2) return '';
    const isWinner = higherIsBetter ? value1 > value2 : value1 < value2;
    return isWinner ? 'text-emerald-700 font-semibold' : '';
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-primary text-primary-foreground">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <Image
                src="https://github.com/almarj.png"
                alt="Logo"
                width={40}
                height={40}
                className="rounded-full"
              />
              <div>
                <h1 className="text-2xl font-bold">MLB Contract Advisor</h1>
                <p className="text-primary-foreground/70 text-sm">AI-Powered Contract Predictions</p>
              </div>
            </div>
            <nav className="flex gap-4">
              <Link href="/" className="hover:text-primary-foreground/80">Predict</Link>
              <Link href="/compare" className="hover:text-primary-foreground/80 font-medium">Compare</Link>
              <Link href="/contracts" className="hover:text-primary-foreground/80">Contracts</Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Compare Players</CardTitle>
            <p className="text-sm text-muted-foreground">
              Search for two players to compare their contract predictions side-by-side
            </p>
          </CardHeader>
        </Card>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Player 1 */}
          <div className="space-y-4">
            <PlayerSearchCard
              title="Player 1"
              state={player1}
              dropdownRef={dropdown1Ref}
              onSearchChange={(query) => setPlayer1(prev => ({ ...prev, searchQuery: query, selectedPlayer: null }))}
              onPlayerSelect={(player) => handlePlayerSelect(player, setPlayer1)}
              onClear={() => clearPlayer(setPlayer1)}
              onToggleDetails={() => setPlayer1(prev => ({ ...prev, showDetails: !prev.showDetails }))}
              otherPrediction={player2.prediction}
              getComparisonClass={getComparisonClass}
            />
          </div>

          {/* VS Divider (Mobile) */}
          <div className="lg:hidden flex items-center justify-center py-2">
            <div className="bg-muted rounded-full px-4 py-2 text-sm font-medium text-muted-foreground">
              VS
            </div>
          </div>

          {/* Player 2 */}
          <div className="space-y-4">
            <PlayerSearchCard
              title="Player 2"
              state={player2}
              dropdownRef={dropdown2Ref}
              onSearchChange={(query) => setPlayer2(prev => ({ ...prev, searchQuery: query, selectedPlayer: null }))}
              onPlayerSelect={(player) => handlePlayerSelect(player, setPlayer2)}
              onClear={() => clearPlayer(setPlayer2)}
              onToggleDetails={() => setPlayer2(prev => ({ ...prev, showDetails: !prev.showDetails }))}
              otherPrediction={player1.prediction}
              getComparisonClass={getComparisonClass}
              isSecondPlayer
            />
          </div>
        </div>

        {/* Comparison Summary (when both players selected) */}
        {player1.prediction && player2.prediction && (
          <Card className="mt-8">
            <CardHeader>
              <CardTitle className="text-lg">Comparison Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="font-semibold">{player1.prediction.player_name}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">vs</p>
                </div>
                <div>
                  <p className="font-semibold">{player2.prediction.player_name}</p>
                </div>

                {/* AAV Comparison */}
                <div className={getComparisonClass(player1.prediction.predicted_aav, player2.prediction.predicted_aav)}>
                  <p className="text-2xl font-bold font-mono">{formatAAV(player1.prediction.predicted_aav)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Predicted AAV</p>
                </div>
                <div className={getComparisonClass(player2.prediction.predicted_aav, player1.prediction.predicted_aav)}>
                  <p className="text-2xl font-bold font-mono">{formatAAV(player2.prediction.predicted_aav)}</p>
                </div>

                {/* Length Comparison */}
                <div className={getComparisonClass(player1.prediction.predicted_length, player2.prediction.predicted_length)}>
                  <p className="text-xl font-semibold">{player1.prediction.predicted_length} years</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Contract Length</p>
                </div>
                <div className={getComparisonClass(player2.prediction.predicted_length, player1.prediction.predicted_length)}>
                  <p className="text-xl font-semibold">{player2.prediction.predicted_length} years</p>
                </div>

                {/* Total Value */}
                <div className={getComparisonClass(
                  player1.prediction.predicted_aav * player1.prediction.predicted_length,
                  player2.prediction.predicted_aav * player2.prediction.predicted_length
                )}>
                  <p className="text-lg font-mono">
                    {formatAAV(player1.prediction.predicted_aav * player1.prediction.predicted_length).replace('M', '')}M total
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Value</p>
                </div>
                <div className={getComparisonClass(
                  player2.prediction.predicted_aav * player2.prediction.predicted_length,
                  player1.prediction.predicted_aav * player1.prediction.predicted_length
                )}>
                  <p className="text-lg font-mono">
                    {formatAAV(player2.prediction.predicted_aav * player2.prediction.predicted_length).replace('M', '')}M total
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-muted/50 border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-sm text-muted-foreground">
          <p>MLB Contract Advisor - For educational purposes only</p>
        </div>
      </footer>
    </div>
  );
}

interface PlayerSearchCardProps {
  title: string;
  state: PlayerState;
  dropdownRef: React.RefObject<HTMLDivElement | null>;
  onSearchChange: (query: string) => void;
  onPlayerSelect: (player: PlayerSearchResult) => void;
  onClear: () => void;
  onToggleDetails: () => void;
  otherPrediction: PredictionResponse | null;
  getComparisonClass: (v1: number | null | undefined, v2: number | null | undefined, higherIsBetter?: boolean) => string;
  isSecondPlayer?: boolean;
}

function PlayerSearchCard({
  title,
  state,
  dropdownRef,
  onSearchChange,
  onPlayerSelect,
  onClear,
  onToggleDetails,
  otherPrediction,
  getComparisonClass,
  isSecondPlayer = false,
}: PlayerSearchCardProps) {
  const getAssessmentBadge = (prediction: PredictionResponse) => {
    if (prediction.actual_aav === null) {
      return <Badge className="bg-gray-50 text-gray-700">Projected</Badge>;
    }
    const diff = prediction.actual_aav - prediction.predicted_aav;
    const pctDiff = (diff / prediction.predicted_aav) * 100;
    if (Math.abs(pctDiff) < 10) {
      return <Badge className="bg-emerald-50 text-emerald-800">Fair Value</Badge>;
    } else if (pctDiff > 10) {
      return <Badge className="bg-amber-50 text-amber-800">Overpaid</Badge>;
    } else {
      return <Badge className="bg-slate-100 text-slate-700">Underpaid</Badge>;
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Search Input */}
        <div className="relative" ref={dropdownRef}>
          <Input
            value={state.searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search for a player..."
            autoComplete="off"
          />
          {state.isSearching && (
            <div className="absolute right-3 top-3">
              <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
            </div>
          )}
          {state.showDropdown && state.searchResults.length > 0 && (
            <div className="absolute z-50 w-full mt-1 bg-popover border rounded-md shadow-lg max-h-60 overflow-auto">
              {state.searchResults.map((player) => (
                <button
                  key={player.id}
                  type="button"
                  className="w-full px-3 py-2 text-left hover:bg-accent flex items-center justify-between"
                  onClick={() => onPlayerSelect(player)}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{player.name}</span>
                    {!player.has_contract && (
                      <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">
                        Pre-FA
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="text-xs">
                      {player.position}
                    </Badge>
                    {player.stats && (
                      <span className="text-xs text-muted-foreground">
                        {player.stats.war_3yr?.toFixed(1)} WAR
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Loading State */}
        {state.isLoading && (
          <div className="mt-6 flex items-center justify-center py-8">
            <div className="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full" />
            <span className="ml-2 text-muted-foreground">Generating prediction...</span>
          </div>
        )}

        {/* Error State */}
        {state.error && (
          <div className="mt-4 p-3 bg-destructive/10 text-destructive rounded-lg text-sm">
            {state.error}
          </div>
        )}

        {/* Prediction Result */}
        {state.prediction && !state.isLoading && (
          <div className="mt-6 space-y-4">
            {/* Player Info */}
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-lg">{state.prediction.player_name}</p>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="secondary">{state.prediction.position}</Badge>
                  {getAssessmentBadge(state.prediction)}
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={onClear}>
                Clear
              </Button>
            </div>

            {/* Main Prediction */}
            <div className="bg-muted/50 rounded-lg p-4 text-center">
              <p className="text-sm text-muted-foreground mb-1">Predicted AAV</p>
              <p className={`text-3xl font-bold font-mono ${
                otherPrediction
                  ? isSecondPlayer
                    ? getComparisonClass(state.prediction.predicted_aav, otherPrediction.predicted_aav)
                    : getComparisonClass(state.prediction.predicted_aav, otherPrediction.predicted_aav)
                  : 'text-primary'
              }`}>
                {formatAAV(state.prediction.predicted_aav)}
              </p>
              <p className="text-muted-foreground mt-1">
                {state.prediction.predicted_length} year{state.prediction.predicted_length !== 1 ? 's' : ''}
              </p>
            </div>

            {/* Key Stats */}
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="bg-muted/30 rounded-lg p-3">
                <p className="text-xs text-muted-foreground">WAR (3yr)</p>
                <p className={`font-semibold ${
                  otherPrediction?.signing_war_3yr != null
                    ? getComparisonClass(state.prediction.signing_war_3yr, otherPrediction.signing_war_3yr)
                    : ''
                }`}>
                  {state.prediction.signing_war_3yr?.toFixed(1) ?? '-'}
                </p>
              </div>
              {!isPitcher(state.prediction.position) && state.prediction.signing_wrc_plus_3yr != null && (
                <div className="bg-muted/30 rounded-lg p-3">
                  <p className="text-xs text-muted-foreground">wRC+</p>
                  <p className={`font-semibold ${
                    otherPrediction?.signing_wrc_plus_3yr != null
                      ? getComparisonClass(state.prediction.signing_wrc_plus_3yr, otherPrediction.signing_wrc_plus_3yr)
                      : ''
                  }`}>
                    {state.prediction.signing_wrc_plus_3yr?.toFixed(0)}
                  </p>
                </div>
              )}
              {isPitcher(state.prediction.position) && state.prediction.signing_era_3yr != null && (
                <div className="bg-muted/30 rounded-lg p-3">
                  <p className="text-xs text-muted-foreground">ERA</p>
                  <p className={`font-semibold ${
                    otherPrediction?.signing_era_3yr != null
                      ? getComparisonClass(state.prediction.signing_era_3yr, otherPrediction.signing_era_3yr, false)
                      : ''
                  }`}>
                    {state.prediction.signing_era_3yr?.toFixed(2)}
                  </p>
                </div>
              )}
              <div className="bg-muted/30 rounded-lg p-3">
                <p className="text-xs text-muted-foreground">Confidence</p>
                <p className="font-semibold">{state.prediction.confidence_score.toFixed(0)}%</p>
              </div>
            </div>

            {/* Actual Contract (if signed) */}
            {state.prediction.actual_aav !== null && (
              <div className="border rounded-lg p-3">
                <p className="text-xs text-muted-foreground mb-1">Actual Contract</p>
                <p className="font-mono font-semibold">
                  {formatAAV(state.prediction.actual_aav)} / {state.prediction.actual_length} years
                </p>
              </div>
            )}

            {/* Expandable Details */}
            <button
              type="button"
              onClick={onToggleDetails}
              className="w-full flex items-center justify-center gap-2 text-sm text-muted-foreground hover:text-foreground py-2"
            >
              {state.showDetails ? (
                <>
                  <ChevronUp className="h-4 w-4" />
                  Hide Details
                </>
              ) : (
                <>
                  <ChevronDown className="h-4 w-4" />
                  Show Comparables
                </>
              )}
            </button>

            {state.showDetails && (
              <div className="space-y-2 pt-2 border-t">
                <p className="text-sm font-medium text-muted-foreground">Top Comparables</p>
                {state.prediction.comparables.slice(0, 3).map((comp, idx) => (
                  <div key={idx} className="flex justify-between items-center text-sm py-1">
                    <div className="flex items-center gap-2">
                      <span>{comp.name}</span>
                      {comp.is_extension && (
                        <Badge variant="outline" className="text-xs bg-slate-50 text-slate-600">
                          Ext
                        </Badge>
                      )}
                    </div>
                    <span className="font-mono">{formatAAV(comp.aav)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Empty State */}
        {!state.prediction && !state.isLoading && !state.error && (
          <div className="mt-6 text-center py-8 text-muted-foreground">
            <p>Search for a player to see prediction</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
