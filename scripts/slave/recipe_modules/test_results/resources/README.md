Tool to upload test results to test-results.appspot.com in the
correct format. Supported test input format are gtest-based json and full json
test results format. This is executed by the containing recipe\_module as a
subprocess and should be used in recipes after gtest json has been generated.

Most of this code was originally in build/scripts/slave/gtest.
json\_results\_generator.py was mostly unchanged since it already had testing.
The other files were simplified to have cleaner interfaces and not have external
module dependencies.

Example usage:

    ./upload_test_results.py
      --test-type=webkit_layout_tests --input-json=/tmp/gtest_input.json
      --master-name=chromium.webkit --build-number=2257
      --builder-name='WebKit Win7 (dbg)'
      --chrome-revision=344402
      --build-id=2345
