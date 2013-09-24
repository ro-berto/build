
from slave import recipe_test_api

class GclientTestApi(recipe_test_api.RecipeTestApi):
  def sync(self, cfg, **kwargs):
    return self.m.json.output({
      'solutions': dict(
        (k+'/', {'revision': self.gen_revision(k, cfg.GIT_MODE)})
        for k in cfg.got_revision_mapping
      )
    })

  @staticmethod
  def gen_revision(project, GIT_MODE):
    """Hash project to bogus deterministic revision values."""
    import hashlib
    h = hashlib.sha1(project)
    if GIT_MODE:
      return h.hexdigest()
    else:
      import struct
      return struct.unpack('!I', h.digest()[:4])[0] % 300000

