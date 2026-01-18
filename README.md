# MLB Contract Advisor

AI-powered MLB contract prediction tool that estimates player contract values (AAV and length) using machine learning models trained on historical contract data.

**Live Demo:** [mlb-contract-advisor-production.up.railway.app](https://mlb-contract-advisor-production.up.railway.app)

## Features

- **Contract Predictions** - Get AI-powered AAV and contract length predictions for any MLB player
- **Free Agent Search** - Search any player with FanGraphs data, including upcoming free agents
- **Statcast Integration** - Plate discipline metrics for batters, pitcher-specific Statcast percentiles
- **Contract Assessment** - Fair Value / Overpaid / Underpaid ratings based on predicted vs actual AAV
- **Assessment Summary** - Natural language explanations of predictions and contract evaluations
- **Comparable Players** - Find similar historical contracts with extension flags for pre-FA deals
- **Feature Importance** - See which stats most influence the prediction
- **Historical Database** - Browse 450+ MLB contracts from 2015-2026
- **Separate Models** - Dedicated ML models for batters and pitchers

## Model Performance

| Metric | Batters | Pitchers |
|--------|---------|----------|
| Accuracy (within $5M) | ~74% | ~73% |
| Key Features | WAR, HR, wRC+, Barrel% | WAR, ERA, K/9, xERA |

### Statcast Metrics Used

**Batters:** Exit velocity, barrel rate, hard hit %, chase rate, whiff rate (percentiles)

**Pitchers:** FB velocity, FB spin, xERA, K%, BB%, Whiff%, Chase% (percentiles)

## Tech Stack

**Frontend**
- Next.js 15 (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui components
- SWR for data fetching

**Backend**
- FastAPI
- SQLite database
- scikit-learn (Gradient Boosting models)
- pandas/numpy for data processing

**Data Sources**
- FanGraphs (WAR, wRC+, ERA, FIP)
- Baseball Savant (Statcast percentile rankings)
- Spotrac (contract data)

## Project Structure

```
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/           # App router pages
│   │   ├── components/    # React components
│   │   └── lib/           # API client & utilities
│   └── package.json
│
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── models/       # Database & Pydantic schemas
│   │   └── services/     # Prediction service
│   ├── models/           # Trained ML models (.joblib)
│   └── requirements.txt
│
└── Data/                  # Data collection scripts
    ├── collect_all_data.py
    ├── collect_statcast_data.py
    └── integrate_with_spotrac_fixed.py
```

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- npm or yarn

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:3000` and expects the backend at `http://localhost:8000`.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with model/DB status |
| `/api/v1/predictions` | POST | Get contract prediction |
| `/api/v1/players/search` | GET | Search players by name |
| `/api/v1/contracts` | GET | List historical contracts |

### Example Prediction Request

```bash
curl -X POST "http://localhost:8000/api/v1/predictions" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Corey Seager",
    "position": "SS",
    "age": 27,
    "war_3yr": 4.5,
    "wrc_plus_3yr": 130,
    "avg_3yr": 0.280
  }'
```

## Deployment

The app is deployed on Railway with two services:

- **Frontend**: Next.js app with `NEXT_PUBLIC_API_URL` environment variable
- **Backend**: FastAPI with `ALLOWED_ORIGINS` for CORS configuration

### Environment Variables

**Frontend:**
```
NEXT_PUBLIC_API_URL=https://your-backend-url.up.railway.app
```

**Backend:**
```
ALLOWED_ORIGINS=https://your-frontend-url.up.railway.app
DATABASE_URL=sqlite:///mlb_contracts.db  # optional, defaults to local
```

## Data Pipeline

To rebuild the training dataset from scratch:

```bash
cd Data

# 1. Collect FanGraphs stats (2015-2025)
python collect_all_data.py

# 2. Collect Statcast metrics
python collect_statcast_data.py

# 3. Integrate with contract data
python integrate_with_spotrac_fixed.py
```

Note: First run takes 10-15 minutes; subsequent runs use cached data.

## License

For educational purposes only. Not affiliated with MLB or any team.

## Acknowledgments

- [pybaseball](https://github.com/jldbc/pybaseball) for FanGraphs/Statcast data access
- [Spotrac](https://www.spotrac.com) for contract data
- [shadcn/ui](https://ui.shadcn.com) for UI components
