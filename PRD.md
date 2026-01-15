**MLB CONTRACT ADVISOR**

**Product Requirements Document (PRD)**

*Comprehensive Technical & Product Specifications*

  -----------------------------------------------------------------------
  **Document        Product Requirements Document (PRD)
  Title:**          
  ----------------- -----------------------------------------------------
  **Project Name:** MLB Contract Advisor

  **Version:**      1.0

  **Date:**         January 2026

  **Status:**       Draft

  **Owner:**        Product Manager / Developer
  -----------------------------------------------------------------------

# Table of Contents

[Table of Contents [1](#table-of-contents)](#table-of-contents)

[1. Product Overview [1](#product-overview)](#product-overview)

[Product Description [1](#product-description)](#product-description)

[Core Features (MVP) [1](#core-features-mvp)](#core-features-mvp)

[Technology Stack [1](#technology-stack)](#technology-stack)

[Success Criteria [1](#success-criteria)](#success-criteria)

[2. User Personas & Stories
[1](#user-personas-stories)](#user-personas-stories)

[Primary Personas [1](#primary-personas)](#primary-personas)

[Persona 1: Alex (Analytical Fan)
[1](#persona-1-alex-analytical-fan)](#persona-1-alex-analytical-fan)

[Persona 2: Sarah (Casual Fan)
[1](#persona-2-sarah-casual-fan)](#persona-2-sarah-casual-fan)

[Persona 3: Jamie (Baseball Writer)
[1](#persona-3-jamie-baseball-writer)](#persona-3-jamie-baseball-writer)

[Key User Stories (MVP Priority)
[1](#key-user-stories-mvp-priority)](#key-user-stories-mvp-priority)

[Priority 0 (Must Have for MVP)
[1](#priority-0-must-have-for-mvp)](#priority-0-must-have-for-mvp)

[Priority 1 (Post-MVP) [1](#priority-1-post-mvp)](#priority-1-post-mvp)

[3. Functional Requirements
[1](#functional-requirements)](#functional-requirements)

[3.1 Contract Prediction System
[1](#contract-prediction-system)](#contract-prediction-system)

[Player Search & Input [1](#player-search-input)](#player-search-input)

[Prediction Output [1](#prediction-output)](#prediction-output)

[3.2 Comparable Players System
[1](#comparable-players-system)](#comparable-players-system)

[3.3 Contract Database [1](#contract-database)](#contract-database)

[3.4 Model Transparency [1](#model-transparency)](#model-transparency)

[3.5 Non-Functional Requirements
[1](#non-functional-requirements)](#non-functional-requirements)

[Performance [1](#performance)](#performance)

[Scalability [1](#scalability)](#scalability)

[Accessibility [1](#accessibility)](#accessibility)

[4. Technical Architecture
[1](#technical-architecture)](#technical-architecture)

[4.1 System Architecture
[1](#system-architecture)](#system-architecture)

[Frontend Stack [1](#frontend-stack)](#frontend-stack)

[Backend Stack [1](#backend-stack)](#backend-stack)

[Database [1](#database)](#database)

[ML/AI Stack [1](#mlai-stack)](#mlai-stack)

[4.2 API Specifications [1](#api-specifications)](#api-specifications)

[Base URL & Versioning [1](#base-url-versioning)](#base-url-versioning)

[Core Endpoints (P0) [1](#core-endpoints-p0)](#core-endpoints-p0)

[4.3 Security [1](#security)](#security)

[5. Data Requirements [1](#data-requirements)](#data-requirements)

[5.1 Contract Data [1](#contract-data)](#contract-data)

[Data Source [1](#data-source)](#data-source)

[Required Fields [1](#required-fields)](#required-fields)

[Data Quality Targets [1](#data-quality-targets)](#data-quality-targets)

[5.2 Player Performance Data
[1](#player-performance-data)](#player-performance-data)

[Data Source [1](#data-source-1)](#data-source-1)

[Required Metrics [1](#required-metrics)](#required-metrics)

[5.3 Data Pipeline [1](#data-pipeline)](#data-pipeline)

[6. UI/UX Requirements [1](#uiux-requirements)](#uiux-requirements)

[6.1 Design Principles [1](#design-principles)](#design-principles)

[6.2 Key Pages [1](#key-pages)](#key-pages)

[Homepage [1](#homepage)](#homepage)

[Prediction Page [1](#prediction-page)](#prediction-page)

[Contract Database [1](#contract-database-1)](#contract-database-1)

[6.3 Design System [1](#design-system)](#design-system)

[Typography [1](#typography)](#typography)

[Colors [1](#colors)](#colors)

[Responsive Breakpoints
[1](#responsive-breakpoints)](#responsive-breakpoints)

[7. Testing & Quality Assurance
[1](#testing-quality-assurance)](#testing-quality-assurance)

[7.1 Testing Strategy [1](#testing-strategy)](#testing-strategy)

[7.2 ML Model Testing [1](#ml-model-testing)](#ml-model-testing)

[Model Evaluation Metrics
[1](#model-evaluation-metrics)](#model-evaluation-metrics)

[Test Dataset [1](#test-dataset)](#test-dataset)

[7.3 Functional Testing [1](#functional-testing)](#functional-testing)

[Manual Testing Checklist (MVP)
[1](#manual-testing-checklist-mvp)](#manual-testing-checklist-mvp)

[7.4 Performance Testing
[1](#performance-testing)](#performance-testing)

[7.5 User Acceptance Testing (Beta)
[1](#user-acceptance-testing-beta)](#user-acceptance-testing-beta)

[7.6 Pre-Launch Checklist
[1](#pre-launch-checklist)](#pre-launch-checklist)

[8. Launch & Go-to-Market Strategy
[1](#launch-go-to-market-strategy)](#launch-go-to-market-strategy)

[8.1 Launch Phases [1](#launch-phases)](#launch-phases)

[Phase 1: Closed Beta (Weeks 10-12)
[1](#phase-1-closed-beta-weeks-10-12)](#phase-1-closed-beta-weeks-10-12)

[Phase 2: Soft Launch (Weeks 13-16)
[1](#phase-2-soft-launch-weeks-13-16)](#phase-2-soft-launch-weeks-13-16)

[Phase 3: Public Launch (Month 5-6)
[1](#phase-3-public-launch-month-5-6)](#phase-3-public-launch-month-5-6)

[8.2 Growth Channels [1](#growth-channels)](#growth-channels)

[Organic (Primary Focus)
[1](#organic-primary-focus)](#organic-primary-focus)

[8.3 Success Metrics [1](#success-metrics)](#success-metrics)

[Launch Milestones [1](#launch-milestones)](#launch-milestones)

[8.4 Monetization Timeline
[1](#monetization-timeline)](#monetization-timeline)

[9. Appendix [1](#appendix)](#appendix)

[9.1 Development Timeline Summary
[1](#development-timeline-summary)](#development-timeline-summary)

[9.2 Budget Breakdown [1](#budget-breakdown)](#budget-breakdown)

[9.3 Key Decisions & Rationale
[1](#key-decisions-rationale)](#key-decisions-rationale)

[Technology Choices [1](#technology-choices)](#technology-choices)

[Feature Prioritization
[1](#feature-prioritization)](#feature-prioritization)

[9.4 Risks & Mitigations [1](#risks-mitigations)](#risks-mitigations)

[9.5 Document Control [1](#document-control)](#document-control)

# 1. Product Overview

## Product Description

MLB Contract Advisor is a freemium SaaS web application that uses
machine learning to predict Major League Baseball contract values. The
platform analyzes 10+ years of contract data (2015-2025) combined with
advanced player performance metrics to generate accurate contract
predictions with full model transparency.

## Core Features (MVP)

- **Contract Prediction Engine:** AI-powered predictions with AAV,
  length, and confidence scores

- **Dual-Mode Interface:** Simple mode for casual fans, Advanced mode
  for analysts

- **Comparable Players:** Algorithm-driven matching with similarity
  scores

- **Contract Database:** Searchable repository of 847 MLB contracts

- **Model Transparency:** Feature importance, calculation breakdown, and
  methodology

- **Mobile-First Design:** Responsive, accessible interface optimized
  for all devices

## Technology Stack

**Frontend:** Next.js 14, React, Tailwind CSS, shadcn/ui, SWR

**Backend:** FastAPI (Python), PostgreSQL, SQLAlchemy

**ML/AI:** XGBoost, scikit-learn, pandas, numpy

**Hosting:** Vercel (frontend), Railway (backend + database)

**Data Sources:** Spotrac Premium (contracts), MLB Stats API
(performance)

## Success Criteria

- Model Accuracy: 70%+ predictions within \$3M of actual contracts

- User Adoption: 1,000+ users within 6 months

- User Satisfaction: Net Promoter Score (NPS) ≥ 30

- Conversion: 3-5% free-to-premium conversion rate

- Performance: Page load \< 2s, API response \< 1s (p95)

- Accessibility: WCAG 2.1 Level AA compliance

# 2. User Personas & Stories

## Primary Personas

### Persona 1: Alex (Analytical Fan)

**Demographics:** 28-45, college educated, tech-savvy, 30% of user base

**Behaviors:** Reads FanGraphs daily, plays advanced fantasy,
understands WAR/wRC+

**Goals:** Deep analysis, data validation, win fantasy leagues

**Needs:** Model transparency, full comparables, exportable data,
advanced features

**Conversion:** 5-10% to premium tier

### Persona 2: Sarah (Casual Fan)

**Demographics:** 22-55, follows favorite team, mobile-first, 60% of
user base

**Behaviors:** Checks ESPN, casual fantasy, debates with friends

**Goals:** Quick answers, settle debates, understand if team overpaid

**Needs:** Plain English, mobile-friendly, no jargon, shareable results

**Conversion:** 1-2% to premium tier, high viral potential

### Persona 3: Jamie (Baseball Writer)

**Demographics:** 25-50, freelance or staff writer, 5% of user base

**Goals:** Quick credible data for articles, citable sources

**Needs:** Fast predictions, methodology to reference, API access
(future)

**Conversion:** 10-20% to premium/pro, B2B pipeline

## Key User Stories (MVP Priority)

### Priority 0 (Must Have for MVP)

- As Alex, I want to search for a player and get an instant prediction
  so I can evaluate free agent signings

- As Sarah, I want to see if a contract is fair in plain English so I
  can understand without jargon

- As Alex, I want to see how the model works so I can trust the
  predictions

- As any user, I want to see comparable players so I can understand the
  prediction context

- As Alex, I want to search historical contracts so I can research
  market trends

- As Sarah, I want the site to work on my phone so I can use it anywhere

### Priority 1 (Post-MVP)

- As any user, I want to share predictions so I can discuss with friends

- As Alex, I want to export contract data so I can analyze in Excel

- As Alex, I want to save my predictions so I can track my accuracy over
  time

- As Jamie, I want API access so I can automate predictions for articles

# 3. Functional Requirements

## 3.1 Contract Prediction System

### Player Search & Input

- Search autocomplete triggers after 2 characters (\< 300ms response)

- Results show player name, position, current team, age

- Manual entry option for custom player stats

- Required fields: name, position, age, WAR, wRC+/ERA+

- Optional Statcast fields improve accuracy and confidence

### Prediction Output

- Prediction generated in \< 2 seconds

- Output: AAV (low/likely/high), contract length, confidence score

- Simple mode: Single value, plain language assessment, 1 comparable

- Advanced mode: Range, 3-10 comparables, feature importance,
  calculation

- Toggle between modes persists across sessions

## 3.2 Comparable Players System

- Similarity algorithm: 40% position, 35% performance, 15% age, 10%
  recency

- Returns top 10 comparables with similarity scores

- Display: player name, year signed, AAV, stats at signing

- Minimum similarity threshold: 40% (lower if \< 3 results found)

- Click comparable for full contract detail view

## 3.3 Contract Database

- Search by player name with autocomplete

- Basic filters (P0): position, year range, team

- Advanced filters (P1): AAV range, contract type, age at signing

- Results paginated at 20 contracts per page

- Sortable by AAV, total value, year, player name

- Free tier: 2024-2025 contracts only; Premium: full 2015-2025

## 3.4 Model Transparency

- Feature importance chart (bar graph showing % contribution)

- Step-by-step calculation breakdown

- Model coefficients displayed (advanced users)

- Confidence explanation (why high/low)

- Methodology page with accuracy metrics and limitations

## 3.5 Non-Functional Requirements

### Performance

- Homepage load: \< 2s (p95)

- Prediction API: \< 1s (p95)

- Database search: \< 500ms (p95)

- Autocomplete: \< 300ms (p95)

### Scalability

- MVP: Support 100 concurrent users

- Post-MVP: Scale to 1,000 concurrent users

- Stateless backend enables horizontal scaling

### Accessibility

- WCAG 2.1 Level AA compliance

- Keyboard navigation for all interactive elements

- Screen reader compatible

- Color contrast ratios meet 4.5:1 (normal text)

- Touch targets minimum 44px × 44px

# 4. Technical Architecture

## 4.1 System Architecture

The application follows a three-tier architecture: presentation layer
(Next.js), business logic layer (FastAPI), and data layer (PostgreSQL).
This separation enables independent scaling and clear responsibility
boundaries.

### Frontend Stack

- **Framework:** Next.js 14+ (React, Server-Side Rendering)

- **Styling:** Tailwind CSS, shadcn/ui component library

- **State:** React Context + Hooks (simple), Zustand (if needed)

- **Data Fetching:** SWR (caching, revalidation)

- **Forms:** React Hook Form

- **Charts:** Recharts

- **Hosting:** Vercel (automatic deployments, CDN, free tier)

### Backend Stack

- **Framework:** FastAPI (Python, async support, auto API docs)

- **Database ORM:** SQLAlchemy 2.0, Alembic (migrations)

- **Validation:** Pydantic v2

- **Rate Limiting:** SlowAPI

- **Hosting:** Railway.app (includes PostgreSQL, auto-deploy)

### Database

- **Engine:** PostgreSQL 15+ (B2B-ready, JSONB support)

- **Tables:** contracts, players, predictions, users (P1), organizations
  (P1)

- **Indexing:** Position, year, AAV, player name (trigram for fuzzy
  search)

### ML/AI Stack

- **Algorithm:** XGBoost (gradient boosted trees)

- **Libraries:** scikit-learn, pandas, numpy, joblib

- **Features:** 15-20 inputs (age, WAR, position, Statcast metrics,
  market)

- **Training Data:** 2015-2022 (train), 2023 (validation), 2024-2025
  (test)

- **Deployment:** Model loaded at startup, predictions run in-memory

## 4.2 API Specifications

### Base URL & Versioning

**Development:** http://localhost:8000/api/v1

**Production:** https://api.mlbcontractadvisor.com/api/v1

### Core Endpoints (P0)

**POST /api/v1/predictions**

- Generate contract prediction

- Input: player data, stats (age, position, WAR, etc.)

- Output: AAV range, confidence, comparables, feature importance

- Rate limit: 100/hour per IP

**GET /api/v1/players/search?q={query}**

- Autocomplete player search

- Returns: Player name, position, team, age

- Response time: \< 300ms

**GET /api/v1/contracts**

- Search contract database

- Filters: position, year range, AAV, team

- Pagination: 20 per page

- Response time: \< 500ms

## 4.3 Security

- HTTPS enforced in production

- CORS properly configured (only allow your frontend)

- Rate limiting by IP address (100 predictions/hour)

- Input validation via Pydantic

- SQL injection prevention (SQLAlchemy ORM)

- Secrets in environment variables (never in code)

- Authentication (P1): JWT tokens, password hashing (bcrypt)

# 5. Data Requirements

## 5.1 Contract Data

### Data Source

**Primary:** Spotrac Premium (\$40/year, CSV export)

**Scope:** 500-800 major contracts (2015-2025)

**Update Frequency:** Weekly during offseason, monthly in-season

### Required Fields

- Player name, position, team, year signed

- AAV (average annual value), total value, contract length

- Age at signing, service time

- Contract type (FA, Extension, Arb Buyout)

### Data Quality Targets

- Quality score: ≥ 95%

- Completeness: 100% required fields, 80%+ desirable fields

- Accuracy: All AAV calculations correct

- Duplicates: Zero

## 5.2 Player Performance Data

### Data Source

**Primary:** MLB Stats API (free, public)

**Supplementary:** FanGraphs (manual for WAR, wRC+)

### Required Metrics

- 3-year WAR average (primary performance metric)

- wRC+ for position players (normalized batting performance)

- ERA+ for pitchers (normalized pitching performance)

- Optional Statcast: exit velocity, barrel rate, sprint speed, OAA

## 5.3 Data Pipeline

1.  Export contract data from Spotrac (CSV)

2.  Clean and standardize (Python scripts)

3.  Collect player stats from MLB Stats API / FanGraphs

4.  Merge datasets and validate quality

5.  Seed PostgreSQL database

6.  Backup cleaned data

# 6. UI/UX Requirements

## 6.1 Design Principles

- **Progressive Disclosure:** Simple by default, deep on demand

- **Data-First:** Predictions are the star, interface is supportive

- **Transparency:** Always show \'why\' behind predictions

- **Mobile-First:** Design for mobile, enhance for desktop

- **Performance as Feature:** Fast = professional

## 6.2 Key Pages

### Homepage

- Hero with search input (prominent)

- 5-10 featured predictions (example players)

- \'How It Works\' section (builds credibility)

- Clear call-to-action: \'Make Prediction\'

### Prediction Page

**Input State:**

- Tab toggle: Player Search \| Manual Entry

- Autocomplete with player photos (optional)

- Form validation with helpful error messages

**Results State (Simple Mode):**

- Large AAV display (48px, bold)

- Confidence stars (1-5 filled stars)

- Plain language assessment (\'Fair Deal\', color-coded)

- 1 comparable player with photo

- \'See Detailed Analysis\' button

**Results State (Advanced Mode):**

- Prediction range (low/likely/high) with slider

- All comparables table (sortable)

- Feature importance chart (horizontal bars)

- Expandable calculation breakdown

- Model coefficients (collapsible)

### Contract Database

- Filters sidebar (desktop) or drawer (mobile)

- Results as cards (mobile) or table (desktop)

- Pagination (20 per page)

- Click contract opens detail modal

## 6.3 Design System

### Typography

- Font: Inter (headings and body)

- Prediction values: JetBrains Mono (monospace for numbers)

- H1: 48px (mobile: 36px), H2: 36px (mobile: 28px)

- Body: 16px (never smaller for readability)

### Colors

- Primary: #1E40AF (blue for CTAs, links)

- Success: #059669 (green for \'Fair Deal\')

- Warning: #D97706 (orange for slight over/underpay)

- Error: #DC2626 (red for significant overpay)

- All colors meet WCAG AA contrast requirements

### Responsive Breakpoints

- Mobile: \< 640px (default styles)

- Tablet: 640px - 1024px

- Desktop: \> 1024px

# 7. Testing & Quality Assurance

## 7.1 Testing Strategy

MVP testing focuses on manual validation to enable rapid iteration.
Automated tests will be added post-launch to prevent regression.

## 7.2 ML Model Testing

### Model Evaluation Metrics

- Mean Absolute Error (MAE): \< \$3M

- Accuracy within \$3M: ≥ 70%

- Accuracy within \$5M: ≥ 85%

- R² Score: ≥ 0.75

### Test Dataset

- Training: 2015-2022 contracts

- Validation: 2023 contracts

- Test: 2024-2025 contracts (never seen during training)

## 7.3 Functional Testing

### Manual Testing Checklist (MVP)

- [ ] Player search returns accurate autocomplete

- [ ] Prediction generates in \< 2 seconds

- [ ] Simple/Advanced mode toggle works

- [ ] Comparables display with correct similarity scores

- [ ] Database search filters apply correctly

- [ ] Mobile responsive on 3+ screen sizes

- [ ] Keyboard navigation works (all interactive elements)

- [ ] Error messages display appropriately

## 7.4 Performance Testing

- Lighthouse audit: Performance ≥ 90, Accessibility ≥ 95

- API response times measured (p50, p95, p99)

- Database query performance validated

## 7.5 User Acceptance Testing (Beta)

**Timeline:** Weeks 10-12 of development (2-3 week beta period)

**Participants:** 10-15 beta testers (mix of analytical fans, casual
fans, writers)

**Success Criteria:** 80%+ complete all tasks, NPS ≥ 30, zero critical
bugs, 70%+ say predictions seem accurate

## 7.6 Pre-Launch Checklist

- [ ] All critical user flows work

- [ ] Model accuracy validated (≥ 70%)

- [ ] Mobile responsive (tested on real devices)

- [ ] Accessibility audit passed

- [ ] Performance targets met

- [ ] Data quality score ≥ 95%

- [ ] Security checklist complete

- [ ] Analytics and monitoring configured

- [ ] Database backup verified

- [ ] Zero critical bugs

# 8. Launch & Go-to-Market Strategy

## 8.1 Launch Phases

### Phase 1: Closed Beta (Weeks 10-12)

- **Participants:** 10-15 invited beta testers

- **Goal:** Fix critical issues, validate core value

- **Activities:** Active feedback collection, rapid iteration

- **Output:** Testimonials, validated product-market fit

### Phase 2: Soft Launch (Weeks 13-16)

- **Target:** 100-500 users

- **Channels:** Reddit (r/baseball, r/Sabermetrics), Twitter, baseball
  communities

- **Goal:** Validate product-market fit, build case studies

- **Content:** Launch blog post, Twitter thread, Reddit posts

### Phase 3: Public Launch (Month 5-6)

- **Target:** 1,000-5,000 users

- **Channels:** Product Hunt, Hacker News, media outreach, Twitter

- **Timing:** November-December (offseason, hot stove season)

- **Goal:** Establish presence, build user base

## 8.2 Growth Channels

### Organic (Primary Focus)

7.  **Content Marketing:** Weekly blog posts with predictions, data
    analysis

8.  **SEO:** Target keywords like \'\[Player\] contract prediction\'

9.  **Community:** Active on Reddit, Twitter, baseball forums

10. **Word of Mouth:** Shareable predictions, viral mechanics

11. **Media Coverage:** Pitch to baseball writers, analytics community

## 8.3 Success Metrics

### Launch Milestones

- Week 16: MVP Launch (product live, zero critical bugs)

- Month 1: 100-500 users, NPS ≥ 30

- Month 3: 1,000+ users, organic growth evident

- Month 6: 5,000+ users, ready to monetize

- Month 12: 10,000 users, 250+ premium, \$25-50K ARR

- Year 2: 15K users, 3-5 B2B clients, \$100-150K ARR

## 8.4 Monetization Timeline

**Months 1-6:** Free only (validate product-market fit)

**Month 7-9:** Launch premium tier (\$9.99/month or \$79/year)

**Month 10-12:** Optimize pricing and features based on conversion data

**Year 2+:** Add Pro tier (\$29.99/month), pilot B2B (custom pricing)

# 9. Appendix

## 9.1 Development Timeline Summary

  -----------------------------------------------------------------------
  **Phase**         **Timeline**               **Effort**
  ----------------- -------------------------- --------------------------
  Phase 0: Data     Weeks 1-2                  30-40 hours
  Collection                                   

  Phase 1: Core MVP Weeks 3-8                  75-105 hours

  Phase 2:          Weeks 9-12                 45-60 hours
  Refinement                                   

  Phase 3: Soft     Weeks 13-16                45-60 hours
  Launch                                       

  **Total**         **16 weeks (4 months)**    **195-265 hours**
  -----------------------------------------------------------------------

## 9.2 Budget Breakdown

  -----------------------------------------------------------------------
  **Item**                                                       **Cost**
  ----------------------------------- -----------------------------------
  Spotrac Premium (annual)                                           \$40

  Domain Registration (.com)                                         \$12

  Hosting (Railway + Vercel)                              \$0 (free tier)

  Development Tools                                     \$0 (open source)

  **Total MVP Budget**                                           **\$52**
  -----------------------------------------------------------------------

## 9.3 Key Decisions & Rationale

### Technology Choices

- **PostgreSQL over SQLite:** Better concurrency, B2B-ready architecture

- **XGBoost over simpler models:** Superior accuracy on tabular data

- **Next.js over Create React App:** SSR for SEO, better performance

- **FastAPI over Flask:** Auto API docs, async support, type validation

### Feature Prioritization

- **Sharing features moved to P1:** Focus MVP on prediction quality, add
  viral features post-validation

- **Public API moved to P2:** Validate B2B demand before building
  infrastructure

- **Dual-mode interface (P0):** Serve both audiences from launch,
  critical differentiation

## 9.4 Risks & Mitigations

- **Risk:** Model accuracy below 70%

- **Mitigation:** Extensive testing, multiple algorithms, pivot to
  database tool if needed

- **Risk:** Low user adoption (\< 100 users)

- **Mitigation:** Beta validation, timing with offseason, community
  engagement

- **Risk:** Conversion to premium \< 3%

- **Mitigation:** Strong free tier, clear premium value, flexible
  pricing

## 9.5 Document Control

**Version:** 1.0

**Last Updated:** January 2026

**Owner:** Product Manager / Developer

**Status:** Draft - Ready for Review

**Next Review:** Post-Beta (Week 13)
