# Looplog

Looplog is helper to log processing done in a loop, catching errors and warnings to produce a nice report.

```python
loop_log = LoopLog("doing something")
for item in items:
    with loop_log.step(name=item.name):
        # do something, incl. throwing exceptions or raising warnings
        ...
# print out a summary showing the number of success/warnings/errors
loop_log.report()
```

## Contribute

```bash
# install pre-commit
pip install pre-commit
pre-commit install

# run tests
python -m tests
```
