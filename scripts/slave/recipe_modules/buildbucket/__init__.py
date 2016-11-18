DEPS = [
    'recipe_engine/json',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
]

from recipe_engine.recipe_api import Property

PROPERTIES = {
    'buildername': Property(default=None),
    'buildnumber': Property(default=None),
}
