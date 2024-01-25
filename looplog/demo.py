import random
import time
import warnings

from looplog import SKIP, looplog


def demo():
    old_grades = [12, 14, 7, 11, "19", 11.25, 22, 0, 13, None, 15, 12]
    new_grades = []

    @looplog(old_grades)
    def convert_grades(old_grade):
        if old_grade is None:
            return SKIP
        # simulate some processing time
        time.sleep(random.uniform(0, 1))

        # raise warnings if needed
        if isinstance(old_grade, float) and not old_grade.is_integer():
            warnings.warn("Input will be rounded !")
            old_grade = round(old_grade)

        # raise warnings if needed
        if old_grade > 20 or old_grade < 0:
            warnings.warn("Input out of range !")

        # do something...
        new_grades.append(old_grade / 20 * 10)


if __name__ == "__main__":
    demo()
