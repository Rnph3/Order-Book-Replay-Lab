import unittest
from decimal import Decimal as D
from orderbook import Book,SequenceGap,CrossedBook,LiquidityError,generate,replay,measure_latency
class TestOrderBook(unittest.TestCase):
    def setUp(self):
        self.b=Book();self.b.snapshot(10,[['99','2'],['98','3']],[['101','2'],['102','3']],0)
    def test_mid(self):self.assertEqual(self.b.quote().mid,D(100))
    def test_spread(self):self.assertEqual(self.b.quote().spread_bps,D(200))
    def test_imbalance(self):self.assertEqual(self.b.quote().top_imbalance,D('0.5'))
    def test_buy_vwap(self):self.assertEqual(self.b.execute('buy',3),D(304)/3)
    def test_sell_vwap(self):self.assertEqual(self.b.execute('sell',3),D(296)/3)
    def test_liquidity(self):
        with self.assertRaises(LiquidityError):self.b.execute('buy',100)
    def test_invalid_side(self):
        with self.assertRaises(ValueError):self.b.execute('short',1)
    def test_nonpositive_qty(self):
        with self.assertRaises(ValueError):self.b.execute('buy',0)
    def test_update(self):
        self.assertTrue(self.b.apply(11,11,[['99','4']],[['101','0'],['102','2']],10));self.assertEqual(self.b.last_id,11)
    def test_stale_duplicate(self):
        self.assertFalse(self.b.apply(9,10,[],[],10))
    def test_overlap_accepted(self):
        self.assertTrue(self.b.apply(10,12,[['99','3']],[],10));self.assertEqual(self.b.last_id,12)
    def test_gap_rejected(self):
        with self.assertRaises(SequenceGap):self.b.apply(12,12,[],[],10)
        self.assertTrue(self.b.stale)
    def test_requires_snapshot_after_gap(self):
        with self.assertRaises(SequenceGap):self.b.apply(12,12,[],[],10)
        with self.assertRaises(SequenceGap):self.b.execute('buy',1)
        self.b.snapshot(12,[['99','2']],[['101','2']],10);self.assertFalse(self.b.stale)
    def test_crossed_snapshot(self):
        with self.assertRaises(CrossedBook):Book().snapshot(1,[['101','1']],[['100','1']])
    def test_crossed_update_atomic(self):
        with self.assertRaises(CrossedBook):self.b.apply(11,11,[['102','1']],[],10)
        self.assertEqual(self.b.last_id,10)
    def test_negative_qty_rejected(self):
        with self.assertRaises(ValueError):self.b.apply(11,11,[['99','-1']],[],10)
    def test_time_not_reversed(self):
        self.b.time_ms=100
        with self.assertRaises(ValueError):self.b.apply(11,11,[],[],50)
    def test_clone_independent(self):
        clone=self.b.clone();clone.bids[D(99)]=D(999);self.assertEqual(self.b.bids[D(99)],D(2))
    def test_generate_deterministic(self):self.assertEqual(list(generate(seed=1,n=15)),list(generate(seed=1,n=15)))
    def test_feed_replay(self):
        bs=replay(generate(seed=17,n=20));self.assertEqual(len(bs),21);self.assertFalse(bs[-1].stale)
    def test_latency_zero_identity(self):
        bs=replay(generate(seed=17,n=110));x=measure_latency(bs,latencies=(0,),qty='1');self.assertTrue(all(r['executed_ms']==r['signal_ms'] for r in x))
    def test_feed_has_synthetic_label(self):self.assertTrue(all(x['source']=='SYNTHETIC' for x in generate(n=10)))
    def test_invalid_updates(self):
        with self.assertRaises(ValueError): self.b.apply(12,11,[],[],10)
    def test_overlapping_price_spread(self):
        with self.assertRaises(CrossedBook):self.b.apply(11,11,[['101','2']],[],10)
if __name__=='__main__':unittest.main()
