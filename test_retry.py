import unittest
from unittest.mock import MagicMock, patch
import time
from quant_engine.execution_futures import FuturesExecution

class TestRetryLogic(unittest.TestCase):
    @patch('quant_engine.execution_futures.requests.post')
    def test_retry_success(self, mock_post):
        # Setup: Fail twice (502), then succeed (200)
        mock_resp_fail = MagicMock()
        mock_resp_fail.status_code = 502
        
        mock_resp_success = MagicMock()
        mock_resp_success.status_code = 200
        mock_resp_success.json.return_value = {"orderId": 12345}
        
        mock_post.side_effect = [mock_resp_fail, mock_resp_fail, mock_resp_success]
        
        exec_mod = FuturesExecution("key", "secret", testnet=True)
        print("\n--- Testing Retry Logic (Expect 2 Retries) ---")
        res = exec_mod.place_order("BTCUSDT", "BUY", 0.1)
        
        self.assertIsNotNone(res)
        self.assertEqual(res['orderId'], 12345)
        self.assertEqual(mock_post.call_count, 3)
        print("✅ Retry Logic Verified: 3 attempts made, success returned.")

    @patch('quant_engine.execution_futures.requests.post')
    def test_retry_failure(self, mock_post):
        # Setup: Fail 3 times (504)
        mock_resp_fail = MagicMock()
        mock_resp_fail.status_code = 504
        
        mock_post.return_value = mock_resp_fail
        
        exec_mod = FuturesExecution("key", "secret", testnet=True)
        print("\n--- Testing Max Retries (Expect Failure) ---")
        res = exec_mod.place_order("BTCUSDT", "BUY", 0.1)
        
        self.assertIsNone(res)
        self.assertEqual(mock_post.call_count, 3)
        print("✅ Max Retries Verified: 3 attempts made, None returned.")

if __name__ == '__main__':
    unittest.main()
