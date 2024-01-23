import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, List, Optional


class LoopLog:
    """A helper to log processing done in a loop, catching errors and warnings to produce a nice report.

    ```python
    loop_log = LoopLog("doing something")
    for item in items:
        with loop_log.step(name=item.name):
            # do something, incl. throwing exceptions or raising warnings
            ...
    # print out a summary showing the number of success/warnings/errors
    loop_log.report()
    ```
    """

    @dataclass
    class StepLog:
        name: str
        exception: Exception
        warns: List
        output: Any

        @property
        def is_success(self):
            return not self.warns and not self.exception

        @property
        def is_warning(self):
            return self.warns and not self.exception

        @property
        def is_error(self):
            return self.exception

    def __init__(self, name: str, limit: Optional[int] = None):
        print(f"Starting {name}...")
        self.logs: List[LoopLog.StepLog] = []
        self.limit = limit

    @property
    def successes(self):
        return (l for l in self.logs if l.is_success)

    @property
    def warns(self):
        return (l for l in self.logs if l.is_warning)

    @property
    def errors(self):
        return (l for l in self.logs if l.is_error)

    @property
    def count(self):
        return len(self.logs)

    @contextmanager
    def step(self, name=None):
        if name is None:
            name = f"step_{len(self.logs)}"

        output = None
        exception = None
        with warnings.catch_warnings(record=True) as warns:
            try:
                yield
            except Exception as e:
                exception = e

        log = LoopLog.StepLog(
            name=name, exception=exception, warns=warns, output=output
        )
        if log.is_success:
            print(".", end="")
        elif log.is_warning:
            print("?", end="")
        else:
            print("!", end="")
        self.logs.append(log)

    def report(self):
        print("")
        for l in self.errors:
            print("=" * 80)
            print(f"{l.name} errored: {l.exception}")
        for l in self.warns:
            print("=" * 80)
            print(f"{l.name} raised {len(l.warns)} warnings:")
            for w in l.warns:
                print(f"  {w.__class__.__name__}: {w.message}")

        print("=" * 80)
        count_ok = sum(1 for _ in self.successes)
        count_warn = sum(1 for _ in self.warns)
        count_ko = sum(1 for _ in self.errors)
        print("Done 🌍 !")
        print(f"{count_ok} ok / {count_warn} warn / {count_ko} err")
