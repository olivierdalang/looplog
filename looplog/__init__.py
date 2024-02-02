try:
    from ._version import __version__
except ModuleNotFoundError:
    __version__ = "0.0.dev"
    version_tuple = (0, 0, "dev")
import logging
import sys
import warnings
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable, List, Optional

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
    warns: List = field(default_factory=list)
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
        if self.warns or self.exception:
            retval += f"{self.name}\n"
            if self.warns:
                for w in self.warns:
                    retval += f"    WARN:  {w.message}\n"
            if self.exception:
                retval += f"    ERROR: {self.exception}\n"
            retval += f"{SEPARATOR}\n"
        return retval


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

    def details(self):
        retval = SEPARATOR + "\n"
        for log in self._list:
            retval += log.details()
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
) -> Callable[[Callable[[Any], Any]], StepLogs]:
    """Decorator running the given function against each value of the provided iterable values, logging warnings and exceptions for each one. This returns a StepLogs object.

    Args:
        values: List of items to iterate on
        name: The name of the loop, only used for printing to stdout.
        logger: Optional logger on which to log errors and warnings. Note that a stap may log more than one message.
        check_tty: If true, will only print real time if output is a tty, otherwise always prints.
        limit: Limit the count of objects to created (ignoring the rest).
        step_name: A callable returning the name of the item in logging.
        unmanaged: If true, warnings and exceptions will be raised natively instead of being catched.

    Returns:
        StepLogs: _description_
    """

    def inner(function: Callable):
        steplogs = StepLogs()

        loop_name = function.__name__ if name is None else name
        max_val = len(values) if hasattr(values, "__len__") else None

        lw = LineWriter(enabled=not check_tty or sys.stdout.isatty())
        timer = Timer()

        lw.writeln(SEPARATOR_BOLD)
        lw.writeln(f"Starting loop `{loop_name}`...")
        lw.writeln(SEPARATOR_BOLD)

        i = 0
        for i, value in enumerate(values, start=0):
            lw.provln(
                f"{loop_name} [{progress(i, max_val)}][{i+1}/{max_val or '?'}][{timer}][{steplogs.summary()}]"
            )

            output = None
            exception = None

            if limit is not None and i >= limit:
                break

            skipped = False
            with warnings.catch_warnings(record=True) as warns:
                try:
                    output = function(value)
                except Exception as e:
                    if unmanaged:
                        raise e
                    exception = e
                else:
                    if output is SKIP:
                        skipped = True
            if unmanaged:
                for warn in warns:
                    warnings._showwarnmsg(warn)

            steplog = StepLog(
                name=step_name(value) if step_name else f"step_{i+1}",
                exception=exception,
                warns=warns,
                output=output,
                skipped=skipped,
            )
            if logger:
                steplog.emit(logger)

            if steplog.warns or steplog.exception:
                lw.writeln(steplog.name)
                if steplog.warns:
                    for w in steplog.warns:
                        lw.writeln(f"    WARN:  {w.message}")
                if steplog.exception:
                    lw.writeln(f"    ERROR: {steplog.exception}")
                lw.writeln(SEPARATOR)

            steplogs.append(steplog)
        lw.writeln(
            f"Finished `{loop_name}` [{i+1} steps][in {timer}][{steplogs.summary()}]"
        )

        return steplogs

    return inner
