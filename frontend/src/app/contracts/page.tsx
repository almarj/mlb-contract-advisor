'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
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
import { ChevronDown, ChevronRight } from 'lucide-react';
import { ExpandableStatsRow } from '@/components/ExpandableStatsRow';

const POSITIONS = ['All', 'OF', '1B', '2B', '3B', 'SS', 'C', 'DH', 'SP', 'RP'];

export default function ContractsPage() {
  const [page, setPage] = useState(1);
  const [position, setPosition] = useState<string>('All');
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

  // Fetch contracts with SWR
  const { data, error, isLoading } = useSWR(
    ['contracts', page, position, sortBy, sortOrder, search],
    () => getContracts({
      page,
      per_page: 20,
      position: position === 'All' ? undefined : position,
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

  const SortIcon = ({ column }: { column: string }) => {
    if (sortBy !== column) return <span className="text-muted ml-1">↕</span>;
    return <span className="ml-1">{sortOrder === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-primary text-primary-foreground">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold">MLB Contract Advisor</h1>
              <p className="text-primary-foreground/70 text-sm">AI-Powered Contract Predictions</p>
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
        <Card>
          <CardHeader>
            <CardTitle>Historical Contracts Database</CardTitle>
          </CardHeader>
          <CardContent>
            {/* Filters */}
            <div className="flex flex-wrap gap-4 mb-6">
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
                <SelectTrigger className="w-[180px]">
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
                <div className="overflow-x-auto rounded-md border">
                  <Table>
                    <TableHeader>
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
                          AAV <SortIcon column="aav" />
                        </TableHead>
                        <TableHead
                          className="text-right cursor-pointer hover:bg-muted/50"
                          onClick={() => handleSort('length')}
                        >
                          Years <SortIcon column="length" />
                        </TableHead>
                        <TableHead className="text-right">WAR (3yr)</TableHead>
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

        {/* Stats Summary */}
        {summary && (
          <div className="mt-8 grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-2xl font-bold text-primary">{summary.total_contracts}</p>
                <p className="text-sm text-muted-foreground">Total Contracts</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-2xl font-bold text-green-600">{summary.year_min}-{summary.year_max}</p>
                <p className="text-sm text-muted-foreground">Years Covered</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-2xl font-bold text-purple-600">{summary.unique_positions}</p>
                <p className="text-sm text-muted-foreground">Positions</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-2xl font-bold text-orange-600">
                  {formatAAV(summary.aav_min)} - {formatAAV(summary.aav_max)}
                </p>
                <p className="text-sm text-muted-foreground">AAV Range</p>
              </CardContent>
            </Card>
          </div>
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
