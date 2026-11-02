import csv,json,statistics
from pathlib import Path
from orderbook import generate,replay,measure_latency
out=Path('results');out.mkdir(exist_ok=True)
events=list(generate(seed=17,n=600))
with (out/'synthetic_depth_feed.jsonl').open('w') as f:
    for ev in events:f.write(json.dumps(ev)+'\n')
books=replay(events)
results=measure_latency(books)
with (out/'execution_samples.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
summary={'source':'DETERMINISTIC_SYNTHETIC_ONLY','seed':17,'depth_updates':len(events)-1,
         'sampled_buy_orders':len(results),'quantity_units':2,'assumed_taker_fee_bps':5,
         'delay_results':[]}
for latency in sorted(set(r['delay_ms'] for r in results)):
    group=[r for r in results if r['delay_ms']==latency]
    summary['delay_results'].append({'delay_ms':latency,'observations':len(group),
        'mean_execution_cost_bps':round(statistics.mean(r['cost_bps'] for r in group),5),
        'median_execution_cost_bps':round(statistics.median(r['cost_bps'] for r in group),5),
        'mean_post_fill_markout_bps':round(statistics.mean(r['post_fill_markout_bps'] for r in group),5)})
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
