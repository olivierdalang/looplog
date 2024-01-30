import io
import logging
import unittest
import warnings
from contextlib import redirect_stdout

from looplog import SEPARATOR, SKIP, StepLog, StepLogs, looplog


class UsageTests(unittest.TestCase):
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
        @looplog([3.5, "invalid"], step_name=lambda v: f"item [{v}]")
        def func_custom_name(value):
            if isinstance(value, float) and not value.is_integer():
                warnings.warn("Input will be rounded !")
            10 // value

        self.assertTrue("WARNING item [3.5]" in func_custom_name.details())
        self.assertTrue("ERROR item [invalid]" in func_custom_name.details())

    def test_logger(self):
        logger = logging.getLogger("tests")
        with self.assertLogs("tests", level="DEBUG") as logstests:

            @looplog([1, None, 3.5, 0], logger=logger)
            def func_logger(value):
                if value is None:
                    return SKIP
                if isinstance(value, float) and not value.is_integer():
                    warnings.warn("Input will be rounded !")
                10 // value

            self.assertCountEqual(
                logstests.output,
                [
                    "DEBUG:tests:step_1 succeeded",
                    "DEBUG:tests:step_2 skipped",
                    "WARNING:tests:Input will be rounded !",
                    # TODO: not sure what NoneType: None is doing there
                    "ERROR:tests:integer division or modulo by zero\nNoneType: None",
                ],
            )

        self.assertEqual(func_logger.summary(), "1 ok / 1 warn / 1 err / 1 skip")

    def test_limit(self):
        @looplog([1, 2, 3, 4, 5], limit=3)
        def func_limit(value):
            10 // value

        self.assertEqual(func_limit.summary(), "3 ok / 0 warn / 0 err / 0 skip")

    def test_realtime_notty(self):
        # default without tty
        f = io.StringIO()
        with redirect_stdout(f):

            @looplog([1, 2, 3])
            def func(value):
                pass

        self.assertEqual("", f.getvalue())

    def test_realtime_tty(self):
        f = io.StringIO()
        f.isatty = lambda: True
        with redirect_stdout(f):

            @looplog([1, 2, 3])
            def func(value):
                pass

        self.assertEqual(
            f"Starting loop `func`\n...\n{SEPARATOR}\n3 ok / 0 warn / 0 err / 0 skip\n",
            f.getvalue(),
        )

    def test_realtime_yes(self):
        f = io.StringIO()
        with redirect_stdout(f):

            @looplog([1, 2, 3], realtime_output=True)
            def func(value):
                pass

        self.assertEqual(
            f"Starting loop `func`\n...\n{SEPARATOR}\n3 ok / 0 warn / 0 err / 0 skip\n",
            f.getvalue(),
        )

    def test_realtime_no(self):
        f = io.StringIO()
        f.isatty = lambda: True
        with redirect_stdout(f):

            @looplog([1, 2, 3], realtime_output=False)
            def func(value):
                pass

        self.assertEqual("", f.getvalue())

    def test_unmanaged(self):
        with self.assertWarns(UserWarning):
            with self.assertRaises(ZeroDivisionError):

                @looplog([1, 2.5, 0, 4, 5], unmanaged=True)
                def func_unmanaged(value):
                    if isinstance(value, float) and not value.is_integer():
                        warnings.warn("Input will be rounded !")
                    10 // value


class UnitTests(unittest.TestCase):
    def test_steplogs(self):
        log_a = StepLogs()
        log_a.append(
            StepLog(name="a", exception=None, warns=[], skipped=False, output="")
        )
        log_b = StepLogs()
        log_b.append(
            StepLog(name="b", exception=None, warns=["warn"], skipped=False, output="")
        )
        log_c = StepLogs()
        log_c.append(
            StepLog(
                name="c", exception=Exception("e"), warns=[], skipped=False, output=""
            )
        )
        log_d = StepLogs()
        log_d.append(
            StepLog(name="d", exception=None, warns=[], skipped=True, output="")
        )
        log_t = log_a + log_b + log_c + log_d

        self.assertEqual(
            (log_a.count_ok, log_a.count_warn, log_a.count_ko, log_a.count_skip),
            (1, 0, 0, 0),
        )
        self.assertEqual(
            (log_b.count_ok, log_b.count_warn, log_b.count_ko, log_b.count_skip),
            (0, 1, 0, 0),
        )
        self.assertEqual(
            (log_c.count_ok, log_c.count_warn, log_c.count_ko, log_c.count_skip),
            (0, 0, 1, 0),
        )
        self.assertEqual(
            (log_d.count_ok, log_d.count_warn, log_d.count_ko, log_d.count_skip),
            (0, 0, 0, 1),
        )
        self.assertEqual(
            (log_t.count_ok, log_t.count_warn, log_t.count_ko, log_t.count_skip),
            (1, 1, 1, 1),
        )


class RegressionTests(unittest.TestCase):
    def test_limit_none(self):
        # No limit (implicit)
        @looplog([1, 2, 3, 4, 5])
        def func_limit(value):
            10 // value

        self.assertEqual(func_limit.summary(), "5 ok / 0 warn / 0 err / 0 skip")

        # No limit (explicit)
        @looplog([1, 2, 3, 4, 5], limit=None)
        def func_limit(value):
            10 // value

        self.assertEqual(func_limit.summary(), "5 ok / 0 warn / 0 err / 0 skip")

        # 0 limit (should treat 0 items)
        @looplog([1, 2, 3, 4, 5], limit=0)
        def func_limit(value):
            10 // value

        self.assertEqual(func_limit.summary(), "0 ok / 0 warn / 0 err / 0 skip")


if __name__ == "__main__":
    unittest.main()
