'use client';

import useSWR from 'swr';
import {
  getContractPlayerStats,
  BatterYearlyStats,
  PitcherYearlyStats,
  isPitcher,
} from '@/lib/api';
import { TableRow, TableCell } from '@/components/ui/table';

interface ExpandableStatsRowProps {
  contractId: number;
  playerName: string;
  position: string;
  isExpanded: boolean;
}

export function ExpandableStatsRow({
  contractId,
  playerName,
  position,
  isExpanded,
}: ExpandableStatsRowProps) {
  // Only fetch when expanded
  const { data, error, isLoading } = useSWR(
    isExpanded ? ['contract-stats', contractId] : null,
    () => getContractPlayerStats(contractId)
  );

  if (!isExpanded) return null;

  const playerIsPitcher = isPitcher(position);

  return (
    <TableRow className="bg-muted/30 hover:bg-muted/30">
      <TableCell colSpan={7} className="p-0">
        <div className="px-6 py-4">
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
              Failed to load stats for {playerName}
            </div>
          )}

          {data && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-muted-foreground mb-3">
                Year-by-Year Performance ({data.seasons[0]}-{data.seasons[data.seasons.length - 1]})
              </p>

              {playerIsPitcher ? (
                <PitcherStatsTable stats={data.pitcher_stats} />
              ) : (
                <BatterStatsTable stats={data.batter_stats} />
              )}

              {((playerIsPitcher &&
                (!data.pitcher_stats || data.pitcher_stats.length === 0)) ||
                (!playerIsPitcher &&
                  (!data.batter_stats || data.batter_stats.length === 0))) && (
                <p className="text-sm text-muted-foreground text-center py-2">
                  No recent stats available for this player
                </p>
              )}
            </div>
          )}
        </div>
      </TableCell>
    </TableRow>
  );
}

function BatterStatsTable({ stats }: { stats: BatterYearlyStats[] | null }) {
  if (!stats || stats.length === 0) return null;

  return (
    <div className="overflow-x-auto rounded border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            <th className="px-3 py-2 text-left font-medium">Year</th>
            <th className="px-3 py-2 text-left font-medium">Team</th>
            <th className="px-3 py-2 text-right font-medium">G</th>
            <th className="px-3 py-2 text-right font-medium">PA</th>
            <th className="px-3 py-2 text-right font-medium">WAR</th>
            <th className="px-3 py-2 text-right font-medium">wRC+</th>
            <th className="px-3 py-2 text-right font-medium">AVG</th>
            <th className="px-3 py-2 text-right font-medium">OBP</th>
            <th className="px-3 py-2 text-right font-medium">SLG</th>
            <th className="px-3 py-2 text-right font-medium">HR</th>
            <th className="px-3 py-2 text-right font-medium">RBI</th>
            <th className="px-3 py-2 text-right font-medium">R</th>
            <th className="px-3 py-2 text-right font-medium">H</th>
            <th className="px-3 py-2 text-right font-medium">SB</th>
          </tr>
        </thead>
        <tbody>
          {stats.map((stat) => (
            <tr key={stat.season} className="border-t">
              <td className="px-3 py-2 font-medium">{stat.season}</td>
              <td className="px-3 py-2">{stat.team}</td>
              <td className="px-3 py-2 text-right">{stat.games ?? '-'}</td>
              <td className="px-3 py-2 text-right">{stat.pa ?? '-'}</td>
              <td className="px-3 py-2 text-right font-medium">
                {stat.war?.toFixed(1) ?? '-'}
              </td>
              <td className="px-3 py-2 text-right">
                {stat.wrc_plus?.toFixed(0) ?? '-'}
              </td>
              <td className="px-3 py-2 text-right font-mono">
                {stat.avg?.toFixed(3) ?? '-'}
              </td>
              <td className="px-3 py-2 text-right font-mono">
                {stat.obp?.toFixed(3) ?? '-'}
              </td>
              <td className="px-3 py-2 text-right font-mono">
                {stat.slg?.toFixed(3) ?? '-'}
              </td>
              <td className="px-3 py-2 text-right">{stat.hr ?? '-'}</td>
              <td className="px-3 py-2 text-right">{stat.rbi ?? '-'}</td>
              <td className="px-3 py-2 text-right">{stat.runs ?? '-'}</td>
              <td className="px-3 py-2 text-right">{stat.hits ?? '-'}</td>
              <td className="px-3 py-2 text-right">{stat.sb ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PitcherStatsTable({ stats }: { stats: PitcherYearlyStats[] | null }) {
  if (!stats || stats.length === 0) return null;

  return (
    <div className="overflow-x-auto rounded border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            <th className="px-3 py-2 text-left font-medium">Year</th>
            <th className="px-3 py-2 text-left font-medium">Team</th>
            <th className="px-3 py-2 text-right font-medium">G</th>
            <th className="px-3 py-2 text-right font-medium">W-L</th>
            <th className="px-3 py-2 text-right font-medium">IP</th>
            <th className="px-3 py-2 text-right font-medium">WAR</th>
            <th className="px-3 py-2 text-right font-medium">ERA</th>
            <th className="px-3 py-2 text-right font-medium">FIP</th>
            <th className="px-3 py-2 text-right font-medium">K/9</th>
            <th className="px-3 py-2 text-right font-medium">BB/9</th>
          </tr>
        </thead>
        <tbody>
          {stats.map((stat) => (
            <tr key={stat.season} className="border-t">
              <td className="px-3 py-2 font-medium">{stat.season}</td>
              <td className="px-3 py-2">{stat.team}</td>
              <td className="px-3 py-2 text-right">{stat.games ?? '-'}</td>
              <td className="px-3 py-2 text-right">
                {stat.wins ?? 0}-{stat.losses ?? 0}
              </td>
              <td className="px-3 py-2 text-right">
                {stat.ip?.toFixed(1) ?? '-'}
              </td>
              <td className="px-3 py-2 text-right font-medium">
                {stat.war?.toFixed(1) ?? '-'}
              </td>
              <td className="px-3 py-2 text-right font-mono">
                {stat.era?.toFixed(2) ?? '-'}
              </td>
              <td className="px-3 py-2 text-right font-mono">
                {stat.fip?.toFixed(2) ?? '-'}
              </td>
              <td className="px-3 py-2 text-right">
                {stat.k_9?.toFixed(1) ?? '-'}
              </td>
              <td className="px-3 py-2 text-right">
                {stat.bb_9?.toFixed(1) ?? '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
