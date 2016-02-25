from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import Single, Static
from recipe_engine.config_types import Path

def BaseConfig(**_kwargs):
  return ConfigGroup(
    install_emulator_deps_path = Static(Path('[CHECKOUT]', 'build', 'android',
                                             'install_emulator_deps.py')),
    avd_script_path = Static(Path('[CHECKOUT]', 'build', 'android', 'avd.py'))
  )

config_ctx = config_item_context(BaseConfig)

@config_ctx()
def base_config(c):
  pass
