from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc, text
from datetime import datetime, timezone, timedelta
from app.db.session import Base, engine, get_db
from app.models.models import User, Watchlist, WatchlistItem, Snapshot, MarketEvent, Feedback, SmartAlert, DemoState
from app.schemas.schemas import *
from app.core.config import settings
from app.core.security import *
from app.providers.synthetic import SyntheticProvider
from app.services.meaningfulness import score_change
from app.services.ai import explain

Base.metadata.create_all(bind=engine)
app=FastAPI(title="Market Memory API", version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(',')],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])

def current_user(authorization: str|None=Header(None), db:Session=Depends(get_db)):
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401,'Authentication required')
    try: uid=int(decode_token(authorization.split(' ',1)[1])['sub'])
    except Exception: raise HTTPException(401,'Invalid token')
    user=db.get(User,uid)
    if not user: raise HTTPException(401,'User not found')
    return user

def owned_watchlist(wid,user,db):
    w=db.get(Watchlist,wid)
    if not w or w.user_id!=user.id: raise HTTPException(404,'Watchlist not found')
    return w

@app.get('/health')
def health(db:Session=Depends(get_db)):
    db.execute(text('SELECT 1'))
    return {'status':'ok','database':'ok'}

@app.post('/api/auth/register',response_model=Token)
def register(data:AuthIn,db:Session=Depends(get_db)):
    if db.query(User).filter(User.email==data.email).first(): raise HTTPException(409,'Email already registered')
    u=User(email=data.email,password_hash=hash_password(data.password)); db.add(u); db.commit(); db.refresh(u)
    # Give every new user an immediately usable default watchlist.
    db.add(Watchlist(user_id=u.id,name="My Market Memory")); db.commit()
    return {'token':create_token(u.id)}
@app.post('/api/auth/login',response_model=Token)
def login(data:AuthIn,db:Session=Depends(get_db)):
    u=db.query(User).filter(User.email==data.email).first()
    if not u or not verify_password(data.password,u.password_hash): raise HTTPException(401,'Invalid credentials')
    return {'token':create_token(u.id)}

@app.get('/api/watchlists')
def list_watchlists(user=Depends(current_user),db:Session=Depends(get_db)):
    return db.query(Watchlist).filter(Watchlist.user_id==user.id).all()
@app.post('/api/watchlists')
def create_watchlist(data:WatchlistCreate,user=Depends(current_user),db:Session=Depends(get_db)):
    w=Watchlist(user_id=user.id,name=data.name); db.add(w); db.commit(); db.refresh(w); return w
@app.patch('/api/watchlists/{wid}')
def update_watchlist(wid:int,data:WatchlistUpdate,user=Depends(current_user),db:Session=Depends(get_db)):
    w=owned_watchlist(wid,user,db)
    if data.name is not None: w.name=data.name
    if data.sensitivity in {'low','medium','high'}: w.sensitivity=data.sensitivity
    db.commit(); return w
@app.delete('/api/watchlists/{wid}')
def delete_watchlist(wid:int,user=Depends(current_user),db:Session=Depends(get_db)):
    w=owned_watchlist(wid,user,db); db.delete(w); db.commit(); return {'ok':True}
@app.post('/api/watchlists/{wid}/items')
def add_item(wid:int,data:SymbolIn,user=Depends(current_user),db:Session=Depends(get_db)):
    w=owned_watchlist(wid,user,db); s=data.symbol.upper()
    if not SyntheticProvider().company(s): raise HTTPException(400,'Unsupported demo symbol')
    if db.query(WatchlistItem).filter_by(watchlist_id=wid,symbol=s).first(): return {'ok':True}
    pos=len(w.items); db.add(WatchlistItem(watchlist_id=wid,symbol=s,position=pos)); db.commit(); return {'ok':True}
@app.delete('/api/watchlists/{wid}/items/{symbol}')
def remove_item(wid:int,symbol:str,user=Depends(current_user),db:Session=Depends(get_db)):
    owned_watchlist(wid,user,db); item=db.query(WatchlistItem).filter_by(watchlist_id=wid,symbol=symbol.upper()).first()
    if item: db.delete(item); db.commit()
    return {'ok':True}
