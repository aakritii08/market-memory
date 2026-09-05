# 🧠 Market Memory

### Catch up on what matters.

Market Memory is an intelligent market watchlist and memory layer that helps users understand **what meaningfully changed since they last checked the market**.

Instead of forcing users to scan prices, charts, news, and alerts every time they return, Market Memory remembers the user's previous market snapshot and identifies the changes that actually deserve attention.

---

## 🚀 Live Demo

### Frontend
https://frontend-production-a1b3.up.railway.app

### Backend Health
https://backend-production-5cbc.up.railway.app/health

---

## 🎯 Problem

Traditional stock watchlists answer:

> "What is happening in the market right now?"

But they don't answer the question users actually have when they return after being away:

> **"What changed since I last checked, and does it matter?"**

Small price movements, routine news, and normal market fluctuations can create a large amount of noise.

Market Memory solves this by creating a persistent snapshot of the market and comparing the latest state against what the user previously knew.

---

## 💡 Solution

Market Memory acts as a **personal market memory layer**.

When a user checks their watchlist:

1. The current market state is captured.
2. A snapshot of the user's known state is stored.
3. New market information is compared against the previous snapshot.
4. Routine noise is filtered out.
5. Meaningful changes are scored.
6. Important changes are explained.
7. Evidence is shown for every explanation.
8. The user can see what they missed while they were away.

The result is a focused briefing rather than another information-heavy stock dashboard.

---

# ✨ Key Features

## 1. 📋 Smart Watchlists

Users can create and manage their own market watchlists.

Each watchlist remembers the user's previous market state and uses it as the baseline for future comparisons.

---

## 2. 🔄 "What Changed Since I Last Checked?"

The main dashboard is built around one question:

> **Catch up on what matters.**

When users return, Market Memory identifies meaningful changes since their previous snapshot.

Changes are categorized into:

- 🔴 Needs Attention
- 🟡 Worth Knowing
- ⚪ Nothing Meaningful

This prevents users from having to manually scan every stock and news item.

---

## 3. 📊 Explainable Meaningfulness Score

Every detected change receives a **Meaningfulness Score from 0–100**.

The score is based on deterministic signals such as:

- Price movement
- Volume anomaly
- Market/sector movement
- Volatility-adjusted movement
- News and event signals
- Earnings/events
- Sentiment
- Analyst changes

Example:

> NVDA  
> +4.8%  
> 3.0× normal volume  
> **96/100 Meaningfulness**

The score is explainable rather than being a black-box prediction.

---

## 4. 🧠 Explain

Users can ask the system to explain why a change matters.

The explanation provides:

### Why?
What caused the detected change?

### Why it matters
Why should the user care?

### Uncertainty
What information may be incomplete or uncertain?

### Confidence
How confident is the system in the explanation?

The LLM is used as an explanation layer rather than as the source of truth.

---

## 5. 🔎 Evidence

Every meaningful change can be inspected through an evidence panel.

Evidence can include:

- Price movement
- Volume
- Events
- News
- Sources
- Timestamps
- Freshness
- Confidence

This makes the system auditable and reduces the risk of unsupported AI explanations.

---

## 6. ⏳ Market Time Machine

Users can see what they missed while they were away.

Supported views include:

- Since last visit
- Last 24 hours
- Last 7 days
- Custom time range

The feature reconstructs the important changes rather than simply displaying a chronological stream of everything that happened.

---

## 7. 🔔 Smart Alerts

Users can enable alerts for meaningful market changes.

Alert sensitivity:

| Sensitivity | Threshold |
|---|---:|
| Low | 70+ |
| Medium | 55+ |
| High | 40+ |

Alerts are not based solely on price.

They use the same meaningfulness analysis that powers the main briefing.

Users can also mark alerts as read/unread.

---

## 8. 🩺 Data Health

Market information is accompanied by data-quality information.

The system tracks:

- Fresh
- Stale
- Conflicting
- Ready for analysis

Each source includes freshness information.

If data sources conflict, conflicting evidence is excluded from the AI explanation instead of allowing the model to guess.

---

## 9. 🎬 Demo Mode

The application includes deterministic demo scenarios for demonstrating the product without depending on unpredictable live market conditions.

Available scenarios include:

- Normal Market
- Earnings Surprise
- Breaking News
- Unusual Volume
- Sector Movement
- Conflicting Data
- Stale Data
- Repeated Small Movements
- Large but Normal

Example scenarios target specific companies such as:

- NVDA — Earnings Surprise
- TSLA — Breaking News
- AAPL — Unusual Volume
- MSFT — Conflicting Data
- AMZN — Repeated Small Movements

This makes the application reliable and repeatable during demonstrations.

---

# 🏗️ Architecture

```text
                         ┌──────────────────────┐
                         │      React + TS      │
                         │      Frontend        │
                         └──────────┬───────────┘
                                    │
                                    │ REST API
                                    ▼
                         ┌──────────────────────┐
                         │       FastAPI        │
                         │       Backend        │
                         └──────────┬───────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
                  ▼                 ▼                 ▼
           ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
           │ PostgreSQL  │   │    Redis    │   │ Market/Data │
           │             │   │             │   │  Providers  │
           └─────────────┘   └─────────────┘   └─────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Deterministic        │
                         │ Analysis Layer       │
                         │                      │
                         │ Meaningfulness       │
                         │ Change Detection     │
                         │ Data Quality         │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    LLM Explanation   │
                         │       Layer          │
                         └──────────────────────┘
