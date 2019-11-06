## Recipes

If you're here to make a change to 'recipes' (the code located in
`scripts/slave/recipes*`), please take a look at the
[README](./scripts/slave/README.md) for more information pertaining to recipes.

### Style

The preferred style is PEP8 with two-space indent; that is, the [Chromium
Python
style](https://chromium.googlesource.com/chromium/src/+/master/styleguide/python/python.md).
Functions use `lowercase_with_underscores`, with the exception of the special
functions `RunSteps` and `RunTests` in recipes. Use yapf (`git cl format`) to
autoformat new code.
