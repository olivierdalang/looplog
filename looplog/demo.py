import logging
import random
import sys
import time
import warnings

from looplog import SKIP, looplog

logger = logging.getLogger("")


def demo():
    old_grades = [12, 14, 7, 11.25, "19", 0, 22.25, 0, 13, None, 15, 12]

    @looplog(old_grades, step_name=lambda g: f"validating {repr(g)}")
    def validate_grade(old_grade):
        if old_grade is None:
            return SKIP

        # debug messages are shown if there are warnings
        print(f"Computing grade `{old_grade}`")

        # simulate some processing time
        time.sleep(random.uniform(0, 0.1))

        # raise warnings if needed
        if isinstance(old_grade, float) and not old_grade.is_integer():
            warnings.warn("Input will be rounded !")
            old_grade = round(old_grade)

        # raise exceptions if needed
        if old_grade > 20 or old_grade < 0:
            raise ValueError("Input out of range !")

        try:
            10 / old_grade
        except ZeroDivisionError as e:
            if sys.version_info >= (3, 11):
                e.add_note("this was done on purpose")
            raise e

    time.sleep(0.5)
    input("\n\nPress enter to show summary...")
    print(validate_grade.summary())

    time.sleep(0.5)
    input("\n\nPress enter to show report...")
    print(validate_grade.report())

    time.sleep(0.5)
    input("\n\nPress enter to show details...")
    print(validate_grade.details())


if __name__ == "__main__":
    demo()
