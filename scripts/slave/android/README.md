# Directory contents

Ideally, the files in this directory will be moved under the `recipes` or
`recipe_modules` directories in the `scripts/slave` directory as resources.

The files are currently being used in the following locations:

* `__init__.py` - needed for modules to import modules from this directory
* `archive_build.py` - called from [chromium\_android/api.py][1]
  * `archive_build_unittest.py` - unittest

[1]: /scripts/slave/recipe_modules/chromium_android/api.py
