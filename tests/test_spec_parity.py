import unittest

from tools.check_spec_parity import check


class SpecificationParityTest(unittest.TestCase):
    def test_current_specification_matches_web_contract(self):
        self.assertEqual(check(), [])


if __name__ == "__main__":
    unittest.main()
