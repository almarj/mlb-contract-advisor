# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MLB Contract Advisor is a Python-based ML pipeline that predicts MLB player contract values (AAV and contract length) using historical contract data and player performance metrics.

## Tech Stack

- **Python 3** with scikit-learn for ML models
- **Data Sources**: FanGraphs API, Baseball Savant (Statcast), Spotrac CSV imports
- **Libraries**: pandas, numpy, matplotlib, scikit-learn, joblib

## Dependencies

Install manually:
```bash
pip install pybaseball pandas numpy matplotlib scikit-learn joblib
```

## Running the Full Pipeline

Execute scripts from the project root in this order:

```bash
# 1. Collect FanGraphs batting/pitching stats (2015-2025)
python Data/collect_all_data_expanded.py

# 2. Integrate all sources with Spotrac contracts
python Data/integrate_with_spotrac_improved.py

# 3. Train ML models
python Data/train_contract_model.py

# 4. Generate visualizations and analysis
python Data/quick_analysis.py
```

**Note**: First run takes 10-15 minutes; subsequent runs use cached data.

## Architecture

```
Data Collection → Integration → ML Training → API (future)
     │                │              │
     ├─ FanGraphs     │              └─ train_contract_model.py
     ├─ Statcast      │                   (4 Gradient Boosting models)
     └─ Spotrac       │
                      │
        integrate_with_spotrac_improved.py
              │
              └─ master_contract_dataset.csv (450 contracts)
```

### Data Flow

1. **Collection Scripts** pull from APIs:
   - `collect_all_data_expanded.py`: WAR, wRC+, ERA, batting/pitching stats (qual=50 PA / 10 IP)
   - Statcast collected during integration: Exit velocity, barrel rate, hard hit %

2. **Integration Script** (`integrate_with_spotrac_improved.py`):
   - Loads Spotrac contract CSV
   - Matches players using normalized names (handles accents, suffixes)
   - Calculates 3-year average stats (years: year_signed-3 to year_signed-1)
   - Adds Statcast metrics where available (~46% coverage)
   - Outputs: `Data/Master Data/master_contract_dataset.csv`

3. **ML Training** (`train_contract_model.py`):
   - Trains 4 Gradient Boosting models:
     - Batter AAV, Batter Length
     - Pitcher AAV, Pitcher Length
   - Outputs models to `Data/Models/`

### Key Integration Logic

```python
# Position determines pitcher vs batter
is_pitcher = position in ['SP', 'RP', 'P', 'CL']

# Stats averaged from 3 years before signing
years_to_avg = [year_signed - 3, year_signed - 2, year_signed - 1]
```

## Output Files

Located in `Data/Master Data/`:
- `master_contract_dataset.csv` - Training dataset (450 contracts)
- `failed_matches.csv` - Contracts that couldn't be matched (15)
- `*.png` - Visualization plots and feature importance charts

Located in `Data/Models/`:
- `*_model.joblib` - Trained Gradient Boosting models
- `*_scaler.joblib` - StandardScaler for each model
- `*_features.joblib` - Feature list for each model
- `*_metrics.joblib` - Evaluation metrics

## ML Model Performance

**Target Metrics (Updated):**
- Accuracy within $5M: >= 70%
- R² Score: >= 0.50

**Current Results:**

| Model | MAE | Within $5M | R² |
|-------|-----|------------|-----|
| Batter AAV | $4.17M | 74.4% ✅ | 0.559 |
| Batter Length | 1.38 yrs | 93.0% ✅ | 0.498 |
| Pitcher AAV | $3.55M | 72.9% ✅ | 0.624 |
| Pitcher Length | 0.66 yrs | 100% ✅ | 0.588 |

## Important Constraints

- **Statcast data only available 2015+** - Pre-2015 contracts have no advanced metrics
- **Name matching uses normalization** - Handles accents (José→Jose), suffixes (Jr., II)
- **Caching is enabled** - pybaseball caches API calls; clear cache if data seems stale
- **Minimum qualification thresholds** - 50 PA (batters), 10 IP (pitchers)

## Target Variables for ML

- `AAV` (Annual Average Value in dollars)
- `length` (Contract length in years)

## Feature Categories

