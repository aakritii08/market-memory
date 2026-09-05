from app.services.meaningfulness import score_change

def q(pct,vol=1.0,avg=1.0,v=.8): return {'pct_change':pct,'volume':vol,'average_volume':avg,'volatility':v}
def test_routine_move_is_low():
    r=score_change({},q(4,v=5.0),[]); assert r['score'] < 40
def test_earnings_signal_is_high():
    r=score_change({},q(2.1,3),[{'title':'Earnings beat'}]); assert r['score'] >= 70
