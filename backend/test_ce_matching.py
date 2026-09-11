import unittest
from main import ce_3_0_matching_logic

class TestCEMatchingLogic(unittest.TestCase):
    
    def test_ce_3_0_auto_block_empty_box(self):
        # High evidence (0.8) + "empty_box" (+15) = 95.0% -> auto-block True
        result = ce_3_0_matching_logic(0.8, "empty_box")
        self.assertTrue(result["auto_block"])
        self.assertEqual(result["confidence_score"], 95.0)

    def test_ce_3_0_auto_block_wrong_item(self):
        # Med evidence (0.75) + "wrong_item" (+15) = 90.0% -> auto-block True
        result = ce_3_0_matching_logic(0.75, "wrong_item")
        self.assertTrue(result["auto_block"])
        self.assertEqual(result["confidence_score"], 90.0)

    def test_ce_3_0_no_block_defective(self):
        # High evidence (0.9) + "item_defective" (-10) = 80.0% -> auto-block False
        result = ce_3_0_matching_logic(0.9, "item_defective")
        self.assertFalse(result["auto_block"])
        self.assertEqual(result["confidence_score"], 80.0)

    def test_ce_3_0_score_capping(self):
        # 1.0 evidence (100) + "empty_box" (+15) should cap at 100
        result = ce_3_0_matching_logic(1.0, "empty_box")
        self.assertEqual(result["confidence_score"], 100.0)

if __name__ == '__main__':
    unittest.main()
