'use client';

import useSWR from 'swr';
import { ContractRecord, formatAAV, getContractPlayerStats, isPitcher, BatterYearlyStats, PitcherYearlyStats } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface ContractCardProps {
  contract: ContractRecord;
  isExpanded: boolean;
  onToggle: () => void;
}

export function ContractCard({ contract, isExpanded, onToggle }: ContractCardProps) {
  // Only fetch stats when expanded
  const { data, error, isLoading } = useSWR(
    isExpanded ? ['contract-stats', contract.id] : null,
    () => getContractPlayerStats(contract.id)
  );

  const playerIsPitcher = isPitcher(contract.position);

  return (
    <Card
      className="cursor-pointer hover:bg-muted/50 transition-colors"
      onClick={onToggle}
    >
      <CardContent className="p-4">
        {/* Header row: Name and Position */}
        <div className="flex justify-between items-start mb-2">
          <h3 className="font-semibold text-base">{contract.player_name}</h3>
          <Badge variant="secondary" className="text-xs">
            {contract.position}
          </Badge>
        </div>

        {/* Primary stats row: AAV and Years */}
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-lg font-bold font-mono text-primary">
            {formatAAV(contract.aav)}
          </span>
          <span className="text-muted-foreground">•</span>
          <span className="text-sm text-muted-foreground">
            {contract.length} year{contract.length !== 1 ? 's' : ''}
          </span>
        </div>

        {/* Secondary stats row: Year, Age, WAR */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span>{contract.year_signed}</span>
            <span>•</span>
            <span>Age {contract.age_at_signing}</span>
            <span>•</span>
            <span>{contract.war_3yr?.toFixed(1) ?? '-'} WAR</span>
          </div>
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>

        {/* Expanded stats section */}
        {isExpanded && (
          <div className="mt-4 pt-4 border-t" onClick={(e) => e.stopPropagation()}>
            {isLoading && (
              <div className="flex items-center justify-center py-4">
                <div className="animate-spin h-5 w-5 border-2 border-primary border-t-transparent rounded-full" />
                <span className="ml-2 text-sm text-muted-foreground">
                  Loading stats...
                </span>
              </div>
            )}

            {error && (
              <div className="text-center py-4 text-sm text-destructive">
                Failed to load stats
              </div>
            )}

            {data && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-muted-foreground mb-3">
                  Year-by-Year Performance ({data.seasons[0]}-{data.seasons[data.seasons.length - 1]})
                </p>

                {playerIsPitcher ? (
                  <MobilePitcherStats stats={data.pitcher_stats} />
                ) : (
                  <MobileBatterStats stats={data.batter_stats} />
                )}

                {((playerIsPitcher &&
                  (!data.pitcher_stats || data.pitcher_stats.length === 0)) ||
                  (!playerIsPitcher &&
                    (!data.batter_stats || data.batter_stats.length === 0))) && (
                  <p className="text-sm text-muted-foreground text-center py-2">
                    No recent stats available
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MobileBatterStats({ stats }: { stats: BatterYearlyStats[] | null }) {
  if (!stats || stats.length === 0) return null;

  return (
    <div className="space-y-3">
      {stats.map((stat) => (
        <div key={stat.season} className="bg-muted/30 rounded-lg p-3">
          <div className="flex justify-between items-center mb-2">
            <span className="font-medium">{stat.season}</span>
            <span className="text-sm text-muted-foreground">{stat.team}</span>
          </div>
          <div className="grid grid-cols-4 gap-2 text-sm">
            <StatCell label="WAR" value={stat.war?.toFixed(1)} highlight />
            <StatCell label="wRC+" value={stat.wrc_plus?.toFixed(0)} />
            <StatCell label="AVG" value={stat.avg?.toFixed(3)} mono />
            <StatCell label="HR" value={stat.hr?.toString()} />
            <StatCell label="OBP" value={stat.obp?.toFixed(3)} mono />
            <StatCell label="SLG" value={stat.slg?.toFixed(3)} mono />
            <StatCell label="G" value={stat.games?.toString()} />
            <StatCell label="PA" value={stat.pa?.toString()} />
          </div>
        </div>
      ))}
    </div>
  );
}

function MobilePitcherStats({ stats }: { stats: PitcherYearlyStats[] | null }) {
  if (!stats || stats.length === 0) return null;

  return (
    <div className="space-y-3">
      {stats.map((stat) => (
        <div key={stat.season} className="bg-muted/30 rounded-lg p-3">
          <div className="flex justify-between items-center mb-2">
            <span className="font-medium">{stat.season}</span>
            <span className="text-sm text-muted-foreground">{stat.team}</span>
          </div>
          <div className="grid grid-cols-4 gap-2 text-sm">
            <StatCell label="WAR" value={stat.war?.toFixed(1)} highlight />
            <StatCell label="ERA" value={stat.era?.toFixed(2)} mono />
            <StatCell label="FIP" value={stat.fip?.toFixed(2)} mono />
            <StatCell label="IP" value={stat.ip?.toFixed(1)} />
            <StatCell label="K/9" value={stat.k_9?.toFixed(1)} />
            <StatCell label="BB/9" value={stat.bb_9?.toFixed(1)} />
            <StatCell label="W-L" value={`${stat.wins ?? 0}-${stat.losses ?? 0}`} />
            <StatCell label="G" value={stat.games?.toString()} />
          </div>
        </div>
      ))}
    </div>
  );
}

function StatCell({
  label,
  value,
  mono = false,
  highlight = false
}: {
  label: string;
  value?: string | null;
  mono?: boolean;
  highlight?: boolean;
}) {
  return (
    <div className="text-center">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`${mono ? 'font-mono' : ''} ${highlight ? 'font-semibold' : ''}`}>
        {value ?? '-'}
      </p>
    </div>
  );
}
