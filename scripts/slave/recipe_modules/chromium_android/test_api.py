
from slave import recipe_test_api

class ChromiumAndroidTestApi(recipe_test_api.RecipeTestApi):
  def envsetup(self):
    return self.m.json.output({
        'PATH': './',
        'GYP_DEFINES': 'my_new_gyp_def=aaa',
        'GYP_SOMETHING': 'gyp_something_value',
    })

  def default_step_data(self, api):
    return (
        api.step_data(
            'get_internal_names',
            api.json.output({
                'BUILD_BUCKET': 'build-bucket',
                'SCREENSHOT_BUCKET': 'screenshot-archive',
                'INSTRUMENTATION_TEST_DATA': 'a:b/test/data/android/device_files',
                'FLAKINESS_DASHBOARD_SERVER': 'test-results.appspot.com',
            })) +
        api.step_data(
            'get app_manifest_vars',
            api.json.output({
                'version_code': 10,
                'version_name': 'some_builder_1234',
                'build_id': 3333,
                'date_string': 6001,
            }))
    )
