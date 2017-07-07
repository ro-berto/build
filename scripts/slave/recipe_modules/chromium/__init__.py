DEPS = [
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  # in order to have set_config automatically populate gclient
  'depot_tools/gclient',
  'depot_tools/git',
  'depot_tools/tryserver',

  'adb',
  'build',
  'commit_position',
  'goma',

  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
]
