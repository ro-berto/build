DEPS = [
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'commit_position',
  'file',
  'goma',
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
