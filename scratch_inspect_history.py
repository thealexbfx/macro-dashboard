from datetime import date
from pprint import pprint

from macro_engine.pipelines.history import run_usa_environment_history

history = run_usa_environment_history(
    start_date=date(2021, 1, 1),
    end_date=date.today(),
)

print(type(history))
print()

print(history)

print()

print("Attributes:")
print(history.__dict__.keys())

print()

print("History object:")
print(type(history.history))

print()

print(history.history)

print()

if history.history is not None:
    print(history.history.__dict__.keys())