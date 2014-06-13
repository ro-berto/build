from slave import recipe_test_api

class AOSPTestApi(recipe_test_api.RecipeTestApi):
  def calculate_blacklist(self):
    return self.m.json.output({
      'blacklist': {
        'src/blacklist/project/1': None,
        'src/blacklist/project/2': None,
      }
    })

