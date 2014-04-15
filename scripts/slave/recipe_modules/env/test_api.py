import os
from slave import recipe_test_api

class EnvTestApi(recipe_test_api.RecipeTestApi):
  @recipe_test_api.mod_test_data
  @staticmethod
  def test_environ(retval):
    return retval

  def __call__(self, **kwargs):
    self._test_environ = kwargs
    return self.test_environ(self._test_environ)
