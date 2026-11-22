import sys,unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai_chat import reply
class ChatTests(unittest.TestCase):
    @patch('ai_chat.requests.post')
    def test_real_provider_contract_and_no_remote_storage(self,post):
        post.return_value=Mock(status_code=200)
        post.return_value.json.return_value={'message':{'content':'Your cart exceeds your remaining budget.'}}
        self.assertIn('cart',reply([{'role':'user','content':'Explain saving habits'}],{'cash':100}))
        self.assertFalse(post.call_args.kwargs['json']['stream'])
        self.assertEqual(post.call_args.args[0],'http://127.0.0.1:11434/api/chat')
        self.assertEqual(post.call_args.kwargs['json']['model'],'llama3.2:3b')
    @patch('ai_chat.requests.post')
    def test_provider_error_is_not_fake_advice(self,post):
        post.return_value=Mock(status_code=401)
        with self.assertRaises(RuntimeError):reply([],{})
