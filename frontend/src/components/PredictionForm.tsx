'use client';

import { useState, useEffect, useRef } from 'react';
import { PredictionRequest, isPitcher, POSITIONS, searchPlayers, PlayerSearchResult } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface PredictionFormProps {
  onSubmit: (data: PredictionRequest) => void;
  isLoading: boolean;
}

export default function PredictionForm({ onSubmit, isLoading }: PredictionFormProps) {
  const [formData, setFormData] = useState<PredictionRequest>({
    name: '',
    position: 'RF',
    age: 28,
    war_3yr: 3.0,
    wrc_plus_3yr: 120,
    avg_3yr: 0.270,
    obp_3yr: 0.350,
    slg_3yr: 0.450,
    hr_3yr: 25,
  });

  const [showAdvanced, setShowAdvanced] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<PlayerSearchResult[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedPlayer, setSelectedPlayer] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const isPitcherPosition = isPitcher(formData.position);

  // Debounced player search
  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await searchPlayers(searchQuery);
        setSearchResults(results);
        setShowDropdown(results.length > 0);
      } catch (error) {
        console.error('Search failed:', error);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handlePlayerSelect = (player: PlayerSearchResult) => {
    setSearchQuery(player.name);
    setSelectedPlayer(player.name);
    setShowDropdown(false);

    // Auto-fill form with player stats
    if (player.stats) {
      const stats = player.stats;
      // Calculate estimated current age (year_signed was when contract was signed)
      const currentYear = new Date().getFullYear();
      const estimatedAge = stats.age_at_signing + (currentYear - stats.year_signed);

      setFormData({
        name: player.name,
        position: stats.position,
        age: Math.min(estimatedAge, 45), // Cap at 45
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
      });
    } else {
      // Just update name and position
      setFormData(prev => ({
        ...prev,
        name: player.name,
        position: player.position,
      }));
    }
  };

  const handleNameInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    setSelectedPlayer(null);
    setFormData(prev => ({ ...prev, name: value }));
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? parseFloat(value) || 0 : value,
    }));
  };

  const handlePositionChange = (value: string) => {
    setFormData(prev => ({ ...prev, position: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Clean up data based on position type
    const cleanedData = { ...formData };
    if (isPitcherPosition) {
      // Remove batter-specific fields
      delete cleanedData.wrc_plus_3yr;
      delete cleanedData.avg_3yr;
      delete cleanedData.obp_3yr;
      delete cleanedData.slg_3yr;
      delete cleanedData.hr_3yr;
      delete cleanedData.avg_exit_velo;
      delete cleanedData.barrel_rate;
      delete cleanedData.max_exit_velo;
      delete cleanedData.hard_hit_pct;

      // Set default pitcher values if missing
      if (!cleanedData.era_3yr) cleanedData.era_3yr = 3.50;
      if (!cleanedData.fip_3yr) cleanedData.fip_3yr = 3.50;
      if (!cleanedData.k_9_3yr) cleanedData.k_9_3yr = 9.0;
      if (!cleanedData.bb_9_3yr) cleanedData.bb_9_3yr = 2.5;
      if (!cleanedData.ip_3yr) cleanedData.ip_3yr = 180;
    } else {
      // Remove pitcher-specific fields
      delete cleanedData.era_3yr;
      delete cleanedData.fip_3yr;
      delete cleanedData.k_9_3yr;
      delete cleanedData.bb_9_3yr;
      delete cleanedData.ip_3yr;
    }

    onSubmit(cleanedData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Basic Info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="space-y-2 relative" ref={dropdownRef}>
          <Label htmlFor="name">Player Name</Label>
          <Input
            id="name"
            name="name"
            value={searchQuery || formData.name}
            onChange={handleNameInputChange}
            placeholder="Search for a player..."
            autoComplete="off"
            required
          />
          {isSearching && (
            <div className="absolute right-3 top-9">
              <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
            </div>
          )}
          {showDropdown && searchResults.length > 0 && (
            <div className="absolute z-50 w-full mt-1 bg-popover border rounded-md shadow-lg max-h-60 overflow-auto">
              {searchResults.map((player) => (
                <button
                  key={player.id}
                  type="button"
                  className="w-full px-3 py-2 text-left hover:bg-accent flex items-center justify-between"
                  onClick={() => handlePlayerSelect(player)}
                >
                  <span className="font-medium">{player.name}</span>
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
          {selectedPlayer && (
            <p className="text-xs text-green-600 mt-1">Stats auto-filled from database</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="position">Position</Label>
          <Select value={formData.position} onValueChange={handlePositionChange}>
            <SelectTrigger>
              <SelectValue placeholder="Select position" />
            </SelectTrigger>
            <SelectContent>
              {POSITIONS.map(pos => (
                <SelectItem key={pos.value} value={pos.value}>
                  {pos.value} - {pos.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="age">Age at Signing</Label>
          <Input
            id="age"
            type="number"
            name="age"
            value={formData.age}
            onChange={handleChange}
            min={18}
            max={45}
            required
          />
        </div>
      </div>

      {/* Core Stats */}
      <div>
        <h3 className="text-lg font-semibold mb-3">3-Year Average Stats</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="space-y-2">
            <Label htmlFor="war_3yr">WAR</Label>
            <Input
              id="war_3yr"
              type="number"
              name="war_3yr"
              value={formData.war_3yr}
              onChange={handleChange}
              step="0.1"
              required
            />
          </div>

          {isPitcherPosition ? (
            <>
              <div className="space-y-2">
                <Label htmlFor="era_3yr">ERA</Label>
                <Input
                  id="era_3yr"
                  type="number"
                  name="era_3yr"
                  value={formData.era_3yr || ''}
                  onChange={handleChange}
                  step="0.01"
                  placeholder="3.50"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="fip_3yr">FIP</Label>
                <Input
                  id="fip_3yr"
                  type="number"
                  name="fip_3yr"
                  value={formData.fip_3yr || ''}
                  onChange={handleChange}
                  step="0.01"
                  placeholder="3.50"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="k_9_3yr">K/9</Label>
                <Input
                  id="k_9_3yr"
                  type="number"
                  name="k_9_3yr"
                  value={formData.k_9_3yr || ''}
                  onChange={handleChange}
                  step="0.1"
                  placeholder="9.0"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="bb_9_3yr">BB/9</Label>
                <Input
                  id="bb_9_3yr"
                  type="number"
                  name="bb_9_3yr"
                  value={formData.bb_9_3yr || ''}
                  onChange={handleChange}
                  step="0.1"
                  placeholder="2.5"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ip_3yr">IP</Label>
                <Input
                  id="ip_3yr"
                  type="number"
                  name="ip_3yr"
                  value={formData.ip_3yr || ''}
                  onChange={handleChange}
                  step="1"
                  placeholder="180"
                />
              </div>
            </>
          ) : (
            <>
              <div className="space-y-2">
                <Label htmlFor="wrc_plus_3yr">wRC+</Label>
                <Input
                  id="wrc_plus_3yr"
                  type="number"
                  name="wrc_plus_3yr"
                  value={formData.wrc_plus_3yr || ''}
                  onChange={handleChange}
                  placeholder="120"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="avg_3yr">AVG</Label>
                <Input
                  id="avg_3yr"
                  type="number"
                  name="avg_3yr"
                  value={formData.avg_3yr || ''}
                  onChange={handleChange}
                  step="0.001"
                  placeholder="0.270"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="obp_3yr">OBP</Label>
                <Input
                  id="obp_3yr"
                  type="number"
                  name="obp_3yr"
                  value={formData.obp_3yr || ''}
                  onChange={handleChange}
                  step="0.001"
                  placeholder="0.350"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="slg_3yr">SLG</Label>
                <Input
                  id="slg_3yr"
                  type="number"
                  name="slg_3yr"
                  value={formData.slg_3yr || ''}
                  onChange={handleChange}
                  step="0.001"
                  placeholder="0.450"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="hr_3yr">HR</Label>
                <Input
                  id="hr_3yr"
                  type="number"
                  name="hr_3yr"
                  value={formData.hr_3yr || ''}
                  onChange={handleChange}
                  placeholder="25"
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Advanced Stats (Statcast) - Batters only */}
      {!isPitcherPosition && (
        <div>
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-primary hover:text-primary/80 text-sm font-medium"
          >
            {showAdvanced ? '- Hide' : '+ Show'} Statcast Metrics (Optional)
          </button>

          {showAdvanced && (
            <Card className="mt-3">
              <CardContent className="pt-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="avg_exit_velo">Exit Velocity</Label>
                    <Input
                      id="avg_exit_velo"
                      type="number"
                      name="avg_exit_velo"
                      value={formData.avg_exit_velo || ''}
                      onChange={handleChange}
                      step="0.1"
                      placeholder="90.0"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="barrel_rate">Barrel %</Label>
                    <Input
                      id="barrel_rate"
                      type="number"
                      name="barrel_rate"
                      value={formData.barrel_rate || ''}
                      onChange={handleChange}
                      step="0.1"
                      placeholder="10.0"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="max_exit_velo">Max Exit Velo</Label>
                    <Input
                      id="max_exit_velo"
                      type="number"
                      name="max_exit_velo"
                      value={formData.max_exit_velo || ''}
                      onChange={handleChange}
                      step="0.1"
                      placeholder="115.0"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="hard_hit_pct">Hard Hit %</Label>
                    <Input
                      id="hard_hit_pct"
                      type="number"
                      name="hard_hit_pct"
                      value={formData.hard_hit_pct || ''}
                      onChange={handleChange}
                      step="0.1"
                      placeholder="45.0"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Submit Button */}
      <Button type="submit" className="w-full" size="lg" disabled={isLoading}>
        {isLoading ? 'Predicting...' : 'Predict Contract Value'}
      </Button>
    </form>
  );
}
