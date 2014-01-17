
from slave import recipe_test_api

class ChromiumAndroidTestApi(recipe_test_api.RecipeTestApi):
  def envsetup(self):
    return self.m.json.output({
        'PATH': './',
        'GYP_DEFINES': 'my_new_gyp_def=aaa',
        'GYP_SOMETHING': 'gyp_something_value',
    })
