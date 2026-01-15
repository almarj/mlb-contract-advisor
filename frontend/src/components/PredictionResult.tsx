'use client';

import { PredictionResponse, formatAAV } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface PredictionResultProps {
  prediction: PredictionResponse;
  showAdvanced: boolean;
}

export default function PredictionResult({ prediction, showAdvanced }: PredictionResultProps) {
  const getAssessment = () => {
    // Simple assessment based on comparable contracts
    const avgComparableAAV = prediction.comparables.length > 0
      ? prediction.comparables.reduce((sum, c) => sum + c.aav, 0) / prediction.comparables.length
      : prediction.predicted_aav;

    const diff = prediction.predicted_aav - avgComparableAAV;
    const pctDiff = (diff / avgComparableAAV) * 100;

    if (Math.abs(pctDiff) < 10) {
      return { text: 'Fair Value', variant: 'success' as const };
    } else if (pctDiff > 10) {
      return { text: 'Premium Value', variant: 'warning' as const };
    } else {
      return { text: 'Below Market', variant: 'info' as const };
    }
  };

  const assessment = getAssessment();

  const getBadgeClass = (variant: 'success' | 'warning' | 'info') => {
    switch (variant) {
      case 'success':
        return 'bg-green-100 text-green-700 hover:bg-green-100';
      case 'warning':
        return 'bg-orange-100 text-orange-700 hover:bg-orange-100';
      case 'info':
        return 'bg-blue-100 text-blue-700 hover:bg-blue-100';
    }
  };

  return (
    <div className="space-y-6">
      {/* Main Prediction */}
      <Card className="bg-muted/50">
        <CardContent className="text-center py-8">
          <p className="text-sm text-muted-foreground mb-2">Predicted Contract Value</p>
          <p className="text-5xl font-bold text-primary font-mono">
            {formatAAV(prediction.predicted_aav)}
          </p>
          <p className="text-lg text-foreground mt-2">
            {prediction.predicted_length} year{prediction.predicted_length !== 1 ? 's' : ''}
          </p>
          <div className="mt-4">
            <Badge className={getBadgeClass(assessment.variant)}>
              {assessment.text}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Confidence & Range */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-sm text-muted-foreground">Low Estimate</p>
            <p className="text-xl font-semibold font-mono">{formatAAV(prediction.predicted_aav_low)}</p>
          </CardContent>
        </Card>
        <Card className="bg-primary/5 border-primary/20">
          <CardContent className="p-4 text-center">
            <p className="text-sm text-muted-foreground">Confidence</p>
            <p className="text-xl font-semibold text-primary">{prediction.confidence_score.toFixed(0)}%</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-sm text-muted-foreground">High Estimate</p>
            <p className="text-xl font-semibold font-mono">{formatAAV(prediction.predicted_aav_high)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Comparable Players */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Comparable Contracts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Player</TableHead>
                  <TableHead>Year</TableHead>
                  <TableHead className="text-right">AAV</TableHead>
                  <TableHead className="text-right">Years</TableHead>
                  <TableHead className="text-right">WAR</TableHead>
                  <TableHead className="text-right">Match</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {prediction.comparables.map((comp, idx) => (
                  <TableRow key={idx}>
                    <TableCell className="font-medium">{comp.name}</TableCell>
                    <TableCell>{comp.year_signed}</TableCell>
                    <TableCell className="text-right font-mono">{formatAAV(comp.aav)}</TableCell>
                    <TableCell className="text-right">{comp.length}</TableCell>
                    <TableCell className="text-right">{comp.war_3yr.toFixed(1)}</TableCell>
                    <TableCell className="text-right">
                      <Badge
                        variant="outline"
                        className={
                          comp.similarity_score >= 90 ? 'bg-green-100 text-green-700 border-green-200' :
                          comp.similarity_score >= 80 ? 'bg-yellow-100 text-yellow-700 border-yellow-200' :
                          'bg-gray-100 text-gray-700 border-gray-200'
                        }
                      >
                        {comp.similarity_score.toFixed(0)}%
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Feature Importance (Advanced Mode) */}
      {showAdvanced && Object.keys(prediction.feature_importance).length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">What Drives This Prediction</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(prediction.feature_importance)
                .sort(([, a], [, b]) => b - a)
                .map(([feature, importance]) => (
                  <div key={feature} className="flex items-center gap-3">
                    <span className="w-24 text-sm text-muted-foreground truncate">{formatFeatureName(feature)}</span>
                    <div className="flex-1 bg-muted rounded-full h-3">
                      <div
                        className="bg-primary h-3 rounded-full transition-all"
                        style={{ width: `${importance * 100}%` }}
                      />
                    </div>
                    <span className="w-12 text-sm text-right font-medium">{(importance * 100).toFixed(0)}%</span>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Model Info */}
      <p className="text-sm text-muted-foreground text-center pt-4 border-t">
        Model accuracy: {prediction.model_accuracy.toFixed(1)}% within $5M
      </p>
    </div>
  );
}

function formatFeatureName(name: string): string {
  const nameMap: Record<string, string> = {
    'WAR_3yr': 'WAR',
    'wRC_plus_3yr': 'wRC+',
    'HR_3yr': 'Home Runs',
    'age_at_signing': 'Age',
    'year_signed': 'Year',
    'barrel_rate': 'Barrel %',
    'avg_exit_velo': 'Exit Velo',
    'SLG_3yr': 'Slugging',
    'OBP_3yr': 'OBP',
    'ERA_3yr': 'ERA',
    'FIP_3yr': 'FIP',
    'K_9_3yr': 'K/9',
    'IP_3yr': 'Innings',
  };
  return nameMap[name] || name.replace(/_/g, ' ');
}
