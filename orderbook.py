"""Offline level-2 order-book reconstruction with integrity checks.
Synthetic feed uses Binance-like update IDs, but is NOT a real exchange feed.
"""
from __future__ import annotations
from bisect import bisect_left
from dataclasses import dataclass
from decimal import Decimal
import random

D=Decimal

class SequenceGap(ValueError): pass
class CrossedBook(ValueError): pass
class LiquidityError(ValueError): pass


def normalize(levels):
    out={}
    for p,q in levels:
        price,qty=D(str(p)),D(str(q))
        if price<=0 or qty<0:
            raise ValueError('price must be positive and quantity nonnegative')
        if qty>0: out[price]=qty
    return out

@dataclass
class Quote:
    time_ms: int
    mid: Decimal
    spread_bps: Decimal
    top_imbalance: Decimal

class Book:
    def __init__(self):
        self.bids={}; self.asks={}; self.last_id=None; self.time_ms=0;self.stale=True

    def snapshot(self, last_id, bids, asks, time_ms=0):
        b=normalize(bids);a=normalize(asks)
        self._validate(b,a)
        self.bids=b;self.asks=a;self.last_id=int(last_id)
        self.time_ms=int(time_ms);self.stale=False

    @staticmethod
    def _validate(b,a):
        if not b or not a:
            raise ValueError('two-sided liquidity required')
        if max(b)>=min(a):
            raise CrossedBook('bid must be below ask')

    def apply(self, first_id, last_id, bids, asks, time_ms):
        if self.stale or self.last_id is None:
            raise SequenceGap('book requires fresh snapshot')
        first_id,last_id=int(first_id),int(last_id)
        if first_id>last_id:
            raise ValueError('reversed update interval')
        if last_id<=self.last_id:
            return False  # stale duplicate already incorporated; no mutation
        if not(first_id<=self.last_id+1<=last_id):
            self.stale=True
            raise SequenceGap(f'expected {self.last_id+1}, observed [{first_id},{last_id}]')
        if int(time_ms)<self.time_ms:
            raise ValueError('nonmonotonic time')
        b=dict(self.bids);a=dict(self.asks)
        for side,patch in ((b,bids),(a,asks)):
            for p,q in patch:
                p,q=D(str(p)),D(str(q))
                if p<=0 or q<0:
                    raise ValueError('invalid price or quantity')
                if q==0: side.pop(p,None)
                else: side[p]=q
        self._validate(b,a)
        self.bids,self.asks=b,a
        self.last_id=last_id;self.time_ms=int(time_ms)
        return True

    def quote(self):
        if self.stale: raise SequenceGap('quote on stale book')
        bid=max(self.bids);ask=min(self.asks)
        mid=(bid+ask)/2
        imbalance=self.bids[bid]/(self.bids[bid]+self.asks[ask])
        return Quote(self.time_ms,mid,(ask-bid)/mid*D(10000),imbalance)

    def execute(self, side: str, quantity):
        """Immediate taker VWAP. Does NOT account for queue position or fills from real trades."""
        if self.stale: raise SequenceGap('execute on stale book')
        if side not in ('buy','sell'): raise ValueError('unknown side')
        remaining=D(str(quantity))
        if remaining<=0:raise ValueError('quantity must be positive')
        ladder=sorted(self.asks.items()) if side=='buy' else sorted(self.bids.items(),reverse=True)
        available=sum((qty for _,qty in ladder),D(0))
        if available<remaining:raise LiquidityError(f'available={available}, requested={remaining}')
        total=D(0)
        for price,volume in ladder:
            take=min(remaining,volume)
            total+=price*take
            remaining-=take
            if remaining==0:break
        return total/D(str(quantity))

    def clone(self):
        b=Book();b.bids=dict(self.bids);b.asks=dict(self.asks)
        b.last_id=self.last_id;b.time_ms=self.time_ms;b.stale=self.stale
        return b


def ladder(mid_tick: int, seed: int):
    """10 synthetic prices on 0.01 tick grid, 5 each side."""
    bids=[];asks=[]
    for i in range(1,6):
        bids.append([str(D(mid_tick-i)/100),str(D(1)+D((seed*7+i*3)%9)/10)])
        asks.append([str(D(mid_tick+i)/100),str(D(1)+D((seed*3+i*5)%11)/10)])
    return bids,asks


def generate(seed=17, n=600):
    """Explicitly synthetic, deterministic dataset, not replayed market data."""
    rng=random.Random(seed)
    center=10000
    b,a=ladder(center,0)
    yield {'type':'snapshot','time_ms':0,'lastUpdateId':1000,'bids':b,'asks':a,'source':'SYNTHETIC'}
    old_b,old_a=b,a
    for i in range(1,n+1):
        center+=rng.choices([-3,-2,-1,0,1,2,3],weights=[7,12,18,20,22,16,10])[0]
        b,a=ladder(center,i)
        old_bid={v[0] for v in old_b};old_ask={v[0] for v in old_a}
        new_bid={v[0] for v in b};new_ask={v[0] for v in a}
        updates_b=[[p,'0'] for p in sorted(old_bid-new_bid)]+b
        updates_a=[[p,'0'] for p in sorted(old_ask-new_ask)]+a
        yield {'type':'delta','time_ms':i*10,'U':1000+i,'u':1000+i,
               'b':updates_b,'a':updates_a,'source':'SYNTHETIC'}
        old_b,old_a=b,a


def replay(events):
    book=Book();snapshots=[]
    for ev in events:
        if ev['type']=='snapshot':
            book.snapshot(ev['lastUpdateId'],ev['bids'],ev['asks'],ev['time_ms'])
        elif ev['type']=='delta':
            book.apply(ev['U'],ev['u'],ev['b'],ev['a'],ev['time_ms'])
        else: raise ValueError('unknown event type')
        snapshots.append(book.clone())
    return snapshots


def measure_latency(books, latencies=(0,20,100,500),qty='2',fee_bps='5'):
    """Decision at index i, execution on first book at t_i+latency; no PnL claims."""
    times=[b.time_ms for b in books]
    if times!=sorted(times):raise ValueError('unsorted books')
    results=[]
    for i in range(20,len(books)-50,10):
        decision=books[i].quote()
        for delay in latencies:
            j=bisect_left(times,books[i].time_ms+delay)
            if j>=len(books):continue
            execution=books[j]
            fill=execution.execute('buy',qty)
            price_bps=(fill/decision.mid-1)*D(10000)
            end_j=min(j+20,len(books)-1)
            future_mid=books[end_j].quote().mid
            results.append({'signal_ms':books[i].time_ms,'delay_ms':delay,
                            'decision_mid':float(decision.mid),'fill_price':float(fill),
                            'cost_bps':float(price_bps+D(fee_bps)),
                            'post_fill_markout_bps':float((future_mid/fill-1)*D(10000)),
                            'top_imbalance':float(decision.top_imbalance),
                            'executed_ms':execution.time_ms})
    return results
