try:
    from ._version import __version__
except ModuleNotFoundError:
    __version__ = "0.0.dev"
    version_tuple = (0, 0, "dev")
import contextlib
import io
import logging
import sys
import warnings
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable, List, Literal, Optional, Sized, cast

from .utils import LineWriter, Timer, progress

SKIP = object()

SEPARATOR = "-" * 88
SEPARATOR_BOLD = "=" * 88


class StepType(Enum):
    """Possible step result types"""

    SKIPPED = "-"
    SUCCESS = "."
    WARNING = "!"
    ERROR = "X"


@dataclass
class StepLog:
    """Logging output of a step"""

    name: str = ""
    exception: Optional[Exception] = None
    warns: List[warnings.WarningMessage] = field(default_factory=list)
    stdout: str = ""
    skipped: bool = False
    output: Any = None

    @property
    def type(self):
        """Step type, based on the logged exceptions/errors"""
        if self.exception:
            return StepType.ERROR
        if self.warns:
            return StepType.WARNING
        if self.skipped:
            return StepType.SKIPPED
        return StepType.SUCCESS

    def emit(self, logger: logging.Logger) -> None:
        """Emit corresponding messages to the provided logger. Can emit mutiple messages."""
        if self.exception:
            logger.exception(f"{self.name} {self.exception}", exc_info=self.exception)

        if self.warns:
            for warn in self.warns:
                logger.warning(f"{self.name} {warn.message}")

        if self.skipped:
            logger.debug(f"{self.name} skipped")

        if not self.exception and not self.warns and not self.skipped:
            logger.debug(f"{self.name} succeeded")

    def details(self):
        retval = ""
        if self.stdout or self.warns or self.exception:
            retval += f"{self.name}\n"
            for message in self.messages():
                retval += f"{message}\n"
            retval += f"{SEPARATOR}\n"
        return retval

    def messages(self):
        for line in self.stdout.splitlines():
            yield f"    OUT:   {line}"
        for w in self.warns:
            yield f"    WARN:  {w.message}"
        if self.exception:
            exception_str = str(self.exception)
            if not exception_str:
                exception_str = self.exception.__class__.__name__
            msg = f"    ERROR: {exception_str}"
            if hasattr(self.exception, "__notes__"):
                notes = " ".join(f"[{note}]" for note in self.exception.__notes__)
                if notes:
                    msg += f" {notes}"
            yield msg


class StepLogs:
    """List of logging outputs of all steps"""

    def __init__(self) -> None:
        self._list: List[StepLog] = []
        self.count_ok = 0
        self.count_warn = 0
        self.count_ko = 0
        self.count_skip = 0

    def append(self, steplog: StepLog):
        self._list.append(steplog)
        if steplog.type == StepType.ERROR:
            self.count_ko += 1
        elif steplog.type == StepType.WARNING:
            self.count_warn += 1
        elif steplog.type == StepType.SKIPPED:
            self.count_skip += 1
        elif steplog.type == StepType.SUCCESS:
            self.count_ok += 1
        else:
            raise NotImplementedError()

    def __add__(self, other: "StepLogs"):
        sum_log = StepLogs()
        for steplog in self._list:
            sum_log.append(steplog)
        for steplog in other._list:
            sum_log.append(steplog)
        return sum_log

    def details(self):
        retval = SEPARATOR + "\n"
        for log in self._list:
            retval += log.details()
        return retval

    def report(self):
        retval = SEPARATOR + "\n"
        errors_counts: dict[type[Warning], int] = defaultdict(int)
        warnings_counts: dict[type[Warning], int] = defaultdict(int)
        for log in self._list:
            if log.exception:
                errors_counts[type(log.exception).__name__] += 1
            for warn in log.warns:
                warnings_counts[warn.category.__name__] += 1
        retval += "Errors:\n"
        for err_type, count in errors_counts.items():
            retval += f"    {count: <3} {err_type}\n"
        retval += "Warnings:\n"
        for warn_type, count in warnings_counts.items():
            retval += f"    {count: <3} {warn_type}\n"
        return retval

    def summary(self) -> str:
        return " / ".join(
            [
                f"{self.count_ok} ok",
                f"{self.count_warn} warn",
                f"{self.count_ko} err",
                f"{self.count_skip} skip",
            ]
        )

    def __str__(self):
        return "\n".join([self.details(), self.summary()])


def looplog(
    values: Iterable[Any],
    name: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
    check_tty: bool = True,
    limit: Optional[int] = None,
    step_name: Optional[Callable[[Any], str]] = None,
    unmanaged=False,
    capture_stdout: Literal["auto", "always", "never"] = "auto",
) -> Callable[[Callable[[Any], Any]], StepLogs]:
    """Decorator running the given function against each value of the provided iterable values, logging warnings and exceptions for each one. This returns a StepLogs object.

    Args:
        values: List of items to iterate on
        name: The name of the loop, only used for printing to stdout.
        logger: Optional logger on which to log errors and warnings. Note that a stap may log more than one message.
        check_tty: If true, will only print real time if output is a tty, otherwise always prints.
        limit: Limit the count of objects to created (ignoring the rest).
        step_name: A callable returning the name of the item in logging.
        unmanaged: If true, warnings and exceptions will be raised natively instead of being catched (note that this will cause reports to be empty)

    Returns:
        StepLogs: _description_
    """

    def inner(function: Callable):
        steplogs = StepLogs()

        loop_name = function.__name__ if name is None else name
        if hasattr(values, "__len__"):
            max_val = len(cast(Sized, values))
        else:
            max_val = None

        lw = LineWriter(enabled=not check_tty or sys.stdout.isatty())
        timer = Timer()

        lw.writeln(SEPARATOR_BOLD)
        lw.writeln(f"Starting loop `{loop_name}`...")
        lw.writeln(SEPARATOR_BOLD)

        i = -1
        for i, value in enumerate(values, start=0):
            lw.provln(
                f"{loop_name} [{progress(i, max_val)}][{i+1}/{max_val or '?'}][{timer}][{steplogs.summary()}]"
            )

            output = None
            exception = None
            skipped = False
            stdout = ""
            warns = []

            if limit is not None and i >= limit:
                break

            if unmanaged:
                output = function(value)

            else:
                stdout_io = io.StringIO()
                with contextlib.redirect_stdout(stdout_io):
                    with warnings.catch_warnings(record=True) as warns:
                        try:
                            output = function(value)
                        except Exception as e:
                            exception = e
                        else:
                            if output is SKIP:
                                skipped = True
                if capture_stdout == "always" or (
                    capture_stdout == "auto" and (exception or warns)
                ):
                    stdout = stdout_io.getvalue()

            steplog = StepLog(
                name=step_name(value) if step_name else f"step_{i+1}",
                exception=exception,
                warns=warns or [],
                stdout=stdout,
                output=output,
                skipped=skipped,
            )
            if logger:
                steplog.emit(logger)

            if steplog.output or steplog.warns or steplog.exception:
                lw.writeln(steplog.name)
                for message in steplog.messages():
                    lw.writeln(message)
                lw.writeln(SEPARATOR)

            steplogs.append(steplog)
        lw.writeln(
            f"Finished `{loop_name}` [{i+1} steps][in {timer}][{steplogs.summary()}]"
        )

        return steplogs

    return inner
