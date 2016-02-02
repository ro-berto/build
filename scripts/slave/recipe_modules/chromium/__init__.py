DEPS = [
  'depot_tools/bot_update',
  'commit_position',
  'file',
  'depot_tools/gclient',  # in order to have set_config automatically populate gclient
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'depot_tools/tryserver',
]
