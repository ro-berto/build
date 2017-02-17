DEPS = [
    'recipe_engine/json',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]

from recipe_engine.recipe_api import Property

PROPERTIES = {
    'buildername': Property(default=None),
    'buildnumber': Property(default=None),
}


# TODO(phajdan.jr): provide coverage (http://crbug.com/693058).
DISABLE_STRICT_COVERAGE = True
