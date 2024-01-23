import logging
import unittest
import warnings

from looplog import SKIP, looplog


class TestStringMethods(unittest.TestCase):
    def test_basic(self):
        @looplog(
            [1, 2, 3, 4, 5, 6, 7, 8, "9", 10, 11.5, 12, 0, 13, None, 15],
        )
        def func_basic(value):
            if value is None:
                return SKIP
            if isinstance(value, float) and not value.is_integer():
                warnings.warn("Input will be rounded !")
            10 // value

        self.assertEqual(func_basic.summary(), "12 ok / 1 warn / 2 err / 1 skip")

    def test_custom_step_name(self):
        @looplog([3.5, "invalid"], step_name_callable=lambda i, v: f"{i:03}-{v}")
        def func_custom_name(value):
            if isinstance(value, float) and not value.is_integer():
                warnings.warn("Input will be rounded !")
            10 // value

        self.assertTrue("WARNING 001-3.5" in func_custom_name.details())
        self.assertTrue("ERROR 002-invalid" in func_custom_name.details())

    def test_logger(self):
        logger = logging.getLogger()
        logging.basicConfig(filename="example.log", level=logging.DEBUG)

        @looplog([1, None, 3.5, 0], logger=logger)
        def func_logger(value):
            if value is None:
                return SKIP
            if isinstance(value, float) and not value.is_integer():
                warnings.warn("Input will be rounded !")
            10 // value

        self.assertEqual(func_logger.summary(), "1 ok / 1 warn / 1 err / 1 skip")

    def test_limit(self):
        @looplog([1, 2, 3, 4, 5], limit=3)
        def func_limit(value):
            10 // value

        self.assertEqual(func_limit.summary(), "3 ok / 0 warn / 0 err / 0 skip")

    def test_unmanaged(self):
        with self.assertWarns(UserWarning):
            with self.assertRaises(ZeroDivisionError):

                @looplog([1, 2.5, 0, 4, 5], unmanaged=True)
                def func_unmanaged(value):
                    if isinstance(value, float) and not value.is_integer():
                        warnings.warn("Input will be rounded !")
                    10 // value


if __name__ == "__main__":
    unittest.main()
