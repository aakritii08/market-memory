# Market Memory

> Your market doesn't wait for you. Your watchlist shouldn't forget.

Market Memory is an intelligence-first market watchlist. Instead of treating every price move as an alert, it remembers a user's last observed state, compares it with the current state, filters routine noise, and produces an explainable Change Story.

## What is implemented

- React + TypeScript editorial dashboard
- FastAPI backend with PostgreSQL persistence
- JWT authentication and per-user watchlist authorization
- Multiple watchlists, add/remove/reorder symbols
- Snapshot creation on each briefing view
- Deterministic 0–100 Meaningfulness Score using movement, volatility, volume and events
- Evidence-backed explanation layer with safe deterministic fallback
- Data freshness/status surfaced in every story
- Helpful / somewhat helpful / not helpful feedback capture
- Competition Demo Mode with nine synthetic scenarios
- Docker Compose for PostgreSQL, Redis, API and web
- Unit tests for the meaningfulness engine
- Swagger API docs at `/docs`

## Demo symbols

NVDA, TSLA, AAPL, MSFT, AMZN, META.

## Run locally

```bash
docker compose up --build
```

Then open `http://localhost:5173`.

Create an account with any email and an 8+ character password. Add symbols, refresh once to establish a snapshot, then choose a Demo Mode scenario and refresh again.

API docs: `http://localhost:8000/docs`

## Architecture

```text
React + TypeScript
       |
       v
 FastAPI API
       |
       +--> Auth / Authorization
       +--> Watchlist Service
       +--> Snapshot Service
       +--> Meaningfulness Engine
       |        |
       |        +--> volatility context
       |        +--> volume anomaly
       |        +--> event/news signals
       |        +--> explainable score
       |
       +--> AI Explanation Service
       |        |
       |        +--> structured evidence only
       |        +--> deterministic fallback
       |
       +--> Provider Interfaces
       |        +--> MarketDataProvider
       |        +--> NewsProvider
       |        +--> CompanyDataProvider
       |                 |
       |                 +--> SyntheticProvider (demo)
       |
       +--> PostgreSQL
       +--> Redis (ready for shared market cache/background jobs)
```

## Production provider integration

The demo deliberately uses `SyntheticProvider` so judging does not depend on live market conditions. To connect a real provider, implement the three provider interfaces in `backend/app/providers/interfaces.py`, then wire the provider in `backend/app/main.py`. The UI already distinguishes fresh/stale status from the provider response.

For an LLM gateway, configure `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`. The intended contract is to send only structured evidence: previous snapshot, current snapshot, detected events, deltas, sector context, and freshness. The model must not be the event detector.

## Testing

```bash
docker compose run --rm api pytest
```

## Competition demo flow

1. Register / sign in.
2. Create a watchlist and add NVDA, TSLA and AAPL.
3. Refresh: this establishes the first Market Memory snapshot.
4. Click `Earnings surprise`.
5. Refresh: NVDA moves into **Needs Attention** with a high Meaningfulness Score.
6. Expand the card: inspect **Why**, **Why it matters**, confidence and evidence.
7. Click `Stale data` to demonstrate that stale information is explicitly labeled.
8. Click `Conflicting data` as a product extension point for source reconciliation/exclusion.

## Next production hardening

- Replace synthetic provider with licensed market/news providers.
- Add Redis-backed shared quote/event cache and async workers.
- Add Alembic migrations and database constraints for full production operations.
- Add refresh-token rotation, stronger password policy, CSRF protection if cookie sessions are used, structured audit logging, and observability.
- Add historical volatility calculations from stored time-series data instead of the demo volatility constants.
- Add a full Time Machine route for arbitrary date ranges and a richer event timeline.


## Market Time Machine
Use **Show me what I missed** on the dashboard to reconstruct the selected period. The UI supports since last visit, last 24 hours, last 7 days, and a custom date/time range. Synthetic history is explicitly labeled so demo events are not presented as live market facts.


### Smart Alert sensitivity

- Low: alerts at 70/100 or above
- Medium: alerts at 55/100 or above
- High: alerts at 40/100 or above

Higher sensitivity means the system surfaces earlier/lower-scoring meaningful signals; stale and conflicting data are excluded from alerts.

## Final competition verification checklist

### Core product
- [x] Create and manage multiple watchlists
- [x] Add, remove, and reorder symbols
- [x] Persistent PostgreSQL state per user
- [x] Latest market information with freshness status
- [x] Personal last-visit snapshot comparison
- [x] Explainable Meaningfulness Score
- [x] Evidence and confidence for significant changes

### Intelligence features
- [x] Market Time Machine: last visit / 24h / 7d / custom
- [x] Noise filtering and explicit "Nothing meaningful"
- [x] Smart Alerts with Low / Medium / High sensitivity
- [x] Data Health for fresh / stale / conflicting data
- [x] Feedback-driven ranking personalization
- [x] Deterministic evidence before AI explanation

### Competition demo
- [x] Normal market
- [x] Earnings surprise (NVDA)
- [x] Breaking news (TSLA)
- [x] Unusual volume (AAPL)
- [x] Sector movement
- [x] Conflicting data (MSFT)
- [x] Stale data
- [x] Repeated small moves (AMZN)
- [x] Large-but-normal volatility

### Final hardening included
- [x] Database health check
- [x] API waits for healthy PostgreSQL in Compose
- [x] Per-watchlist demo state
- [x] Authenticated demo and alert endpoints
- [x] Alert comparison uses the previous persisted snapshot rather than comparing a scenario to itself
- [x] Timeline date arithmetic fixed for the 24h/7d/custom paths
- [x] Watchlist ownership enforced on protected resources
- [x] Backend unit tests pass

### Before a public deployment
Replace the demo secrets/providers and add licensed market/news providers, Redis-backed shared caching/workers, database migrations, refresh-token rotation, production secret management, structured logging/metrics, and expanded integration/security tests.
