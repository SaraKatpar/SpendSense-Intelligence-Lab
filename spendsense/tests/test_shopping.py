import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import storage
from shopping import order_fields,email_text,carts
class ShoppingTests(unittest.TestCase):
    def test_order_total_excludes_subtotal_and_shipping(self):
        result=order_fields('Store: Daraz\nSubtotal: PKR 2000\nShipping: 150\nOrder total: PKR 2,150.00')
        self.assertEqual(result['amount'],2150)
        self.assertEqual(result['merchant'],'Daraz')
        self.assertEqual(result['currency'],'PKR')
    def test_email_and_cart_persistence_without_spending(self):
        text=email_text(b'From: Store <orders@example.com>\nSubject: Order confirmed\nContent-Type: text/plain; charset=utf-8\n\nTotal paid: PKR 1,250\n')
        self.assertEqual(order_fields(text)['amount'],1250)
        with tempfile.TemporaryDirectory() as folder:
            old=storage.DB;storage.DB=Path(folder)/'test.db'
            try:
                storage.save_wallet('me',5000,'2026-12-01',500,100,20)
                carts('me','Shoes',1250)
                self.assertEqual(len(carts('me')),1)
                self.assertTrue(carts('someone else').empty)
                self.assertEqual(storage.wallet('me')['cash'],5000)
                self.assertTrue(storage.read('me').empty)
            finally:storage.DB=old