@app.put('/api/watchlists/{wid}/reorder')
def reorder(wid:int,data:ReorderIn,user=Depends(current_user),db:Session=Depends(get_db)):
    w=owned_watchlist(wid,user,db); items={i.symbol:i for i in w.items}
    for idx,s in enumerate(data.symbols):
        if s in items: items[s].position=idx
    db.commit(); return {'ok':True}


@app.get('/api/watchlists/{wid}/alerts', response_model=list[SmartAlertOut])
def list_alerts(wid:int,user=Depends(current_user),db:Session=Depends(get_db)):
    owned_watchlist(wid,user,db)
    return db.query(SmartAlert).filter(SmartAlert.watchlist_id==wid).order_by(desc(SmartAlert.created_at)).limit(20).all()

@app.patch('/api/watchlists/{wid}/alerts/settings')
def update_alert_settings(wid:int,data:AlertIn,user=Depends(current_user),db:Session=Depends(get_db)):
    w=owned_watchlist(wid,user,db)
    if data.sensitivity not in {'low','medium','high'}: raise HTTPException(400,'Sensitivity must be low, medium or high')
    w.sensitivity=data.sensitivity; db.commit()
    return {'watchlist_id':wid,'sensitivity':w.sensitivity,'meaningful_threshold':{'low':70,'medium':55,'high':40}[w.sensitivity]}

@app.post('/api/watchlists/{wid}/alerts/check')
def check_alerts(wid:int,user=Depends(current_user),db:Session=Depends(get_db)):
    w=owned_watchlist(wid,user,db)
    # Alerts evaluate the latest persisted snapshot against the snapshot immediately before it.
    # This avoids comparing the demo state to itself and keeps alerts deterministic.
    snapshots=db.query(Snapshot).filter(Snapshot.watchlist_id==wid).order_by(desc(Snapshot.created_at)).limit(2).all()
    if len(snapshots) < 2: return {'created':0,'alerts':[]}
    current_snap, previous_snap = snapshots[0], snapshots[1]
    threshold={'low':70,'medium':55,'high':40}.get(w.sensitivity,55)
    provider=SyntheticProvider(watchlist_scenario(wid,db))
    created=[]
    previous_data=previous_snap.data or {}
    for item in w.items:
        q=provider.quote(item.symbol)
        old=previous_data.get(item.symbol,{})
        events=provider.events(item.symbol, previous_snap.created_at)
        analysis=score_change(old,q,events)
        status=q['data_status']
        if provider.scenario=='conflicting_data' and item.symbol=='MSFT': status='conflict'
        if analysis['score'] < threshold or status in {'stale','conflict'}: continue
        recent=db.query(SmartAlert).filter(SmartAlert.watchlist_id==wid,SmartAlert.symbol==item.symbol).order_by(desc(SmartAlert.created_at)).first()
        if recent and (datetime.now(timezone.utc)-recent.created_at).total_seconds()<300: continue
        packet={'symbol':item.symbol,'company':provider.company(item.symbol),'previous':old,'current':q,'events':events,'analysis':analysis}
        ai=explain(packet)
        a=SmartAlert(user_id=user.id,watchlist_id=wid,symbol=item.symbol,title=f'{item.symbol}: meaningful change detected',summary=ai['summary'],score=analysis['score'])
        db.add(a); db.flush(); created.append(a)
    db.commit()
    return {'created':len(created),'alerts':[{'id':a.id,'symbol':a.symbol,'title':a.title,'summary':a.summary,'score':a.score,'created_at':a.created_at,'read':a.read} for a in created]}

