from datetime import datetime, timezone, timedelta
import random
from .interfaces import MarketDataProvider, NewsProvider, CompanyDataProvider

COMPANIES = {"NVDA":"NVIDIA", "TSLA":"Tesla", "AAPL":"Apple", "MSFT":"Microsoft", "AMZN":"Amazon", "META":"Meta Platforms"}
BASE = {"NVDA":170.0,"TSLA":330.0,"AAPL":245.0,"MSFT":510.0,"AMZN":230.0,"META":760.0}
VOL = {"NVDA":0.8,"TSLA":1.0,"AAPL":0.45,"MSFT":0.35,"AMZN":0.55,"META":0.6}

class SyntheticProvider(MarketDataProvider, NewsProvider, CompanyDataProvider):
    def __init__(self, scenario="normal"): self.scenario = scenario
    def quote(self, symbol):
        p = BASE.get(symbol, 100.0); scenario = self.scenario
        # Company-specific demo scenarios should not make the entire watchlist
        # move as though every company experienced the same event.
        targets={
            "earnings_surprise":{"NVDA"},
            "breaking_news":{"TSLA"},
            "unusual_volume":{"AAPL"},
            "conflicting_data":{"MSFT"},
            "repeated_small_movements":{"AMZN"},
            "volatile_normal":{"NVDA"},
        }
        company_active = symbol in targets.get(scenario,set())
        scenario_mult = {"normal":1.0,"earnings_surprise":1.048,"breaking_news":1.031,"unusual_volume":1.021,"sector_movement":1.019,"conflicting_data":1.026,"stale_data":0.992,"repeated_small_movements":1.018,"volatile_normal":1.04}.get(scenario,1.0)
        mult = scenario_mult if (company_active or scenario in {"normal","sector_movement","stale_data"}) else 1.0
        price = p * mult
        pct = (mult-1)*100
        scenario_volume = {"normal":1.0,"earnings_surprise":3.0,"breaking_news":2.4,"unusual_volume":3.2,"sector_movement":1.5,"conflicting_data":2.0,"stale_data":1.1,"repeated_small_movements":2.1,"volatile_normal":1.0}.get(scenario,1.0)
        volume_mult = scenario_volume if (company_active or scenario in {"normal","sector_movement","stale_data"}) else 1.0
        ts = datetime.now(timezone.utc) - (timedelta(minutes=50) if scenario=="stale_data" else timedelta(seconds=8))
        return {"symbol":symbol,"price":round(price,2),"pct_change":round(pct,2),"previous_close":p,"volume":int(20_000_000*volume_mult),"average_volume":20_000_000,"market_status":"open","timestamp":ts.isoformat(),"data_status":"stale" if scenario=="stale_data" else "fresh","volatility":VOL.get(symbol,.5)}
    def events(self, symbol, since=None):
        s=self.scenario
        titles={
            "earnings_surprise":"Earnings beat expectations",
            "breaking_news":"Major company announcement",
            "unusual_volume":"Unusual trading activity",
            "sector_movement":"Semiconductor sector strengthens",
            "conflicting_data":"Conflicting market reports",
            "repeated_small_movements":"Accumulated momentum"
        }
        # Keep competition scenarios realistic: company-specific events target one
        # representative stock instead of making every watchlist constituent have
        # the same news event. Sector movement is intentionally broader.
        targets={
            "earnings_surprise":{"NVDA"},
            "breaking_news":{"TSLA"},
            "unusual_volume":{"AAPL"},
            "sector_movement":{"NVDA","AMD"},
            "conflicting_data":{"MSFT"},
            "repeated_small_movements":{"AMZN"},
        }
        if s in titles and (symbol in targets.get(s,set())):
            return [{"event_type":s,"title":titles[s],"summary":f"Synthetic demonstration event for {symbol}.","source":"Market Memory Demo Feed","timestamp":datetime.now(timezone.utc).isoformat(),"freshness_seconds":20,"reliability":0.95}]
        return []
    def company(self,symbol): return {"symbol":symbol,"name":COMPANIES.get(symbol,symbol),"sector":"Technology"}
