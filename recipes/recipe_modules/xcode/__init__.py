from PB.recipe_modules.build.xcode import properties

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/json',
    'recipe_engine/properties',
]

PROPERTIES = properties.InputProperties