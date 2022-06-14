Chrome Flaky Reproducer
-----------------------

Chrome Flaky Reproducer tries to determine the minimum steps needed for reproducing flaky tests by applying known reproducing methodology.

## api.py

`FlakyReproducer.run` is the recipe entrypoint that coordinate the reproducing strategies and gether the results.

## strategy_runner.py

It's the strategy entrypoint that running on swarming bots to verify the reproducing methodology.