@app.post('/api/alerts/{alert_id}/read')
def mark_alert_read(alert_id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    a=db.get(SmartAlert,alert_id)
    if not a or a.user_id!=user.id: raise HTTPException(404,'Alert not found')
    a.read=True; db.commit(); return {'ok':True}

@app.get('/api/market/search')
def search(q:str=''):
    q=q.upper(); return [{'symbol':s,'name':n} for s,n in __import__('app.providers.synthetic',fromlist=['COMPANIES']).COMPANIES.items() if q in s or q in n.upper()]

@app.post('/api/watchlists/{wid}/demo/{scenario}')
def demo(wid:int,scenario:str,user=Depends(current_user),db:Session=Depends(get_db)):
    owned_watchlist(wid,user,db)
    allowed={'normal','earnings_surprise','breaking_news','unusual_volume','sector_movement','conflicting_data','stale_data','repeated_small_movements','volatile_normal'}
    if scenario not in allowed: raise HTTPException(400,'Unknown scenario')
    state=db.query(DemoState).filter(DemoState.watchlist_id==wid).first()
    if not state:
        state=DemoState(watchlist_id=wid,scenario=scenario); db.add(state)
    else:
        state.scenario=scenario
    db.commit()
    return {'scenario':scenario,'watchlist_id':wid}

def watchlist_scenario(wid:int,db:Session):
    state=db.query(DemoState).filter(DemoState.watchlist_id==wid).first()
    return state.scenario if state else 'normal'

def personalization_for(user_id:int, symbol:str, db:Session):
    rows=db.query(Feedback).filter(Feedback.user_id==user_id, Feedback.symbol==symbol.upper()).all()
    if not rows:
        return 0.0, "Default ranking"
    weights={'helpful':1.0,'somewhat helpful':0.35,'not helpful':-1.0}
    avg=sum(weights.get(r.rating,0) for r in rows)/len(rows)
    # Small, bounded ranking adjustment: feedback changes ordering, never factual Meaningfulness.
    boost=max(-8.0,min(8.0,avg*4.0))
    if avg>=0.5: label=f"Prioritized from your feedback ({len(rows)} ratings)"
    elif avg<0: label=f"Deprioritized from your feedback ({len(rows)} ratings)"
    else: label=f"Personalized from your feedback ({len(rows)} ratings)"
    return round(boost,1), label

@app.get('/api/watchlists/{wid}/personalization')
def personalization(wid:int,user=Depends(current_user),db:Session=Depends(get_db)):
    owned_watchlist(wid,user,db)
    rows=db.query(Feedback).filter(Feedback.user_id==user.id).all()
    counts={'helpful':0,'somewhat helpful':0,'not helpful':0}
    symbols={}
    for r in rows:
        counts[r.rating]=counts.get(r.rating,0)+1
        symbols[r.symbol]=symbols.get(r.symbol,0)+1
    top=sorted(symbols.items(), key=lambda x:x[1], reverse=True)[:5]
    return {'ratings':counts,'total':len(rows),'top_symbols':[{'symbol':s,'ratings':n} for s,n in top]}

@app.get('/api/watchlists/{wid}/dashboard',response_model=Dashboard)
def dashboard(wid:int,user=Depends(current_user),db:Session=Depends(get_db)):
    w=owned_watchlist(wid,user,db); now=datetime.now(timezone.utc)
    provider=SyntheticProvider(watchlist_scenario(wid,db))
    previous=db.query(Snapshot).filter(Snapshot.watchlist_id==wid).order_by(desc(Snapshot.created_at)).first()
    current={}; stories=[]
    for item in w.items:
        q=provider.quote(item.symbol); company=provider.company(item.symbol); events_raw=provider.events(item.symbol, previous.created_at if previous else None)
        events=[]
        for e in events_raw:
            events.append(e)
        current[item.symbol]={'quote':q,'company':company,'events':events}
        old=(previous.data.get(item.symbol,{}).get('quote',{}) if previous else q)
        analysis=score_change(old,q,events)
        ev=[]
        status=q['data_status']
        ev.append(Evidence(type='price',value=f"{q['pct_change']:+.2f}%",source='Synthetic Market Feed',timestamp=datetime.fromisoformat(q['timestamp']),freshness=status,confidence=.98))
        ev.append(Evidence(type='volume',value=f"{analysis['vol_ratio']:.1f}× normal",source='Synthetic Market Feed',timestamp=datetime.fromisoformat(q['timestamp']),freshness=status,confidence=.96))
        if provider.scenario=='conflicting_data' and item.symbol=='MSFT':
            status='conflict'
            ev.append(Evidence(type='source A',value=f"${q['price']:.2f}",source='Synthetic Market Feed A',timestamp=datetime.fromisoformat(q['timestamp']),freshness='fresh',confidence=.91))
            ev.append(Evidence(type='source B',value=f"${q['price']+1.85:.2f}",source='Synthetic Market Feed B',timestamp=datetime.fromisoformat(q['timestamp']),freshness='fresh',confidence=.89))
        for e in events: ev.append(Evidence(type='event',value=e['title'],source=e['source'],timestamp=datetime.fromisoformat(e['timestamp']),freshness='fresh',confidence=e['reliability']))
        packet={'symbol':item.symbol,'company':company,'previous':old,'current':q,'events':events,'analysis':analysis}
        ai=explain(packet)
        if status=='conflict':
            ai={'summary':'MSFT data is excluded from the AI conclusion because two sources disagree.','reason':'Conflicting price values were detected across independent synthetic sources.','why_it_matters':'Questionable data should not be turned into a confident market explanation.','uncertainty':'The system cannot establish a trustworthy current value until the sources agree.','confidence':.89}
        boost, personalization_label = personalization_for(user.id,item.symbol,db)
        stories.append(ChangeStory(symbol=item.symbol,company=company['name'],category=analysis['category'],price=q['price'],pct_change=q['pct_change'],score=analysis['score'],summary=ai['summary'],reason=ai['reason'],why_it_matters=ai['why_it_matters'],uncertainty=ai['uncertainty'],confidence=ai['confidence'],evidence=ev,data_status=status,personalization_boost=boost,personalization_label=personalization_label))
    category_order={'needs_attention':0,'worth_knowing':1,'nothing':2}
    stories.sort(key=lambda x:(category_order.get(x.category,9),-(x.score+x.personalization_boost)))
    snap=Snapshot(watchlist_id=wid,data=current); db.add(snap); db.commit()
    away=int((now-previous.created_at).total_seconds()) if previous else 0
    total_feedback=db.query(Feedback).filter(Feedback.user_id==user.id).count()
    personalization_summary=(f"Your feedback is shaping the order of change stories. {total_feedback} rating" + ("s" if total_feedback!=1 else "") + " collected; Meaningfulness scores remain unchanged.")
    return Dashboard(watchlist_id=wid,previous_visit=previous.created_at if previous else None,away_seconds=away,meaningful_changes=sum(x.score>=40 for x in stories),needs_attention=sum(x.category=='needs_attention' for x in stories),worth_knowing=sum(x.category=='worth_knowing' for x in stories),stories=stories,personalization_summary=personalization_summary)

@app.get('/api/watchlists/{wid}/timeline', response_model=TimelineResponse)
def timeline(wid:int, period:str='since_last_visit', start:str|None=None, end:str|None=None, user=Depends(current_user), db:Session=Depends(get_db)):
    owned_watchlist(wid,user,db)
    now=datetime.now(timezone.utc)
    latest=db.query(Snapshot).filter(Snapshot.watchlist_id==wid).order_by(desc(Snapshot.created_at)).all()
    if period=='since_last_visit':
        if len(latest)>=2:
            start_dt=latest[1].created_at
            end_dt=latest[0].created_at
        elif latest:
            start_dt=latest[0].created_at
            end_dt=now
        else:
            start_dt=now-timedelta(hours=6)
            end_dt=now
    elif period=='24h':
        start_dt=now-timedelta(hours=24); end_dt=now
    elif period=='7d':
        start_dt=now-timedelta(days=7); end_dt=now
    elif period=='custom':
        try:
            start_dt=datetime.fromisoformat((start or '').replace('Z','+00:00'))
            end_dt=datetime.fromisoformat((end or '').replace('Z','+00:00'))
            if start_dt.tzinfo is None: start_dt=start_dt.replace(tzinfo=timezone.utc)
            if end_dt.tzinfo is None: end_dt=end_dt.replace(tzinfo=timezone.utc)
        except Exception:
            raise HTTPException(400,'Custom period requires valid start and end dates')
    else:
        raise HTTPException(400,'Unknown timeline period')
    if end_dt<=start_dt: raise HTTPException(400,'Timeline end must be after start')

    # Deterministic synthetic history makes the competition demo reproducible without live APIs.
    items=list(db.query(WatchlistItem).filter(WatchlistItem.watchlist_id==wid).order_by(WatchlistItem.position).all())
    symbols=[i.symbol for i in items]
    events=[]
    def add(dt,label,category,symbol,title,summary,meaningful):
        if start_dt <= dt <= end_dt:
            events.append(TimelineEvent(date=dt,label=label,category=category,symbol=symbol,title=title,summary=summary,meaningful=meaningful))
    scenario=watchlist_scenario(wid,db)
    if period=='since_last_visit':
        if scenario=='earnings_surprise' and 'NVDA' in symbols:
            add(start_dt+(end_dt-start_dt)*0.65,'TODAY','Earnings','NVDA','Earnings beat expectations','NVDA showed an earnings-related move with unusually high volume.',True)
        elif scenario=='breaking_news' and 'TSLA' in symbols:
            add(start_dt+(end_dt-start_dt)*0.65,'TODAY','Breaking news','TSLA','Major company announcement','TSLA moved after a synthetic breaking-news event.',True)
        elif scenario=='unusual_volume' and 'AAPL' in symbols:
            add(start_dt+(end_dt-start_dt)*0.65,'TODAY','Unusual activity','AAPL','Unusual trading activity','AAPL showed volume well above its normal baseline.',True)
        elif scenario=='conflicting_data' and 'MSFT' in symbols:
            add(start_dt+(end_dt-start_dt)*0.65,'TODAY','Data quality','MSFT','Conflicting market reports','Conflicting synthetic sources were detected and excluded from the AI conclusion.',True)
        elif scenario=='repeated_small_movements' and 'AMZN' in symbols:
            add(start_dt+(end_dt-start_dt)*0.55,'TODAY','Momentum','AMZN','Accumulated momentum','Several small moves combined into a meaningful change.',True)
        else:
            add(start_dt+(end_dt-start_dt)*0.5,'TODAY','Normal','', 'Routine market movement','No meaningful developments were detected in the selected period.',False)
    else:
        anchors=[
            ('MONDAY','Normal',None,'Normal market activity','Routine movement within normal ranges.',False),
            ('TUESDAY','Earnings','NVDA','Earnings beat expectations','Earnings-related evidence created a meaningful change.',True),
            ('WEDNESDAY','Analyst','AAPL','Analyst sentiment improved','A modest sentiment change was detected.',False),
            ('THURSDAY','Unusual activity','AAPL','Unusual trading activity','Volume moved materially above the normal baseline.',True),
            ('FRIDAY','Sector','NVDA','Semiconductor sector strengthens','Sector movement provided context for several stocks.',False),
            ('SATURDAY','Data quality','MSFT','Conflicting market reports','Conflicting values were flagged rather than silently selected.',True),
            ('SUNDAY','Normal',None,'No significant developments','Most watchlist names remained within normal behavior.',False),
        ]
        span=end_dt-start_dt
        for idx,(label,cat,sym,title,summary,meaningful) in enumerate(anchors):
            dt=start_dt+span*((idx+1)/(len(anchors)+1))
            if sym and sym not in symbols: sym=None
            add(dt,label,cat,sym,title,summary,meaningful)
    events.sort(key=lambda x:x.date)
    return TimelineResponse(watchlist_id=wid,period=period,start=start_dt,end=end_dt,total_events=len(events),meaningful_events=sum(e.meaningful for e in events),events=events)

@app.post('/api/feedback')
def feedback(data:FeedbackIn,user=Depends(current_user),db:Session=Depends(get_db)):
    if data.rating not in {'helpful','somewhat helpful','not helpful'}: raise HTTPException(400,'Invalid rating')
    db.add(Feedback(user_id=user.id,symbol=data.symbol.upper(),rating=data.rating)); db.commit(); return {'ok':True}
