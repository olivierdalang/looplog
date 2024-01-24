import logging
import sys
import warnings
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Iterable, List, Optional

SKIP = object()


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

    def details(self) -> str:
        lines = []
        for log in self._list:
            if not log.exception and not log.warns:
                continue
            lines.append("=" * 80)
            if log.exception:
                lines.append(f"ERROR {log.name}: {log.exception}")
            if log.warns:
                for w in log.warns:
                    lines.append(f"WARNING {log.name}: {w.message}")
        lines.append("=" * 80)
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


def looplog(
    values: Iterable[Any],
    name: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
    stdout=None,
    limit: Optional[int] = None,
    step_name_callable: Optional[Callable[[int, Any], str]] = None,
    unmanaged=False,
) -> StepLogs:
    """Decorator running the given function against each value of the provided iterable values, logging warnings and exceptions for each one. This returns a StepLogs object.

    Args:
        values (_type_): List of items to iterate on
        name (Optional[str], optional): The name of the loop, only used for printing to stdout. Defaults to None.
        logger (Optional[logging.Logger], optional): Optional logger on which to log errors and warnings. Note that a stap may log more than one message. Defaults to None.
        stdout (_type_, optional): Where to print stdout for live output. Defaults to sys.stdout.
        limit (Optional[int], optional): Limit the count of objects to created (ignoring the rest). Defaults to None.
        step_name_callable (Optional[Callable[[int, Any], str]], optional): A callable returnin the name of the item in logging. Defaults to None.
        unmanaged (bool, optional): If true, warnings and exceptions will be raised natively instead of being catched. Defaults to False.

    Returns:
        StepLogs: _description_
    """

    if stdout is None:
        stdout = sys.stdout

    def inner(function):
        steplogs = StepLogs()

        stdout.write(f"Starting loop `{name or function.__name__}`\n")
        for i, value in enumerate(values, start=1):
            if step_name_callable:
                step_name = step_name_callable(i, value)
            else:
                step_name = f"step_{i}"
            output = None
            exception = None

            if limit and i > limit:
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
                name=step_name,
                exception=exception,
                warns=warns,
                output=output,
                skipped=skipped,
            )
            if logger:
                steplog.emit(logger)
            stdout.write(steplog.type.value)
            stdout.flush()
            steplogs.append(steplog)
        stdout.write("\n")

        return steplogs

    return inner
