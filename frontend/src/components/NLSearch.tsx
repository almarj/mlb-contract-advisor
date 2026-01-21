'use client';

import { useState, useRef, useEffect } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface NLSearchProps {
  variant?: 'inline' | 'chat' | 'header';
  onSubmit: (query: string) => void;
  isLoading: boolean;
  placeholder?: string;
}

export function NLSearch({
  variant = 'inline',
  onSubmit,
  isLoading,
  placeholder = 'Ask questions about contracts or player value...'
}: NLSearchProps) {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input on Cmd+K (future enhancement)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit(query.trim());
    }
  };

  // Different styles based on variant
  const containerClasses = {
    inline: 'w-full',
    chat: 'w-full',
    header: 'w-80 md:w-96',
  };

  return (
    <form
      onSubmit={handleSubmit}
      className={containerClasses[variant]}
      role="search"
      aria-label="Quick player search"
    >
      <div className="relative flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
            disabled={isLoading}
            className="pl-10 pr-4 h-11"
            aria-label="Search query"
          />
        </div>
        <Button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="h-11 px-6"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Analyzing...
            </>
          ) : (
            'Ask'
          )}
        </Button>
      </div>

      {/* Example queries - only show for inline variant when not loading */}
      {variant === 'inline' && !isLoading && !query && (
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <span>Try:</span>
          <button
            type="button"
            onClick={() => setQuery('Is Juan Soto overpaid?')}
            className="hover:text-foreground hover:underline"
          >
            Soto&apos;s contract
          </button>
          <button
            type="button"
            onClick={() => setQuery('What is Shohei Ohtani worth?')}
            className="hover:text-foreground hover:underline"
          >
            Ohtani&apos;s value
          </button>
          <button
            type="button"
            onClick={() => setQuery('How good is Mookie Betts?')}
            className="hover:text-foreground hover:underline"
          >
            Betts&apos; stats
          </button>
        </div>
      )}
    </form>
  );
}
