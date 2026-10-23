from __future__ import annotations
import json, os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

@dataclass(frozen=True)
class CatalystCandidate:
    title: str; summary: str; category: str; published_at: str | None; source_name: str | None; source_url: str | None; relevance_score: float
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class CatalystSearchResult:
    status: str; candidates: tuple[CatalystCandidate, ...]; sources: tuple[dict[str,str], ...]; note: str | None = None

class CatalystProvider(Protocol):
    def search(self, *, asset: str, market_context: str) -> CatalystSearchResult: ...

class DisabledCatalystProvider:
    def search(self, *, asset: str, market_context: str) -> CatalystSearchResult:
        return CatalystSearchResult("disabled", (), (), "Set OPENAI_API_KEY to enable targeted current-event research.")

class OpenAIWebCatalystProvider:
    def __init__(self, model: str | None=None, api_key: str | None=None):
        self.model=model or os.getenv("MACROLENS_WEB_MODEL","gpt-5.6-luna"); self.api_key=api_key or os.getenv("OPENAI_API_KEY")
    def search(self, *, asset: str, market_context: str) -> CatalystSearchResult:
        if not self.api_key: return DisabledCatalystProvider().search(asset=asset, market_context=market_context)
        from openai import OpenAI
        prompt=f'''You are MacroLens' catalyst-retrieval layer. Search the live web for recent developments plausibly relevant to this move. Do not decide causation. Prefer primary official sources and reputable financial reporting. Return JSON only: {{"candidates":[{{"title":"...","summary":"...","category":"macro_data|central_bank|fiscal_policy|geopolitics|asset_specific|other","published_at":null,"source_name":null,"source_url":null,"relevance_score":0.0}}]}}. At most 5.\nAsset: {asset}\nObserved evidence:\n{market_context}'''
        response=OpenAI(api_key=self.api_key).responses.create(model=self.model,tools=[{"type":"web_search"}],tool_choice="required",include=["web_search_call.action.sources"],input=prompt)
        sources=[]; seen=set()
        for item in getattr(response,"output",[]) or []:
            action=getattr(item,"action",None)
            for source in getattr(action,"sources",[]) or []:
                url=getattr(source,"url",None)
                if url and url not in seen:
                    seen.add(url); sources.append({"title":getattr(source,"title",None) or url,"url":url})
        try: payload=json.loads((getattr(response,"output_text","") or "").strip())
        except json.JSONDecodeError: return CatalystSearchResult("parse_error",(),tuple(sources),"Search completed but structured candidate output could not be parsed safely.")
        out=[]
        for row in payload.get("candidates",[])[:5]:
            try:
                out.append(CatalystCandidate(str(row.get("title","")).strip(),str(row.get("summary","")).strip(),str(row.get("category","other")),row.get("published_at"),row.get("source_name"),row.get("source_url"),max(0,min(float(row.get("relevance_score",0)),1))))
            except (TypeError,ValueError): pass
        return CatalystSearchResult("ok",tuple(out),tuple(sources))

class CachedCatalystProvider:
    def __init__(self, provider: CatalystProvider, ttl_seconds: int=300):
        from time import monotonic
        self.provider=provider; self.ttl=ttl_seconds; self.clock=monotonic; self.cache={}
    def search(self, *, asset: str, market_context: str):
        key=(asset.lower(),market_context); now=self.clock(); hit=self.cache.get(key)
        if hit and now-hit[0] <= self.ttl: return hit[1]
        result=self.provider.search(asset=asset,market_context=market_context)
        if result.status in {"ok","disabled"}: self.cache[key]=(now,result)
        return result

def default_catalyst_provider():
    base=OpenAIWebCatalystProvider() if os.getenv("OPENAI_API_KEY") else DisabledCatalystProvider()
    return CachedCatalystProvider(base)
