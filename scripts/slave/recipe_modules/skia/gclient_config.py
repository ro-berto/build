from common.skia import global_constants
from RECIPE_MODULES.gclient import CONFIG_CTX


@CONFIG_CTX()
def skia(c):
  soln = c.solutions.add()
  soln.name = 'skia'
  soln.url = global_constants.SKIA_REPO
  c.got_revision_mapping['skia'] = 'got_revision'
  c.target_os = ['android', 'chromeos']
