'use client';

import { useRouter } from 'next/navigation';
import { ChatResponse, ChatActionType, formatAAV } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ExternalLink, AlertCircle, Sparkles } from 'lucide-react';

interface NLResponseProps {
  response: ChatResponse;
  displayMode?: 'card' | 'chat-bubble';
  onClear?: () => void;
}

export function NLResponse({
  response,
  displayMode = 'card',
  onClear
}: NLResponseProps) {
  const router = useRouter();

  const handleAction = (action: typeof response.actions[0]) => {
    switch (action.action_type) {
      case ChatActionType.VIEW_PREDICTION:
        if (action.target_player) {
          router.push(`/?player=${encodeURIComponent(action.target_player)}`);
        }
        break;
      case ChatActionType.COMPARE_PLAYERS:
        const { player1, player2 } = action.parameters;
        if (player1 && player2) {
          router.push(`/compare?p1=${encodeURIComponent(player1)}&p2=${encodeURIComponent(player2)}`);
        } else {
          router.push('/compare');
        }
        break;
      case ChatActionType.SHOW_CONTRACTS:
        const params = new URLSearchParams(action.parameters);
        router.push(`/contracts?${params.toString()}`);
        break;
    }
  };

  // Parse the response text to remove action markers for display
  const cleanResponse = response.response.replace(/\[ACTION:[^\]]+\]/g, '').trim();

  // Get prediction summary if available
  const prediction = response.prediction;
  const hasPrediction = prediction && response.player_found;

  if (displayMode === 'chat-bubble') {
    // Future: Chat bubble style for full chat panel
    return (
      <div className="bg-muted/50 rounded-lg p-4 max-w-[80%]">
        <p className="text-sm whitespace-pre-wrap">{cleanResponse}</p>
      </div>
    );
  }

  // Card display mode (default)
  return (
    <Card className="border-primary/20 bg-gradient-to-br from-background to-muted/30">
      <CardContent className="p-4 sm:p-6">
        {/* Header with player info */}
        {hasPrediction && (
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold">
                {response.player_name}
              </h3>
              <p className="text-sm text-muted-foreground">
                {response.is_two_way_player ? 'DH + SP (Two-Way)' : prediction.position}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {response.used_fallback && (
                <Badge variant="outline" className="text-xs">
                  <AlertCircle className="h-3 w-3 mr-1" />
                  Limited
                </Badge>
              )}
              {!response.used_fallback && (
                <Badge variant="secondary" className="text-xs">
                  <Sparkles className="h-3 w-3 mr-1" />
                  AI Analysis
                </Badge>
              )}
            </div>
          </div>
        )}

        {/* Prediction summary - Two-way player version */}
        {hasPrediction && response.is_two_way_player && response.two_way_predictions && (
          <div className="bg-primary/5 rounded-lg p-3 sm:p-4 mb-4">
            <div className="mb-3">
              <Badge variant="secondary" className="text-xs mb-2">
                Two-Way Player
              </Badge>
            </div>
            {/* Individual role predictions */}
            <div className="grid grid-cols-2 gap-2 sm:gap-4 mb-4">
              {response.two_way_predictions.map((pred) => (
                <div key={pred.role} className="bg-background/50 rounded-lg p-2 sm:p-3 text-center">
                  <p className="text-xs font-medium text-muted-foreground mb-1">
                    As {pred.role}
                  </p>
                  <p className="text-lg sm:text-xl font-bold font-mono text-primary">
                    ${pred.predicted_aav.toFixed(1)}M
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {pred.predicted_length}yr • {pred.confidence_score.toFixed(0)}%
                  </p>
                </div>
              ))}
            </div>
            {/* Combined value */}
            <div className="border-t pt-3 text-center">
              <p className="text-xs text-muted-foreground mb-1">Combined Value</p>
              <p className="text-xl sm:text-2xl font-bold font-mono text-primary">
                ${response.combined_aav?.toFixed(1)}M
              </p>
              <p className="text-xs text-muted-foreground">per year</p>
            </div>
          </div>
        )}

        {/* Prediction summary - Standard player version */}
        {hasPrediction && !response.is_two_way_player && (
          <div className="bg-primary/5 rounded-lg p-3 sm:p-4 mb-4">
            <div className="grid grid-cols-3 gap-2 sm:gap-4 text-center">
              <div>
                <p className="text-lg sm:text-2xl font-bold font-mono text-primary">
                  {formatAAV(prediction.predicted_aav)}
                </p>
                <p className="text-xs text-muted-foreground">Predicted AAV</p>
              </div>
              <div>
                <p className="text-lg sm:text-2xl font-bold">
                  {prediction.predicted_length}
                </p>
                <p className="text-xs text-muted-foreground">Years</p>
              </div>
              <div>
                <p className="text-lg sm:text-2xl font-bold">
                  {prediction.confidence_score.toFixed(0)}%
                </p>
                <p className="text-xs text-muted-foreground">Confidence</p>
              </div>
            </div>
          </div>
        )}

        {/* AI explanation */}
        <div className="prose prose-sm max-w-none">
          <p className="text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed">
            {cleanResponse}
          </p>
        </div>

        {/* Suggestions if player not found */}
        {!response.player_found && response.suggestions.length > 0 && (
          <div className="mt-4 p-3 bg-muted/50 rounded-lg">
            <p className="text-sm font-medium mb-2">Did you mean:</p>
            <div className="flex flex-wrap gap-2">
              {response.suggestions.map((suggestion) => (
                <Button
                  key={suggestion}
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    // Trigger a new search with this player
                    router.push(`/?player=${encodeURIComponent(suggestion)}`);
                  }}
                >
                  {suggestion}
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* Action buttons */}
        {response.actions.length > 0 && (
          <div className="mt-4 pt-4 border-t flex flex-wrap gap-2">
            {response.actions.map((action, index) => (
              <Button
                key={index}
                variant={index === 0 ? 'default' : 'outline'}
                size="sm"
                onClick={() => handleAction(action)}
              >
                {action.action_type === ChatActionType.VIEW_PREDICTION && (
                  <>
                    <span className="hidden sm:inline">View Full Prediction</span>
                    <span className="sm:hidden">Full Details</span>
                    <ExternalLink className="h-3 w-3 ml-1" />
                  </>
                )}
                {action.action_type === ChatActionType.COMPARE_PLAYERS && (
                  <>
                    <span className="hidden sm:inline">Compare Players</span>
                    <span className="sm:hidden">Compare</span>
                  </>
                )}
                {action.action_type === ChatActionType.SHOW_CONTRACTS && (
                  <>
                    <span className="hidden sm:inline">Browse Contracts</span>
                    <span className="sm:hidden">Contracts</span>
                  </>
                )}
              </Button>
            ))}
            {onClear && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onClear}
                className="ml-auto"
              >
                Clear
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
