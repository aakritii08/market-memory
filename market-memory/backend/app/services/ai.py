import httpx
from app.core.config import settings

def explain(evidence: dict) -> dict:
    # Deterministic fallback is intentionally safe: it can never invent an event.
    pct=evidence["current"].get("pct_change",0); vr=evidence["analysis"]["vol_ratio"]; events=evidence["events"]
    event_text=events[0]["title"] if events else "no major external event detected"
    summary=f"{evidence['company']['name']} moved {pct:+.1f}% since your last snapshot, with volume at {vr:.1f}× normal."
    reason=(f"{event_text}; " if events else "The move appears primarily market-data driven; ") + ", ".join(evidence["analysis"]["reason_parts"]) if evidence["analysis"]["reason_parts"] else "No strong abnormal signal was detected."
    matter="This deserves attention because the movement is unusual relative to the stock's normal behavior." if evidence["analysis"]["score"]>=70 else "This is worth knowing, but it is not outside the range of routine market noise."
    return {"summary":summary,"reason":reason,"why_it_matters":matter,"uncertainty":"Synthetic/demo evidence is illustrative; live provider coverage may differ." if settings.llm_base_url is None else "AI explanation grounded in supplied evidence.","confidence":min(.98,max(.55,evidence["analysis"]["score"]/100))}
