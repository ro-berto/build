# Directory contents

Ideally, the files in this directory will be moved under the `recipes` or
`recipe_modules` directories in the `scripts/slave` directory as resources.

The files are currently being used in the following locations:

* `__init__.py` - needed for modules to import modules from this directory
* `json_results_generator.py` - used by [gtest\_slave\_utils.py][1]
  * `json_results_generator_unittest.py` - unittest
* `networktransaction.py` - used by [test\_results\_uploader.py][2]
* `test_result.py` - used by [gtest\_slave\_utils.py][1] and
  [json\_results\_generator.py][3]
* `test_results_uploader.py` - used by [json\_results\_generator.py][3]

`json_results_generator.py`, `test_result.py` and `test_results_uploader.py`
have been forked to [test\_utils resources][4].

[1]: /scripts/slave/gtest_slave_utils.py
[2]: ./test_results_uploader.py
[3]: ./json_results_generator.py
[4]: /scripts/slave/recipe_modules/test_utils/resources
