
from recipe_engine.config import config_item_context, ConfigGroup, Single

def BaseConfig(**_kwargs):
  return ConfigGroup(
      test_results_server = Single(basestring))


config_ctx = config_item_context(BaseConfig)


@config_ctx(is_root=True)
def BASE(c):
  pass

@config_ctx()
def public_server(c):
  c.test_results_server = 'test-results.appspot.com'

