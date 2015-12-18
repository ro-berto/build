from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import Single
from recipe_engine.config_types import Path

def BaseConfig(**_kwargs):
  return ConfigGroup(
    install_emulator_deps_path = Single(Path),
    avd_script_path = Single(Path),
  )

config_ctx = config_item_context(BaseConfig)

@config_ctx()
def base_config(c):
  c.install_emulator_deps_path = Path('[CHECKOUT]', 'build', 'android',
                                      'install_emulator_deps.py')
  c.avd_script_path = Path('[CHECKOUT]', 'build', 'android', 'avd.py')
