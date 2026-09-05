from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class AuthIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
class Token(BaseModel): token: str
class WatchlistCreate(BaseModel): name: str = Field(min_length=1, max_length=120)
class WatchlistUpdate(BaseModel): name: str | None = None; sensitivity: str | None = None
class SymbolIn(BaseModel): symbol: str = Field(min_length=1, max_length=10)
class ReorderIn(BaseModel): symbols: list[str]
class FeedbackIn(BaseModel): symbol: str; rating: str

class Evidence(BaseModel):
    type: str; value: str; source: str; timestamp: datetime | None = None; freshness: str; confidence: float
class ChangeStory(BaseModel):
    symbol: str; company: str; category: str; price: float; pct_change: float; score: float
    summary: str; reason: str; why_it_matters: str; uncertainty: str
    confidence: float; evidence: list[Evidence]
    data_status: str
    personalization_boost: float = 0
    personalization_label: str = "Default ranking"
class Dashboard(BaseModel):
    watchlist_id: int; previous_visit: datetime | None; away_seconds: int
    meaningful_changes: int; needs_attention: int; worth_knowing: int
    stories: list[ChangeStory]
    personalization_summary: str = "Your ranking is based on market evidence. Feedback will personalize future prioritization."

class TimelineEvent(BaseModel):
    date: datetime
    label: str
    category: str
    symbol: str | None = None
    title: str
    summary: str
    meaningful: bool

class TimelineResponse(BaseModel):
    watchlist_id: int
    period: str
    start: datetime
    end: datetime
    total_events: int
    meaningful_events: int
    events: list[TimelineEvent]
    synthetic: bool = True


class AlertIn(BaseModel):
    sensitivity: str

class SmartAlertOut(BaseModel):
    id: int; symbol: str; title: str; summary: str; score: float; created_at: datetime; read: bool
