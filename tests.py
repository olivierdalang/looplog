import unittest
import warnings

from looplog import LoopLog


class TestStringMethods(unittest.TestCase):
    def test_basic(self):
        values = [1, 2, 3.5, 0, 5, "invalid", complex(1, 2)]
        results = []
        loop_log = LoopLog("testing floor div")
        for value in values:
            with loop_log.step(name=value):
                if isinstance(value, float) and not value.is_integer():
                    warnings.warn("Input will be rounded !")
                results.append(10 // value)
        loop_log.report()


if __name__ == "__main__":
    unittest.main()
