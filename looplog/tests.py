import io
import logging
import re
import sys
import unittest
import warnings
from contextlib import redirect_stdout

from . import SKIP, StepLog, StepLogs, looplog


def collapse_carriage(text: str) -> str:
    """Helper to remove text before cariage returns"""
    return "\n".join(re.sub(".*\r", "", s) for s in text.split("\n"))


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
        self.assertEqual(
            func_basic.report(),
            "----------------------------------------------------------------------------------------\n"
            "Errors:\n"
            "    1   TypeError\n"
            "    1   ZeroDivisionError\n"
            "Warnings:\n"
            "    1   UserWarning\n",
        )
        self.assertEqual(
            func_basic.details(),
            "----------------------------------------------------------------------------------------\n"
            "step_9\n"
            "    ERROR: unsupported operand type(s) for //: 'int' and 'str'\n"
            "----------------------------------------------------------------------------------------\n"
            "step_11\n"
            "    WARN:  Input will be rounded !\n"
            "----------------------------------------------------------------------------------------\n"
            "step_13\n"
            "    ERROR: integer division or modulo by zero\n"
            "----------------------------------------------------------------------------------------\n",
        )

    def test_empty(self):
        @looplog([])
        def func_basic(value):
            # nothing to do
            pass

        self.assertEqual(func_basic.summary(), "0 ok / 0 warn / 0 err / 0 skip")

    def test_custom_step_name(self):
        @looplog([3.5, "invalid"], step_name=lambda v: f"item [{v}]")
        def func_custom_name(value):
            if isinstance(value, float) and not value.is_integer():
                warnings.warn("Input will be rounded !")
            10 // value

        self.assertIn(
            "----------------------------------------------------------------------------------------\n"
            "item [3.5]\n"
            "    WARN:  Input will be rounded !\n"
            "----------------------------------------------------------------------------------------\n",
            func_custom_name.details(),
        )
        self.assertIn(
            "----------------------------------------------------------------------------------------\n"
            "item [invalid]\n"
            "    ERROR: unsupported operand type(s) for //: 'int' and 'str'\n"
            "----------------------------------------------------------------------------------------\n",
            func_custom_name.details(),
        )

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

            logs = "\n".join(logstests.output)
            self.assertIn("DEBUG:tests:step_1 succeeded", logs)
            self.assertIn("DEBUG:tests:step_2 skipped", logs)
            self.assertIn("WARNING:tests:step_3 Input will be rounded !", logs)
            self.assertIn("ERROR:tests:step_4 integer division or modulo by zero", logs)
        self.assertEqual(func_logger.summary(), "1 ok / 1 warn / 1 err / 1 skip")

    def test_limit(self):
        @looplog([1, 2, 3, 4, 5], limit=3)
        def func_limit(value):
            10 // value

        self.assertEqual(func_limit.summary(), "3 ok / 0 warn / 0 err / 0 skip")

    def test_generator(self):
        @looplog((i for i in range(10)))
        def generator(i):
            pass

        self.assertEqual(generator.summary(), "10 ok / 0 warn / 0 err / 0 skip")

    @unittest.skipIf(sys.version_info < (3, 11), "add_note was introduced in py3.11")
    def test_exception_note(self):
        @looplog([1, 0], step_name=lambda v: f"item [{v}]")
        def func_div(value):
            try:
                10 / value
            except ZeroDivisionError as e:
                e.add_note("this was done on purpose")
                e.add_note("just saying")
                raise e

        self.assertEqual(
            "----------------------------------------------------------------------------------------\n"
            "item [0]\n"
            "    ERROR: division by zero [this was done on purpose] [just saying]\n"
            "----------------------------------------------------------------------------------------\n",
            func_div.details(),
        )

    def test_realtime_notty(self):
        # default without tty
        f = io.StringIO()
        with redirect_stdout(f):

            @looplog([1, 0, 3])
            def func(value):
                1 / value

        self.assertEqual(
            "",
            f.getvalue(),
        )

    def test_realtime_tty(self):
        f = io.StringIO()
        f.isatty = lambda: True
        with redirect_stdout(f):

            @looplog([1, 0, 3])
            def func(value):
                1 / value

        self.assertEqual(
            "========================================================================================\n"
            "Starting loop `func`...\n"
            "========================================================================================\n"
            "step_2\n"
            "    ERROR: division by zero\n"
            "----------------------------------------------------------------------------------------\n"
            "Finished `func` [3 steps][in 0:00:00][2 ok / 0 warn / 1 err / 0 skip]\n",
            collapse_carriage(f.getvalue()),
        )

    def test_realtime_nocheck(self):
        f = io.StringIO()
        f.isatty = lambda: True
        with redirect_stdout(f):

            @looplog([1, 0, 3], check_tty=False)
            def func(value):
                1 / value

        self.assertEqual(
            "========================================================================================\n"
            "Starting loop `func`...\n"
            "========================================================================================\n"
            "step_2\n"
            "    ERROR: division by zero\n"
            "----------------------------------------------------------------------------------------\n"
            "Finished `func` [3 steps][in 0:00:00][2 ok / 0 warn / 1 err / 0 skip]\n",
            collapse_carriage(f.getvalue()),
        )

    def test_realtime_empty(self):
        f = io.StringIO()
        f.isatty = lambda: True
        with redirect_stdout(f):

            @looplog([])
            def func(value):
                pass

        self.assertEqual(
            "========================================================================================\n"
            "Starting loop `func`...\n"
            "========================================================================================\n"
            "Finished `func` [0 steps][in 0:00:00][0 ok / 0 warn / 0 err / 0 skip]\n",
            collapse_carriage(f.getvalue()),
        )

    def test_realtime_short(self):
        f = io.StringIO()
        f.isatty = lambda: True
        with redirect_stdout(f):

            @looplog([1])
            def func(value):
                pass

        self.assertEqual(
            "========================================================================================\n"
            "Starting loop `func`...\n"
            "========================================================================================\n"
            "Finished `func` [1 steps][in 0:00:00][1 ok / 0 warn / 0 err / 0 skip]\n",
            collapse_carriage(f.getvalue()),
        )

    def test_unmanaged(self):
        with self.assertWarns(UserWarning):
            with self.assertRaises(ZeroDivisionError):

                @looplog([1, 2.5, 0, 4, 5], unmanaged=True)
                def func_unmanaged(value):
                    if isinstance(value, float) and not value.is_integer():
                        warnings.warn("Input will be rounded !")
                    10 // value

    def test_stdout(self):
        def my_func(value):
            print(f"i knew {value} would come")
            if value == 2:
                warnings.warn("soon the last one")
            if value == 3:
                raise Exception("this is the last one")

        # by default, stdout is shown only on warnings/errors
        @looplog([1, 2, 3])
        def stdout_default(value):
            my_func(value)

        self.assertEqual(
            stdout_default.details(),
            "----------------------------------------------------------------------------------------\n"
            "step_2\n"
            "    OUT:   i knew 2 would come\n"
            "    WARN:  soon the last one\n"
            "----------------------------------------------------------------------------------------\n"
            "step_3\n"
            "    OUT:   i knew 3 would come\n"
            "    ERROR: this is the last one\n"
            "----------------------------------------------------------------------------------------\n",
        )

        # check it works with always
        @looplog([1, 2, 3], capture_stdout="always")
        def stdout_always(value):
            my_func(value)

        self.assertEqual(
            stdout_always.details(),
            "----------------------------------------------------------------------------------------\n"
            "step_1\n"
            "    OUT:   i knew 1 would come\n"
            "----------------------------------------------------------------------------------------\n"
            "step_2\n"
            "    OUT:   i knew 2 would come\n"
            "    WARN:  soon the last one\n"
            "----------------------------------------------------------------------------------------\n"
            "step_3\n"
            "    OUT:   i knew 3 would come\n"
            "    ERROR: this is the last one\n"
            "----------------------------------------------------------------------------------------\n",
        )

        # check it works with never
        @looplog([1, 2, 3], capture_stdout="never")
        def stdout_never(value):
            my_func(value)

        self.assertEqual(
            stdout_never.details(),
            "----------------------------------------------------------------------------------------\n"
            "step_2\n"
            "    WARN:  soon the last one\n"
            "----------------------------------------------------------------------------------------\n"
            "step_3\n"
            "    ERROR: this is the last one\n"
            "----------------------------------------------------------------------------------------\n",
        )


class UnitTests(unittest.TestCase):
    def test_steplogs(self):
        log_a = StepLogs()
        log_a.append(StepLog(name="succeeded"))
        log_b = StepLogs()
        log_b.append(StepLog(name="warned", warns=["warn"]))
        log_c = StepLogs()
        log_c.append(StepLog(name="errored", exception=Exception("e")))
        log_d = StepLogs()
        log_d.append(StepLog(name="skipped", skipped=True))
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

    def test_nomessage_exception(self):
        @looplog([1])
        def func_limit(value):
            raise RuntimeError()

        self.assertEqual(
            func_limit.details(),
            "----------------------------------------------------------------------------------------\n"
            "step_1\n"
            "    ERROR: RuntimeError\n"
            "----------------------------------------------------------------------------------------\n",
        )


if __name__ == "__main__":
    unittest.main()
