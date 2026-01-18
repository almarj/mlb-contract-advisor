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
  // Calculate assessment comparing actual vs predicted
  const getAssessment = (actualAAV: number | null, predictedAAV: number) => {
    if (actualAAV === null) {
      return { text: 'Projected', variant: 'neutral' as const, pctDiff: 0 };
    }
    const diff = actualAAV - predictedAAV;
    const pctDiff = (diff / predictedAAV) * 100;

    if (Math.abs(pctDiff) < 10) {
      return { text: 'Fair Value', variant: 'success' as const, pctDiff };
    } else if (pctDiff > 10) {
      return { text: 'Overpaid', variant: 'warning' as const, pctDiff };
    } else {
      return { text: 'Underpaid', variant: 'info' as const, pctDiff };
    }
  };

  // Assessment at signing (actual vs predicted based on pre-signing stats)
  const assessmentAtSigning = getAssessment(prediction.actual_aav, prediction.predicted_aav);

  // Assessment based on recent performance (actual vs predicted based on recent stats)
  const assessmentRecent = prediction.predicted_aav_recent !== null
    ? getAssessment(prediction.actual_aav, prediction.predicted_aav_recent)
    : null;

  // For backwards compatibility
  const assessment = assessmentAtSigning;

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
      // Signed player - compare predicted vs actual at signing
      const actualAAV = formatAAV(prediction.actual_aav);
      const diff = prediction.actual_aav - prediction.predicted_aav;
      const pctDiff = Math.abs((diff / prediction.predicted_aav) * 100);

      if (assessment.text === 'Fair Value') {
        sentences.push(
          `At signing, ${playerName}'s ${actualAAV} AAV was within ${pctDiff.toFixed(0)}% of our model's predicted ${predictedAAV}, suggesting the contract reflected fair market value at the time.`
        );
      } else if (assessment.text === 'Overpaid') {
        sentences.push(
          `At signing, ${playerName}'s ${actualAAV} AAV was ${pctDiff.toFixed(0)}% above our model's predicted ${predictedAAV}. This may reflect factors like marketability, team needs, or bidding competition not captured in performance metrics.`
        );
      } else {
        sentences.push(
          `At signing, ${playerName}'s ${actualAAV} AAV was ${pctDiff.toFixed(0)}% below our model's predicted ${predictedAAV}, suggesting the player may have been undervalued or accepted a team-friendly deal.`
        );
      }

      // Add recent performance analysis if available
      if (prediction.predicted_aav_recent !== null && assessmentRecent) {
        const recentPredictedAAV = formatAAV(prediction.predicted_aav_recent);
        const recentDiff = prediction.actual_aav - prediction.predicted_aav_recent;
        const recentPctDiff = Math.abs((recentDiff / prediction.predicted_aav_recent) * 100);

        if (assessmentRecent.text === 'Fair Value') {
          sentences.push(
            `Based on recent performance (2023-2025), the model would predict ${recentPredictedAAV}, which is still close to the actual contract value.`
          );
        } else if (assessmentRecent.text === 'Overpaid') {
          sentences.push(
            `However, based on recent performance (2023-2025), the model would only predict ${recentPredictedAAV} — making the contract ${recentPctDiff.toFixed(0)}% above current value.`
          );
        } else {
          sentences.push(
            `Based on recent performance (2023-2025), the model would predict ${recentPredictedAAV}, meaning the player has outperformed the contract by ${recentPctDiff.toFixed(0)}%.`
          );
        }
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
      {/* Contract Assessment (for signed players) */}
      {prediction.actual_aav !== null ? (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Contract Assessment</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* At Signing Assessment */}
              <div className="border rounded-lg p-4 text-center">
                <p className="text-sm font-medium text-muted-foreground mb-2">At Signing</p>
                <Badge className={`${getBadgeClass(assessmentAtSigning.variant)} mb-3`}>
                  {assessmentAtSigning.text}
                </Badge>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Actual AAV</p>
                  <p className="text-lg font-bold font-mono">{formatAAV(prediction.actual_aav)}</p>
                  <p className="text-xs text-muted-foreground mt-2">Model Predicted</p>
                  <p className="text-lg font-semibold font-mono text-primary">{formatAAV(prediction.predicted_aav)}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {assessmentAtSigning.pctDiff > 0 ? '+' : ''}{assessmentAtSigning.pctDiff.toFixed(0)}% vs prediction
                  </p>
                </div>
              </div>

              {/* Recent Performance Assessment */}
              {assessmentRecent && prediction.predicted_aav_recent !== null && (
                <div className="border rounded-lg p-4 text-center">
                  <p className="text-sm font-medium text-muted-foreground mb-2">Based on Recent Performance</p>
                  <Badge className={`${getBadgeClass(assessmentRecent.variant)} mb-3`}>
                    {assessmentRecent.text}
                  </Badge>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Actual AAV</p>
                    <p className="text-lg font-bold font-mono">{formatAAV(prediction.actual_aav)}</p>
                    <p className="text-xs text-muted-foreground mt-2">Would Predict Today</p>
                    <p className="text-lg font-semibold font-mono text-primary">{formatAAV(prediction.predicted_aav_recent)}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {assessmentRecent.pctDiff > 0 ? '+' : ''}{assessmentRecent.pctDiff.toFixed(0)}% vs prediction
                    </p>
                  </div>
                </div>
              )}

              {/* Fallback if no recent stats */}
              {!assessmentRecent && (
                <div className="border rounded-lg p-4 text-center border-dashed opacity-50">
                  <p className="text-sm font-medium text-muted-foreground mb-2">Based on Recent Performance</p>
                  <p className="text-sm text-muted-foreground">No recent stats available</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        /* Main Prediction (for prospects/unsigned players only) */
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
      )}

      {/* Performance Since Signing (only show if we have recent stats) */}
      {prediction.actual_aav !== null && prediction.recent_war_3yr !== null && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Performance Since Signing</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-6">
              <div className="text-center border-r">
                <p className="text-sm font-medium text-muted-foreground mb-3">At Signing</p>
                <div className="space-y-2">
                  <div>
                    <p className="text-xs text-muted-foreground">WAR (3yr avg)</p>
                    <p className="text-lg font-semibold">{prediction.signing_war_3yr?.toFixed(1) ?? 'N/A'}</p>
                  </div>
                  {prediction.signing_wrc_plus_3yr !== null && (
                    <div>
                      <p className="text-xs text-muted-foreground">wRC+</p>
                      <p className="text-lg font-semibold">{prediction.signing_wrc_plus_3yr?.toFixed(0)}</p>
                    </div>
                  )}
                  {prediction.signing_era_3yr !== null && (
                    <div>
                      <p className="text-xs text-muted-foreground">ERA</p>
                      <p className="text-lg font-semibold">{prediction.signing_era_3yr?.toFixed(2)}</p>
                    </div>
                  )}
                </div>
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-muted-foreground mb-3">Recent (2023-2025)</p>
                <div className="space-y-2">
                  <div>
                    <p className="text-xs text-muted-foreground">WAR (3yr avg)</p>
                    <p className={`text-lg font-semibold ${
                      prediction.recent_war_3yr !== null && prediction.signing_war_3yr !== null
                        ? prediction.recent_war_3yr < prediction.signing_war_3yr * 0.5
                          ? 'text-red-600'
                          : prediction.recent_war_3yr > prediction.signing_war_3yr
                            ? 'text-green-600'
                            : ''
                        : ''
                    }`}>
                      {prediction.recent_war_3yr?.toFixed(1) ?? 'N/A'}
                    </p>
                  </div>
                  {prediction.recent_wrc_plus_3yr !== null && (
                    <div>
                      <p className="text-xs text-muted-foreground">wRC+</p>
                      <p className={`text-lg font-semibold ${
                        prediction.recent_wrc_plus_3yr !== null && prediction.signing_wrc_plus_3yr !== null
                          ? prediction.recent_wrc_plus_3yr < prediction.signing_wrc_plus_3yr * 0.7
                            ? 'text-red-600'
                            : prediction.recent_wrc_plus_3yr > prediction.signing_wrc_plus_3yr
                              ? 'text-green-600'
                              : ''
                          : ''
                      }`}>
                        {prediction.recent_wrc_plus_3yr?.toFixed(0)}
                      </p>
                    </div>
                  )}
                  {prediction.recent_era_3yr !== null && (
                    <div>
                      <p className="text-xs text-muted-foreground">ERA</p>
                      <p className={`text-lg font-semibold ${
                        prediction.recent_era_3yr !== null && prediction.signing_era_3yr !== null
                          ? prediction.recent_era_3yr > prediction.signing_era_3yr * 1.5
                            ? 'text-red-600'
                            : prediction.recent_era_3yr < prediction.signing_era_3yr
                              ? 'text-green-600'
                              : ''
                          : ''
                      }`}>
                        {prediction.recent_era_3yr?.toFixed(2)}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
            <p className="text-xs text-muted-foreground text-center mt-4 italic">
              Compares stats at time of signing vs recent performance
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

      {/* Comparable Players (At Signing) */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Comparable Contracts (At Signing)</CardTitle>
          <p className="text-sm text-muted-foreground">Players with similar stats when they signed</p>
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

      {/* Comparable Players (Based on Recent Performance) */}
      {prediction.comparables_recent && prediction.comparables_recent.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Comparable Contracts (Recent Performance)</CardTitle>
            <p className="text-sm text-muted-foreground">Players with similar stats to recent 2023-2025 performance</p>
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
                  {prediction.comparables_recent.map((comp, idx) => (
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
      )}

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
    'max_exit_velo': 'Max Exit Velo',
    'hard_hit_pct': 'Hard Hit %',
    'SLG_3yr': 'Slugging',
    'OBP_3yr': 'OBP',
    'AVG_3yr': 'Batting Avg',
    'ERA_3yr': 'ERA',
    'FIP_3yr': 'FIP',
    'K_9_3yr': 'K/9',
    'BB_9_3yr': 'BB/9',
    'IP_3yr': 'Innings',
    // Plate discipline (batters)
    'chase_rate': 'Chase Rate',
    'whiff_rate': 'Whiff Rate',
    // Pitcher Statcast
    'fb_velocity': 'FB Velocity',
    'fb_spin': 'FB Spin',
    'xera': 'xERA',
    'k_percent': 'K%',
    'bb_percent': 'BB%',
    'whiff_percent_pitcher': 'Whiff%',
    'chase_percent_pitcher': 'Chase%',
    'is_starter': 'Starter',
  };
  return nameMap[name] || name.replace(/_/g, ' ');
}
