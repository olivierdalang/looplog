import logging
import random
import time
import warnings

from looplog import SKIP, looplog

logger = logging.getLogger("")


def demo():
    old_grades = [12, 14, 7, 11, "19", 11.25, 22.25, 0, 13, None, 15, 12]

    @looplog(old_grades, logger=logger)
    def convert_list(old_grade):
        if old_grade is None:
            return SKIP

        # simulate some processing time
        time.sleep(random.uniform(0, 1))

        # raise warnings if needed
        if isinstance(old_grade, float) and not old_grade.is_integer():
            warnings.warn("Input will be rounded !")
            old_grade = round(old_grade)

        # raise exceptions if needed
        if old_grade > 20 or old_grade < 0:
            raise ValueError("Input out of range !")

        # do something..

    time.sleep(2)
    input("\n\nPress enter to show summary...")
    print(convert_list.summary())

    time.sleep(2)
    input("\n\nPress enter to show details...")
    print(convert_list.details())


if __name__ == "__main__":
    logging.basicConfig(filename="example.log", encoding="utf-8", level=logging.DEBUG)
    demo()
