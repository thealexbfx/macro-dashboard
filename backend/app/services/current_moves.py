from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from backend.app.registry.markets import MarketRegistry, MarketSpec
from backend.app.schemas.customer_answer import AnswerBlock, CustomerAnswer, ExperienceLink
from backend.app.services.catalysts import CatalystProvider, default_catalyst_provider
from backend.app.services.direct_answers import PublicTimeSeriesProvider, TimeSeriesProvider
from backend.app.services.historical_relationships import EXTRA_SERIES

EVIDENCE_PLANS = {
    "gold": ("gold","us10y_real","us2y","us10y","us30y","dxy","sp500"),
    "dxy": ("dxy","us2y","us10y","eurusd","usdjpy","gbpusd","sp500"),
    "sp500": ("sp500","us10y_real","us2y","us10y","dxy"),
    "us2y": ("us2y","us10y","us30y","dxy","sp500"),
    "us10y": ("us10y","us2y","us30y","us10y_real","us10y_breakeven","dxy"),
    "us30y": ("us30y","us10y","us2y","us10y_real","us10y_breakeven","dxy"),
}

@dataclass
class CurrentMoveInvestigationService:
    provider: TimeSeriesProvider
    catalysts: CatalystProvider
    today_fn: Any

    def __init__(self, provider: TimeSeriesProvider | None=None, catalysts: CatalystProvider | None=None, today_fn=None):
        self.provider=provider or PublicTimeSeriesProvider(); self.catalysts=catalysts or default_catalyst_provider(); self.today_fn=today_fn or date.today
        base=MarketRegistry(); self.specs={s.key:s for s in base.specs}; self.specs.update(EXTRA_SERIES)

    def _move(self,key):
        spec=self.specs[key]; end=self.today_fn(); start=end-timedelta(days=14)
        rows=self.provider.fred_series(spec.provider_id,start,end) if spec.provider=="fred" else self.provider.market_series(spec,start,end)
        if len(rows)<2: return None
        d0,v0=rows[-2]; d1,v1=rows[-1]
        if spec.kind=="yield": return {"key":key,"name":spec.name,"as_of":d1.isoformat(),"value":v1,"change_bps":(v1-v0)*100,"source":"FRED"}
        return {"key":key,"name":spec.name,"as_of":d1.isoformat(),"value":v1,"return_pct":((v1/v0)-1)*100 if v0 else None,"source":"Yahoo Finance"}

    @staticmethod
    def _sign(m):
        if not m:return 0
        x=m.get("change_bps",m.get("return_pct"))
        return 1 if x and x>0 else -1 if x and x<0 else 0

    def _mechanism(self,asset,m):
        d=lambda k:self._sign(m.get(k)); target=d(asset)
        if asset=="gold":
            if d("us10y_real")==-target and d("dxy")==-target: return "real-yield and US-dollar repricing","moderate"
            if d("us10y_real")==-target:return "real-yield repricing","moderate"
            if d("dxy")==-target:return "US-dollar repricing","moderate"
        if asset=="dxy" and d("us2y")==target:return "US rate-expectations repricing","moderate"
        if asset=="sp500" and d("us10y_real")==-target:return "real-rate repricing","moderate"
        if asset=="us2y": return "near-term Fed policy expectations","moderate"
        if asset in {"us10y","us30y"}:
            if d("us10y_real")==target:return "real-yield repricing","moderate"
            if asset=="us30y" and d("us2y")!=target:return "long-end / term-premium forces rather than near-term Fed expectations","moderate"
            if d("us2y")==target:return "broad rate-expectations repricing","moderate"
        return None,"low"

    def investigate(self, asset: str) -> CustomerAnswer:
        if asset not in EVIDENCE_PLANS: raise ValueError(f"Current-move investigation is not production-enabled for {asset}.")
        moves={}
        for key in EVIDENCE_PLANS[asset]:
            try: moves[key]=self._move(key)
            except Exception: moves[key]=None
        target=moves.get(asset)
        if not target: raise RuntimeError("Target market observation is unavailable.")
        mechanism, confidence=self._mechanism(asset,moves)
        context="\n".join(f"{x['name']}: {x.get('return_pct',x.get('change_bps')):+.2f}{'%' if 'return_pct' in x else 'bp'} as of {x['as_of']}" for x in moves.values() if x)
        search=self.catalysts.search(asset=self.specs[asset].name,market_context=context)
        event=search.candidates[0] if search.status=="ok" and search.candidates else None
        moveval=target.get("return_pct",target.get("change_bps")); unit="%" if "return_pct" in target else "bp"
        if mechanism:
            answer=f"{target['name']} moved {moveval:+.2f}{unit}. The available MacroLens cross-market evidence is most consistent with {mechanism}."
        else:
            answer=f"{target['name']} moved {moveval:+.2f}{unit}, but the available cross-market evidence does not isolate a convincing mechanism."
        if event: answer += f" A recent catalyst worth checking is: {event.title}."
        sources=[]
        for x in moves.values():
            if x: sources.append({"name":x["source"],"series":x["key"]})
        sources.extend({"name":s.get("title","Web source"),"url":s.get("url","")} for s in search.sources)
        return CustomerAnswer(status="ok",answer=answer,confidence=confidence,
            blocks=(AnswerBlock("market_evidence",f"{target['name']} investigation",{"asset":asset,"moves":[x for x in moves.values() if x],"candidate_catalysts":[c.to_dict() for c in search.candidates],"catalyst_status":search.status}),),
            limitations=("MacroLens ranks evidence consistency; it cannot prove a single cause for a market move.","Daily Yahoo/FRED observations can blur intraday reactions.","Web-search results are candidate catalysts, not proof of causation."),
            sources=tuple(sources),follow_up_questions=(f"Has {target['name']} behaved like this before?",f"What would make this explanation wrong?"),
            explore=(ExperienceLink(f"Explore {target['name']} evidence","Inspect the market series used in this investigation.",f"/markets/{asset}","Explore evidence"),))
