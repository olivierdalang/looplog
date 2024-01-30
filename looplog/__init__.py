try:
    from ._version import __version__
except ModuleNotFoundError:
    __version__ = "0.0.dev"
    version_tuple = (0, 0, "dev")


import logging
import sys
import warnings
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Iterable, List, Optional

SKIP = object()

SEPARATOR = "=" * 88


class StepType(Enum):
    """Possible step result types"""

    SKIPPED = "-"
    SUCCESS = "."
    WARNING = "!"
    ERROR = "X"


@dataclass
class StepLog:
    """Logging output of a step"""

    name: str
    exception: Exception
    warns: List
    skipped: bool
    output: Any

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
            logger.exception(self.exception)

        if self.warns:
            for warn in self.warns:
                logger.warning(warn.message)

        if self.skipped:
            logger.debug(f"{self.name} skipped")

        if not self.exception and not self.warns and not self.skipped:
            logger.debug(f"{self.name} succeeded")


class StepLogs:
    """List of logging outputs of all steps"""

    def __init__(self):
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

    def details(self) -> str:
        lines = []
        for log in self._list:
            if not log.exception and not log.warns:
                continue
            lines.append(SEPARATOR)
            if log.exception:
                lines.append(f"ERROR {log.name}: {log.exception}")
            if log.warns:
                for w in log.warns:
                    lines.append(f"WARNING {log.name}: {w.message}")
        lines.append(SEPARATOR)
        return "\n".join(lines)

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
    realtime_output: Optional[bool] = None,
    limit: Optional[int] = None,
    step_name: Optional[Callable[[Any], str]] = None,
    unmanaged=False,
) -> StepLogs:
    """Decorator running the given function against each value of the provided iterable values, logging warnings and exceptions for each one. This returns a StepLogs object.

    Args:
        values: List of items to iterate on
        name: The name of the loop, only used for printing to stdout.
        logger: Optional logger on which to log errors and warnings. Note that a stap may log more than one message.
        realtime_output: Whether to print in readtime to stdout. If left to none, will do so if stdout is a tty decide.
        limit: Limit the count of objects to created (ignoring the rest).
        step_name: A callable returning the name of the item in logging.
        unmanaged: If true, warnings and exceptions will be raised natively instead of being catched.

    Returns:
        StepLogs: _description_
    """

    def inner(function):
        steplogs = StepLogs()

        print_output = realtime_output is True or (
            realtime_output is None and sys.stdout.isatty()
        )
        if print_output:
            print(f"Starting loop `{name or function.__name__}`")

        for i, value in enumerate(values, start=1):
            output = None
            exception = None

            if limit is not None and i > limit:
                break

            skipped = False
            with warnings.catch_warnings(record=True) as warns:
                try:
                    ret = function(value)
                except Exception as e:
                    if unmanaged:
                        raise e
                    exception = e
                else:
                    if ret is SKIP:
                        skipped = True
            if unmanaged:
                for warn in warns:
                    warnings._showwarnmsg(warn)

            steplog = StepLog(
                name=step_name(value) if step_name else f"step_{i}",
                exception=exception,
                warns=warns,
                output=output,
                skipped=skipped,
            )
            if logger:
                steplog.emit(logger)
            if print_output:
                print(steplog.type.value, end="", flush=True)
            steplogs.append(steplog)

        if print_output:
            print()
            print(steplogs)

        return steplogs

    return inner
