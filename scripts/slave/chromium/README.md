# Directory contents

Ideally, the files in this directory will be moved under the `recipes` or
`recipe_modules` directories in the `scripts/slave` directory as resources.

The files are currently being used in the following locations:

* `__init__.py` - needed for modules to import modules from this directory
* `archive_build.py` - called from [chromium/api.py][1]
  * `archive_build_unittest.py` - unittest
* `archive_layout_test_results.py` - called from [chromium\_tests/steps.py][2]
* `archive_layout_test_results_summary.py` - called from [test\_utils/api.py][3]

[1]: /scripts/slave/recipe_modules/chromium/api.py
[2]: /scripts/slave/recipe_modules/chromium_tests/api.py
[3]: /scripts/slave/recipe_modules/test_utils/api.py
