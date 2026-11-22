import sys,unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from survival import hybrid_daily_costs


class HybridCostTests(unittest.TestCase):
    def test_due_essentials_optional_each_counted_once(self):
        dates=pd.date_range('2026-11-20',periods=3)
        dues=pd.DataFrame([{'due':'2026-11-19','amount':30,'paid':0},
            {'due':'2026-11-21','amount':40,'paid':0},{'due':'2026-11-21','amount':999,'paid':1},
            {'due':'2026-11-23','amount':999,'paid':0}])
        result=hybrid_daily_costs(10,dates,dues,[1,2,3])
        self.assertEqual(result.tolist(),[41,52,13])
    def test_no_cash_is_required_and_invalid_forecasts_reject(self):
        dates=pd.date_range('2026-11-20',periods=2)
        dues=pd.DataFrame(columns=['due','amount','paid'])
        self.assertEqual(hybrid_daily_costs(10,dates,dues,[1,2]).tolist(),[11,12])
        for values in ([1],[-1,2],[float('nan'),2]):
            with self.assertRaises(ValueError):hybrid_daily_costs(10,dates,dues,values)


if __name__=='__main__':unittest.main()
