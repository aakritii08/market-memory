import math

def score_change(previous: dict, current: dict, events: list[dict]) -> dict:
    pct=abs(float(current.get("pct_change",0)))
    vol_ratio=(current.get("volume",0) or 0)/max(current.get("average_volume",1),1)
    vol_anomaly=min(30, max(0,(vol_ratio-1)*12))
    volatility=max(float(current.get("volatility",1)),0.1)
    movement=min(30, (pct/volatility)*8)
    news=min(25, len(events)*12)
    event_bonus=20 if events else 0
    score=min(100, round(movement+vol_anomaly+news+event_bonus))
    if abs(current.get("pct_change",0)) > volatility*3: score=min(100,score+10)
    category="needs_attention" if score>=70 else "worth_knowing" if score>=40 else "nothing"
    reasons=[]
    if movement>=10: reasons.append("movement is large relative to normal volatility")
    if vol_ratio>=1.8: reasons.append(f"volume is {vol_ratio:.1f}× normal")
    if events: reasons.append(f"{len(events)} relevant event(s) detected")
    return {"score":score,"category":category,"vol_ratio":round(vol_ratio,2),"reason_parts":reasons}
