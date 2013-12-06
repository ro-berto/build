
from slave import recipe_test_api

class GclientTestApi(recipe_test_api.RecipeTestApi):
  def sync(self, cfg, **kwargs):
    return self.output_json(cfg.got_revision_mapping.keys(), cfg.GIT_MODE)

  def output_json(self, projects, git_mode=False):
    """Deterministically synthesize json.output test data for gclient's
    --output-json option.

    Args:
      projects - a list of project paths (e.g. ['src', 'src/dependency'])
      git_mode - Return git hashes instead of svn revs.
    """
    # TODO(iannucci): Account for parent_got_revision_mapping. Right now the
    # synthesized json output from this method will always use
    # gen_revision(project), but if parent_got_revision and its ilk are
    # specified, we should use those values instead.
    return self.m.json.output({
      'solutions': dict(
        (p+'/', {'revision': self.gen_revision(p, git_mode)})
        for p in projects
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

