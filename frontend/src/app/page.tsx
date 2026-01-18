'use client';

import { useState } from 'react';
import Link from 'next/link';
import PredictionForm from '@/components/PredictionForm';
import PredictionResult from '@/components/PredictionResult';
import { PredictionResponse, PredictionRequest, createPrediction } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export default function Home() {
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = async (data: PredictionRequest) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await createPrediction(data);
      setPrediction(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Prediction failed');
    } finally {
      setIsLoading(false);
    }
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
              <Link href="/" className="hover:text-primary-foreground/80 font-medium">Predict</Link>
              <Link href="/contracts" className="hover:text-primary-foreground/80">Contracts</Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* How It Works Section */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="text-center">How It Works</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="text-center">
                <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-primary font-bold text-lg">1</span>
                </div>
                <h3 className="font-medium mb-2">Enter Name</h3>
                <p className="text-sm text-muted-foreground">
                  Search for any MLB player and their stats will auto-fill from our database
                </p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-primary font-bold text-lg">2</span>
                </div>
                <h3 className="font-medium mb-2">AI Analysis</h3>
                <p className="text-sm text-muted-foreground">
                  Our ML model analyzes 450+ historical contracts to find patterns
                </p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-primary font-bold text-lg">3</span>
                </div>
                <h3 className="font-medium mb-2">Get Prediction</h3>
                <p className="text-sm text-muted-foreground">
                  Receive AAV estimate, contract length, and comparable players
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Mode Toggle */}
        <div className="flex justify-end mb-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <span className="text-sm text-muted-foreground">Simple</span>
            <div className="relative">
              <input
                type="checkbox"
                checked={showAdvanced}
                onChange={(e) => setShowAdvanced(e.target.checked)}
                className="sr-only"
              />
              <div className={`w-10 h-6 rounded-full transition-colors ${showAdvanced ? 'bg-primary' : 'bg-muted'}`}>
                <div className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${showAdvanced ? 'translate-x-5' : 'translate-x-1'}`} />
              </div>
            </div>
            <span className="text-sm text-muted-foreground">Advanced</span>
          </label>
        </div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left: Form */}
          <Card>
            <CardHeader>
              <CardTitle>Player Stats</CardTitle>
            </CardHeader>
            <CardContent>
              <PredictionForm
                onSubmit={handleSubmit}
                isLoading={isLoading}
              />
              {error && (
                <div className="mt-4 p-3 bg-destructive/10 text-destructive rounded-lg text-sm">
                  {error}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Right: Results */}
          <Card>
            <CardHeader>
              <CardTitle>Prediction Results</CardTitle>
            </CardHeader>
            <CardContent>
              {prediction ? (
                <PredictionResult
                  prediction={prediction}
                  showAdvanced={showAdvanced}
                />
              ) : (
                <div className="text-center py-16 text-muted-foreground">
                  <svg className="w-16 h-16 mx-auto mb-4 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  <p>Enter player stats to see contract prediction</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Model Info */}
        <div className="mt-8 text-center text-sm text-muted-foreground">
          <p>Model trained on 450 MLB contracts from 2015-2024</p>
          <p>Accuracy: 74% of predictions within $5M of actual AAV</p>
        </div>
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
