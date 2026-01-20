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
import { ChevronUp, ChevronDown } from 'lucide-react';

interface PredictionFormProps {
  onSubmit: (data: PredictionRequest) => void;
  isLoading: boolean;
  onClear?: () => void;
  initialPlayer?: string;
}

interface ValidationErrors {
  name?: string;
  age?: string;
  war_3yr?: string;
  wrc_plus_3yr?: string;
  avg_3yr?: string;
  obp_3yr?: string;
  slg_3yr?: string;
  hr_3yr?: string;
  era_3yr?: string;
  fip_3yr?: string;
  k_9_3yr?: string;
  bb_9_3yr?: string;
  ip_3yr?: string;
}

const defaultFormData: PredictionRequest = {
  name: '',
  position: 'RF',
  age: 28,
  war_3yr: 3.0,
  wrc_plus_3yr: 120,
  avg_3yr: 0.270,
  obp_3yr: 0.350,
  slg_3yr: 0.450,
  hr_3yr: 25,
};

export default function PredictionForm({ onSubmit, isLoading, onClear, initialPlayer }: PredictionFormProps) {
  const [formData, setFormData] = useState<PredictionRequest>(defaultFormData);
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [touched, setTouched] = useState<Set<string>>(new Set());

  const [showAdvanced, setShowAdvanced] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<PlayerSearchResult[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedPlayer, setSelectedPlayer] = useState<string | null>(null);
  const [isProspect, setIsProspect] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Validate a single field
  const validateField = (name: string, value: unknown): string | undefined => {
    switch (name) {
      case 'name':
        if (!value || (typeof value === 'string' && value.trim().length < 2)) {
          return 'Player name is required';
        }
        break;
      case 'age':
        if (typeof value === 'number' && (value < 18 || value > 45)) {
          return 'Age must be 18-45';
        }
        break;
      case 'war_3yr':
        if (typeof value === 'number' && (value < -5 || value > 15)) {
          return 'WAR should be -5 to 15';
        }
        break;
      case 'avg_3yr':
        if (value && typeof value === 'number' && (value < 0.100 || value > 0.400)) {
          return 'AVG should be .100-.400';
        }
        break;
      case 'obp_3yr':
        if (value && typeof value === 'number' && (value < 0.150 || value > 0.550)) {
          return 'OBP should be .150-.550';
        }
        break;
      case 'slg_3yr':
        if (value && typeof value === 'number' && (value < 0.200 || value > 0.800)) {
          return 'SLG should be .200-.800';
        }
        break;
      case 'era_3yr':
        if (value && typeof value === 'number' && (value < 0 || value > 10)) {
          return 'ERA should be 0-10';
        }
        break;
      case 'fip_3yr':
        if (value && typeof value === 'number' && (value < 0 || value > 10)) {
          return 'FIP should be 0-10';
        }
        break;
    }
    return undefined;
  };

  // Validate all fields
  const validateForm = (): boolean => {
    const newErrors: ValidationErrors = {};
    Object.entries(formData).forEach(([key, value]) => {
      const error = validateField(key, value);
      if (error) {
        newErrors[key as keyof ValidationErrors] = error;
      }
    });
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle field blur for inline validation
  const handleBlur = (name: string) => {
    setTouched(prev => new Set(prev).add(name));
    const error = validateField(name, formData[name as keyof PredictionRequest]);
    setErrors(prev => ({ ...prev, [name]: error }));
  };

  // Clear form
  const handleClear = () => {
    setFormData(defaultFormData);
    setSearchQuery('');
    setSelectedPlayer(null);
    setIsProspect(false);
    setErrors({});
    setTouched(new Set());
    onClear?.();
  };

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

  // Auto-search when initialPlayer is provided (from contracts page link)
  useEffect(() => {
    if (initialPlayer && initialPlayer.length >= 2) {
      setSearchQuery(initialPlayer);
      // Trigger search and auto-select first matching result
      const autoSearch = async () => {
        setIsSearching(true);
        try {
          const results = await searchPlayers(initialPlayer);
          if (results.length > 0) {
            // Find exact match or use first result
            const exactMatch = results.find(r => r.name.toLowerCase() === initialPlayer.toLowerCase());
            const playerToSelect = exactMatch || results[0];
            handlePlayerSelect(playerToSelect);
          }
        } catch (error) {
          console.error('Auto-search failed:', error);
        } finally {
          setIsSearching(false);
        }
      };
      autoSearch();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialPlayer]);

  const handlePlayerSelect = (player: PlayerSearchResult) => {
    setSearchQuery(player.name);
    setSelectedPlayer(player.name);
    setShowDropdown(false);
    setIsProspect(!player.has_contract);

    // Auto-fill form with player stats
    if (player.stats) {
      const stats = player.stats;
      const currentYear = new Date().getFullYear();

      // Calculate age differently for signed vs prospect players
      let estimatedAge: number;
      if (player.has_contract && stats.age_at_signing) {
        // Signed player: use their actual age at signing from the database
        estimatedAge = stats.age_at_signing;
      } else if (stats.current_age && stats.last_season) {
        // Pre-FA player: calculate current age, adjusted for year
        estimatedAge = stats.current_age + (currentYear - stats.last_season);
      } else {
        estimatedAge = 28; // Default
      }

      setFormData({
        name: player.name,
        position: stats.position,
        age: Math.min(Math.max(estimatedAge, 18), 45), // Clamp between 18-45
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
        // Pitcher Statcast
        fb_velocity: stats.fb_velocity ?? undefined,
        fb_spin: stats.fb_spin ?? undefined,
        xera: stats.xera ?? undefined,
        k_percent: stats.k_percent ?? undefined,
        bb_percent: stats.bb_percent ?? undefined,
        whiff_percent_pitcher: stats.whiff_percent_pitcher ?? undefined,
        chase_percent_pitcher: stats.chase_percent_pitcher ?? undefined,
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

    // Validate before submitting
    if (!validateForm()) {
      return;
    }

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
      delete cleanedData.chase_rate;
      delete cleanedData.whiff_rate;

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
      // Remove pitcher Statcast
      delete cleanedData.fb_velocity;
      delete cleanedData.fb_spin;
      delete cleanedData.xera;
      delete cleanedData.k_percent;
      delete cleanedData.bb_percent;
      delete cleanedData.whiff_percent_pitcher;
      delete cleanedData.chase_percent_pitcher;
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
            onBlur={() => handleBlur('name')}
            placeholder="Search for a player..."
            autoComplete="off"
            required
            className={touched.has('name') && errors.name ? 'border-destructive' : ''}
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
          {touched.has('name') && errors.name ? (
            <p className="text-xs text-destructive">{errors.name}</p>
          ) : selectedPlayer ? (
            <p className={`text-xs ${isProspect ? 'text-slate-600' : 'text-emerald-700'}`}>
              {isProspect
                ? 'Stats auto-filled from FanGraphs (pre-FA player)'
                : 'Stats auto-filled from contract database'}
            </p>
          ) : null}
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
            onBlur={() => handleBlur('age')}
            min={18}
            max={45}
            required
            className={touched.has('age') && errors.age ? 'border-destructive' : ''}
          />
          {touched.has('age') && errors.age && (
            <p className="text-xs text-destructive">{errors.age}</p>
          )}
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
              onBlur={() => handleBlur('war_3yr')}
              step="0.1"
              required
              className={touched.has('war_3yr') && errors.war_3yr ? 'border-destructive' : ''}
            />
            {touched.has('war_3yr') && errors.war_3yr && (
              <p className="text-xs text-destructive">{errors.war_3yr}</p>
            )}
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
                <div className="mt-4 pt-4 border-t">
                  <h4 className="text-sm font-medium mb-3 text-muted-foreground">Plate Discipline (Percentiles 0-100)</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="chase_rate">Chase Rate</Label>
                      <Input
                        id="chase_rate"
                        type="number"
                        name="chase_rate"
                        value={formData.chase_rate || ''}
                        onChange={handleChange}
                        step="1"
                        min="0"
                        max="100"
                        placeholder="50"
                      />
                      <p className="text-xs text-muted-foreground">Higher = less chasing</p>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="whiff_rate">Whiff Rate</Label>
                      <Input
                        id="whiff_rate"
                        type="number"
                        name="whiff_rate"
                        value={formData.whiff_rate || ''}
                        onChange={handleChange}
                        step="1"
                        min="0"
                        max="100"
                        placeholder="50"
                      />
                      <p className="text-xs text-muted-foreground">Higher = better contact</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Advanced Stats (Statcast) - Pitchers only */}
      {isPitcherPosition && (
        <div>
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            {showAdvanced ? 'Hide' : 'Show'} Pitcher Statcast Metrics
          </button>

          {showAdvanced && (
            <Card className="mt-3">
              <CardContent className="pt-4">
                <p className="text-sm text-muted-foreground mb-4">
                  Statcast percentile rankings (0-100). Higher = better. Leave blank to use average values.
                </p>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="fb_velocity">FB Velocity</Label>
                    <Input
                      id="fb_velocity"
                      type="number"
                      name="fb_velocity"
                      value={formData.fb_velocity || ''}
                      onChange={handleChange}
                      step="1"
                      min="0"
                      max="100"
                      placeholder="50"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="fb_spin">FB Spin</Label>
                    <Input
                      id="fb_spin"
                      type="number"
                      name="fb_spin"
                      value={formData.fb_spin || ''}
                      onChange={handleChange}
                      step="1"
                      min="0"
                      max="100"
                      placeholder="50"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="xera">xERA</Label>
                    <Input
                      id="xera"
                      type="number"
                      name="xera"
                      value={formData.xera || ''}
                      onChange={handleChange}
                      step="1"
                      min="0"
                      max="100"
                      placeholder="50"
                    />
                    <p className="text-xs text-muted-foreground">Higher = better</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="k_percent">K%</Label>
                    <Input
                      id="k_percent"
                      type="number"
                      name="k_percent"
                      value={formData.k_percent || ''}
                      onChange={handleChange}
                      step="1"
                      min="0"
                      max="100"
                      placeholder="50"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="bb_percent">BB%</Label>
                    <Input
                      id="bb_percent"
                      type="number"
                      name="bb_percent"
                      value={formData.bb_percent || ''}
                      onChange={handleChange}
                      step="1"
                      min="0"
                      max="100"
                      placeholder="50"
                    />
                    <p className="text-xs text-muted-foreground">Higher = fewer walks</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="whiff_percent_pitcher">Whiff%</Label>
                    <Input
                      id="whiff_percent_pitcher"
                      type="number"
                      name="whiff_percent_pitcher"
                      value={formData.whiff_percent_pitcher || ''}
                      onChange={handleChange}
                      step="1"
                      min="0"
                      max="100"
                      placeholder="50"
                    />
                    <p className="text-xs text-muted-foreground">Higher = more swings and misses</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="chase_percent_pitcher">Chase%</Label>
                    <Input
                      id="chase_percent_pitcher"
                      type="number"
                      name="chase_percent_pitcher"
                      value={formData.chase_percent_pitcher || ''}
                      onChange={handleChange}
                      step="1"
                      min="0"
                      max="100"
                      placeholder="50"
                    />
                    <p className="text-xs text-muted-foreground">Higher = more chases induced</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        <Button type="submit" className="flex-1" size="lg" disabled={isLoading}>
          {isLoading ? 'Predicting...' : 'Predict Contract Value'}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="lg"
          onClick={handleClear}
          disabled={isLoading}
        >
          Clear
        </Button>
      </div>
    </form>
  );
}
