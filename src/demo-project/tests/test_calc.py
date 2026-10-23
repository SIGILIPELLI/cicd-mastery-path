import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.calc import total
def test_total(): assert total([10, 20]) == 36.0
def test_empty(): assert total([]) == 0
def test_rate(): assert total([100], tax_rate=0.1) == 110.0
