'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import useSWR from 'swr';
import { getContracts, getContractsSummary, formatAAV } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ChevronDown, ChevronRight, X } from 'lucide-react';
import { ExpandableStatsRow } from '@/components/ExpandableStatsRow';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

const POSITIONS = ['All', 'OF', '1B', '2B', '3B', 'SS', 'C', 'DH', 'SP', 'RP'];

const AAV_RANGES = [
  { label: 'All AAV', value: 'all' },
  { label: 'Under $10M', value: '0-10' },
  { label: '$10M - $20M', value: '10-20' },
  { label: '$20M - $30M', value: '20-30' },
  { label: '$30M+', value: '30-999' },
];

const WAR_RANGES = [
  { label: 'All WAR', value: 'all' },
  { label: 'Below 2', value: '-10-2' },
  { label: '2 - 4', value: '2-4' },
  { label: '4 - 6', value: '4-6' },
  { label: '6+', value: '6-20' },
];

const LENGTH_RANGES = [
  { label: 'All Lengths', value: 'all' },
  { label: '1-2 Years', value: '1-2' },
  { label: '3-4 Years', value: '3-4' },
  { label: '5-6 Years', value: '5-6' },
  { label: '7+ Years', value: '7-15' },
];

export default function ContractsPage() {
  const [page, setPage] = useState(1);
  const [position, setPosition] = useState<string>('All');
  const [aavRange, setAavRange] = useState<string>('all');
  const [warRange, setWarRange] = useState<string>('all');
  const [lengthRange, setLengthRange] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('aav');
  const [sortOrder, setSortOrder] = useState<string>('desc');
  const [search, setSearch] = useState<string>('');
  const [searchInput, setSearchInput] = useState<string>('');
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  const toggleRow = (contractId: number) => {
    setExpandedRows((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(contractId)) {
        newSet.delete(contractId);
      } else {
        newSet.add(contractId);
      }
      return newSet;
    });
  };

  // Parse range string to min/max
  const parseRange = (range: string): { min?: number; max?: number } => {
    if (range === 'all') return {};
    const [min, max] = range.split('-').map(Number);
    return { min, max };
  };

  const aavParsed = parseRange(aavRange);
  const warParsed = parseRange(warRange);
  const lengthParsed = parseRange(lengthRange);

  // Fetch contracts with SWR
  const { data, error, isLoading } = useSWR(
    ['contracts', page, position, aavRange, warRange, lengthRange, sortBy, sortOrder, search],
    () => getContracts({
      page,
      per_page: 20,
      position: position === 'All' ? undefined : position,
      aav_min: aavParsed.min,
      aav_max: aavParsed.max,
      war_min: warParsed.min,
      war_max: warParsed.max,
      length_min: lengthParsed.min,
      length_max: lengthParsed.max,
      sort_by: sortBy,
      sort_order: sortOrder,
      search: search || undefined,
    }),
    { keepPreviousData: true }
  );

  // Fetch summary stats (cached, doesn't change often)
  const { data: summary } = useSWR('contracts-summary', getContractsSummary);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
    setPage(1);
  };

  const clearFilters = () => {
    setPosition('All');
    setAavRange('all');
    setWarRange('all');
    setLengthRange('all');
    setSearchInput('');
    setSearch('');
    setPage(1);
  };

  const hasActiveFilters = position !== 'All' || aavRange !== 'all' || warRange !== 'all' || lengthRange !== 'all' || search;

  const SortIcon = ({ column }: { column: string }) => {
    if (sortBy !== column) return <span className="text-muted ml-1">↕</span>;
    return <span className="ml-1">{sortOrder === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <TooltipProvider>
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
                <Link href="/contracts" className="hover:text-primary-foreground/80 font-medium">Contracts</Link>
              </nav>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 py-8">
          {/* Stats Summary - Now at top */}
          {summary && (
            <div className="mb-6 grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="p-4 text-center">
                  <p className="text-2xl font-bold text-primary">{summary.total_contracts}</p>
                  <p className="text-sm text-muted-foreground">Total Contracts</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4 text-center">
                  <p className="text-2xl font-bold text-primary">{summary.year_min}-{summary.year_max}</p>
                  <p className="text-sm text-muted-foreground">Years Covered</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4 text-center">
                  <p className="text-2xl font-bold text-primary">{summary.unique_positions}</p>
                  <p className="text-sm text-muted-foreground">Positions</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4 text-center">
                  <p className="text-2xl font-bold text-primary">
                    {formatAAV(summary.aav_min)} - {formatAAV(summary.aav_max)}
                  </p>
                  <p className="text-sm text-muted-foreground">AAV Range</p>
                </CardContent>
              </Card>
            </div>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Historical Contracts Database</CardTitle>
            </CardHeader>
            <CardContent>
              {/* Filters */}
              <div className="flex flex-wrap gap-3 mb-6">
                {/* Search */}
                <div className="flex-1 min-w-[200px]">
                  <Input
                    type="text"
                    placeholder="Search by player name..."
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                  />
                </div>

                {/* Position Filter */}
                <Select value={position} onValueChange={(value) => { setPosition(value); setPage(1); }}>
                  <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="Position" />
                  </SelectTrigger>
                  <SelectContent>
                    {POSITIONS.map(pos => (
                      <SelectItem key={pos} value={pos}>
                        {pos === 'All' ? 'All Positions' : pos}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {/* AAV Range Filter */}
                <Select value={aavRange} onValueChange={(value) => { setAavRange(value); setPage(1); }}>
                  <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="AAV Range" />
                  </SelectTrigger>
                  <SelectContent>
                    {AAV_RANGES.map(range => (
                      <SelectItem key={range.value} value={range.value}>
                        {range.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {/* WAR Range Filter */}
                <Select value={warRange} onValueChange={(value) => { setWarRange(value); setPage(1); }}>
                  <SelectTrigger className="w-[130px]">
                    <SelectValue placeholder="WAR Range" />
                  </SelectTrigger>
                  <SelectContent>
                    {WAR_RANGES.map(range => (
                      <SelectItem key={range.value} value={range.value}>
                        {range.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {/* Length Range Filter */}
                <Select value={lengthRange} onValueChange={(value) => { setLengthRange(value); setPage(1); }}>
                  <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="Length" />
                  </SelectTrigger>
                  <SelectContent>
                    {LENGTH_RANGES.map(range => (
                      <SelectItem key={range.value} value={range.value}>
                        {range.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {/* Clear Filters */}
                {hasActiveFilters && (
                  <Button variant="ghost" size="sm" onClick={clearFilters} className="h-10">
                    <X className="h-4 w-4 mr-1" />
                    Clear
                  </Button>
                )}
              </div>

              {/* Error State */}
              {error && (
                <div className="text-center py-8 text-destructive">
                  <p>Failed to load contracts. Make sure the backend is running.</p>
                  <p className="text-sm mt-2">Backend URL: {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}</p>
                </div>
              )}

              {/* Loading State */}
              {isLoading && !data && (
                <div className="text-center py-8">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-primary border-t-transparent"></div>
                  <p className="mt-2 text-muted-foreground">Loading contracts...</p>
                </div>
              )}

              {/* Contracts Table */}
              {data && (
                <>
                  <div className="overflow-x-auto rounded-md border max-h-[600px] overflow-y-auto">
                    <Table>
                      <TableHeader className="sticky top-0 bg-background z-10">
                        <TableRow>
                          <TableHead
                            className="cursor-pointer hover:bg-muted/50"
                            onClick={() => handleSort('name')}
                          >
                            Player <SortIcon column="name" />
                          </TableHead>
                          <TableHead>Position</TableHead>
                          <TableHead
                            className="cursor-pointer hover:bg-muted/50"
                            onClick={() => handleSort('year')}
                          >
                            Year <SortIcon column="year" />
                          </TableHead>
                          <TableHead className="text-right">Age</TableHead>
                          <TableHead
                            className="text-right cursor-pointer hover:bg-muted/50"
                            onClick={() => handleSort('aav')}
                          >
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className="cursor-help border-b border-dotted border-muted-foreground">
                                  AAV <SortIcon column="aav" />
                                </span>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p className="max-w-xs">Average Annual Value - the contract&apos;s total value divided by its length</p>
                              </TooltipContent>
                            </Tooltip>
                          </TableHead>
                          <TableHead
                            className="text-right cursor-pointer hover:bg-muted/50"
                            onClick={() => handleSort('length')}
                          >
                            Years <SortIcon column="length" />
                          </TableHead>
                          <TableHead className="text-right">
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className="cursor-help border-b border-dotted border-muted-foreground">
                                  WAR (3yr)
                                </span>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p className="max-w-xs">Wins Above Replacement - 3-year average before signing. Higher is better (MVP ~7+, All-Star ~4-6, Starter ~2-3)</p>
                              </TooltipContent>
                            </Tooltip>
                          </TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.contracts.map((contract) => (
                          <React.Fragment key={contract.id}>
                            <TableRow
                              className="cursor-pointer hover:bg-muted/50"
                              onClick={() => toggleRow(contract.id)}
                            >
                              <TableCell className="font-medium">
                                <div className="flex items-center gap-2">
                                  {expandedRows.has(contract.id) ? (
                                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                  ) : (
                                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                  )}
                                  {contract.player_name}
                                </div>
                              </TableCell>
                              <TableCell>
                                <Badge variant="secondary">
                                  {contract.position}
                                </Badge>
                              </TableCell>
                              <TableCell>{contract.year_signed}</TableCell>
                              <TableCell className="text-right">{contract.age_at_signing}</TableCell>
                              <TableCell className="text-right font-mono">{formatAAV(contract.aav)}</TableCell>
                              <TableCell className="text-right">{contract.length}</TableCell>
                              <TableCell className="text-right">
                                {contract.war_3yr?.toFixed(1) ?? '-'}
                              </TableCell>
                            </TableRow>
                            <ExpandableStatsRow
                              contractId={contract.id}
                              playerName={contract.player_name}
                              position={contract.position}
                              isExpanded={expandedRows.has(contract.id)}
                            />
                          </React.Fragment>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  {/* Pagination */}
                  <div className="flex justify-between items-center mt-6">
                    <p className="text-sm text-muted-foreground">
                      Showing {((page - 1) * 20) + 1}-{Math.min(page * 20, data.total)} of {data.total} contracts
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1}
                      >
                        Previous
                      </Button>
                      <span className="px-4 py-2 text-muted-foreground">
                        Page {page} of {data.total_pages}
                      </span>
                      <Button
                        variant="outline"
                        onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
                        disabled={page >= data.total_pages}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </main>

        {/* Footer */}
        <footer className="bg-muted/50 border-t mt-12">
          <div className="max-w-7xl mx-auto px-4 py-6 text-center text-sm text-muted-foreground">
            <p>MLB Contract Advisor - For educational purposes only</p>
          </div>
        </footer>
      </div>
    </TooltipProvider>
  );
}