**Batter Features (20):**
- Contract context: year_signed, age_at_signing, position (one-hot)
- FanGraphs 3-year averages: WAR, wRC+, AVG, OBP, SLG, HR
- Statcast metrics: avg_exit_velo, barrel_rate, max_exit_velo, hard_hit_pct

**Pitcher Features (10):**
- Contract context: year_signed, age_at_signing, is_starter
- FanGraphs 3-year averages: WAR, ERA, FIP, K/9, BB/9, IP

## Backend API

**Tech Stack:** FastAPI + SQLite + Pydantic

### Running the API

```bash
# Install dependencies
pip install fastapi uvicorn pydantic sqlalchemy

# Seed the database (first time only)
cd backend && python seed_database.py

# Start the server
cd backend && uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with model status |
| `/api/v1/predictions` | POST | Generate contract prediction |
| `/api/v1/players/search?q=` | GET | Player name autocomplete |
| `/api/v1/contracts` | GET | Search/filter contracts database |

### Prediction Request Example

```bash
curl -X POST "http://localhost:8000/api/v1/predictions" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Juan Soto",
    "position": "RF",
    "age": 26,
    "war_3yr": 6.1,
    "wrc_plus_3yr": 160,
    "avg_3yr": 0.268,
    "obp_3yr": 0.410,
    "slg_3yr": 0.513,
    "hr_3yr": 34
  }'
```

### Response includes:
- `predicted_aav`: Predicted AAV in dollars
- `predicted_aav_low` / `predicted_aav_high`: Range based on MAE
- `predicted_length`: Contract length in years
- `confidence_score`: Model accuracy percentage
- `comparables`: 5 similar historical contracts
- `feature_importance`: Top 5 features driving prediction

## Frontend

**Tech Stack:** Next.js 16 + React 19 + TypeScript + Tailwind CSS + shadcn/ui

### Running the Frontend

```bash
cd frontend && npm install && npm run dev
```

Frontend available at: http://localhost:3000

### Features
- Player search with autocomplete (auto-fills stats from database)
- **Prospect support**: Search for players without contracts (e.g., Kyle Tucker)
- Contract prediction form with position-specific fields
- Results display with AAV range, comparables, and feature importance
- Historical contracts browser with filtering

## Prospect Feature

The app supports two types of players in search:

### Signed Players
- Players with historical contracts in the Spotrac database
- Stats come from `master_contract_dataset.csv` (contract-time stats)
- Used for model training and comparables

### Prospects (Unsigned Players)
- Players with FanGraphs data but no free agent contract yet
- Stats calculated as 3-year averages from most recent seasons
- Seeded from `fangraphs_batting_2015-2025.csv` and `fangraphs_pitching_2015-2025.csv`
- Examples: Kyle Tucker, upcoming free agents
- Displayed with "Prospect" badge in search results

### Database Schema

The `Player` table has a `has_contract` boolean flag:
- `True` = signed player (stats from Contract table)
- `False` = prospect (stats stored directly on Player table)

### Updating Prospect Data

To refresh prospect stats after collecting new FanGraphs data:

```bash
# 1. Collect latest FanGraphs data
python Data/collect_all_data_expanded.py

# 2. Re-seed the database (includes both signed players and prospects)
cd backend && python seed_database.py
```

## Deployment (Railway)

Both services can be deployed to Railway:

### Backend Deployment
```bash
# Environment variables needed:
ALLOWED_ORIGINS=https://your-frontend.up.railway.app
DATABASE_URL=sqlite:///mlb_contracts.db
```

### Frontend Deployment
```bash
# Environment variables needed:
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app
```

### Railway Setup Steps
1. Create new Railway project
2. Add backend service (point to `/backend` directory)
3. Add frontend service (point to `/frontend` directory)
4. Set environment variables for each service
5. Deploy

## Making Predictions (Direct Python)

```python
import joblib
import numpy as np

# Load model
model = joblib.load('Data/Models/batter_aav_model.joblib')
scaler = joblib.load('Data/Models/batter_aav_scaler.joblib')
features = joblib.load('Data/Models/batter_aav_features.joblib')

# Prepare input (must match feature order)
player_stats = {...}  # Dict with all features
X = np.array([[player_stats[f] for f in features]])
X_scaled = scaler.transform(X)

# Predict
predicted_aav_millions = model.predict(X_scaled)[0]
print(f"Predicted AAV: ${predicted_aav_millions:.1f}M")
```

