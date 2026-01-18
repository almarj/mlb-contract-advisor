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
    // If player has an actual contract, compare predicted vs actual
    if (prediction.actual_aav !== null) {
      const diff = prediction.actual_aav - prediction.predicted_aav;
      const pctDiff = (diff / prediction.predicted_aav) * 100;

      if (Math.abs(pctDiff) < 15) {
        return { text: 'Fair Value', variant: 'success' as const, hasActual: true };
      } else if (pctDiff > 15) {
        return { text: 'Overpaid', variant: 'warning' as const, hasActual: true };
      } else {
        return { text: 'Underpaid', variant: 'info' as const, hasActual: true };
      }
    }

    // For free agents (no actual contract), show "Projected" instead
    return { text: 'Projected', variant: 'neutral' as const, hasActual: false };
  };

  const assessment = getAssessment();

  // Generate natural language assessment summary
  const generateSummary = (): string[] => {
    const sentences: string[] = [];
    const playerName = prediction.player_name;
    const predictedAAV = formatAAV(prediction.predicted_aav);
    const predictedLength = prediction.predicted_length;

    // Get top 2 features for explanation
    const topFeatures = Object.entries(prediction.feature_importance)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 2)
      .map(([name]) => formatFeatureName(name));

    // Count extensions in comparables
    const extensionCount = prediction.comparables.filter(c => c.is_extension).length;
    const totalComps = prediction.comparables.length;

    if (prediction.actual_aav !== null) {
      // Signed player - compare predicted vs actual
      const actualAAV = formatAAV(prediction.actual_aav);
      const diff = prediction.actual_aav - prediction.predicted_aav;
      const pctDiff = Math.abs((diff / prediction.predicted_aav) * 100);

      if (assessment.text === 'Fair Value') {
        sentences.push(
          `${playerName}'s ${actualAAV} AAV is within ${pctDiff.toFixed(0)}% of our model's predicted ${predictedAAV}, suggesting the contract reflects fair market value based on performance.`
        );
      } else if (assessment.text === 'Overpaid') {
        sentences.push(
          `${playerName}'s ${actualAAV} AAV is ${pctDiff.toFixed(0)}% above our model's predicted ${predictedAAV}. This may reflect factors like marketability, team needs, or bidding competition not captured in performance metrics.`
        );
      } else {
        sentences.push(
          `${playerName}'s ${actualAAV} AAV is ${pctDiff.toFixed(0)}% below our model's predicted ${predictedAAV}, suggesting the player may have been undervalued or accepted a team-friendly deal.`
        );
      }
    } else {
      // Prospect/free agent - projection only
      sentences.push(
        `Based on recent performance, ${playerName} projects to a ${predictedLength}-year contract worth approximately ${predictedAAV} per year on the open market.`
      );
    }

    // Add feature explanation
    if (topFeatures.length >= 2) {
      sentences.push(
        `This prediction is primarily driven by ${topFeatures[0]} and ${topFeatures[1]}.`
      );
    }

    // Add extension caveat if relevant
    if (extensionCount > 0) {
      sentences.push(
        `Note: ${extensionCount} of ${totalComps} comparable contracts are pre-free agency extensions, which typically have below-market AAVs.`
      );
    }

    return sentences;
  };

  const summaryParagraphs = generateSummary();

  const getBadgeClass = (variant: 'success' | 'warning' | 'info' | 'neutral') => {
    switch (variant) {
      case 'success':
        return 'bg-green-100 text-green-700 hover:bg-green-100';
      case 'warning':
        return 'bg-orange-100 text-orange-700 hover:bg-orange-100';
      case 'info':
        return 'bg-blue-100 text-blue-700 hover:bg-blue-100';
      case 'neutral':
        return 'bg-gray-100 text-gray-700 hover:bg-gray-100';
    }
  };

  return (
    <div className="space-y-6">
      {/* Main Prediction */}
      <Card className="bg-muted/50">
        <CardContent className="text-center py-8">
          <p className="text-sm text-muted-foreground mb-2">Predicted Contract Value (AAV)</p>
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

      {/* Actual Contract Comparison (if player has signed) */}
      {prediction.actual_aav !== null && (
        <Card className="border-2 border-dashed">
          <CardContent className="py-6">
            <div className="grid grid-cols-2 gap-6">
              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-1">Model Predicted</p>
                <p className="text-2xl font-bold font-mono text-primary">
                  {formatAAV(prediction.predicted_aav)}
                </p>
                <p className="text-sm text-muted-foreground">
                  {prediction.predicted_length} year{prediction.predicted_length !== 1 ? 's' : ''}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-1">Actual Contract</p>
                <p className="text-2xl font-bold font-mono">
                  {formatAAV(prediction.actual_aav)}
                </p>
                <p className="text-sm text-muted-foreground">
                  {prediction.actual_length} year{prediction.actual_length !== 1 ? 's' : ''}
                </p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground text-center mt-4">
              Difference: {formatAAV(Math.abs(prediction.actual_aav - prediction.predicted_aav))}
              {' '}({prediction.actual_aav > prediction.predicted_aav ? '+' : '-'}
              {Math.abs(((prediction.actual_aav - prediction.predicted_aav) / prediction.predicted_aav) * 100).toFixed(0)}%)
            </p>
          </CardContent>
        </Card>
      )}

      {/* Assessment Summary */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Assessment Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {summaryParagraphs.map((paragraph, idx) => (
              <p key={idx} className={idx === summaryParagraphs.length - 1 && paragraph.startsWith('Note:')
                ? 'text-sm text-muted-foreground italic'
                : 'text-sm text-foreground'
              }>
                {paragraph}
              </p>
            ))}
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
                  <TableRow key={idx} className={comp.is_extension ? 'opacity-70' : ''}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        {comp.name}
                        {comp.is_extension && (
                          <Badge variant="outline" className="text-xs bg-purple-50 text-purple-700 border-purple-200">
                            Extension
                          </Badge>
                        )}
                      </div>
                    </TableCell>
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
