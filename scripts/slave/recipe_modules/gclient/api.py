# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

GIT_DEFAULT_WHITELIST = frozenset((
  'tools_build',
))

def jsonish_to_python(spec, is_top=False):
  ret = ''
  if is_top:  # We're the 'top' level, so treat this dict as a suite.
    ret = '\n'.join(
      '%s = %s' % (k, jsonish_to_python(spec[k])) for k in sorted(spec)
    )
  else:
    if isinstance(spec, dict):
      ret += '{'
      ret += ', '.join(
        "%s: %s" % (repr(k), jsonish_to_python(spec[k])) for k in sorted(spec))
      ret += '}'
    elif isinstance(spec, list):
      ret += '['
      ret += ', '.join(jsonish_to_python(x) for x in spec)
      ret += ']'
    else:
      ret = repr(spec)
  return ret


class GclientApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(GclientApi, self).__init__(**kwargs)
    self.USE_MIRROR = None

  @property
  def use_mirror(self):
    """Indicates if gclient will use mirrors in its configuration."""
    if self.USE_MIRROR is None:
      self.USE_MIRROR = self.m.properties.get('use_mirror', True)
    return self.USE_MIRROR

  @use_mirror.setter
  def use_mirror(self, val):  # pragma: no cover
    self.USE_MIRROR = val

  def get_config_defaults(self, config_name):
    ret = {
      'USE_MIRROR': self.use_mirror
    }
    if config_name in GIT_DEFAULT_WHITELIST:
      ret['GIT_MODE'] = True
    return ret

  def checkout(self, gclient_config=None, spec_name=None):
    """Return a step generator function for gclient checkouts."""
    cfg = gclient_config or self.c
    assert cfg.complete()

    if not spec_name:
      step_name = lambda n: 'gclient ' + n
    else:
      step_name = lambda n: '[spec: %s] gclient %s' % (spec_name, n)

    spec_string = jsonish_to_python(cfg.as_jsonish(), True)
    gclient = lambda name, *args: self.m.python(
        name, self.m.path.depot_tools('gclient.py'), args)

    revisions = []
    for s in cfg.solutions:
      if s.revision is not None:
        revisions.extend(['--revision', '%s@%s' % (s.name, s.revision)])

    if not cfg.GIT_MODE:
      clean_step = self.revert(step_name)
      sync_step = gclient(
          step_name('sync'), 'sync', '--nohooks', *revisions)
    else:
      # clean() isn't used because the gclient sync flags passed in checkout()
      # do much the same thing, and they're more correct than doing a separate
      # 'gclient revert' because it makes sure the other args are correct when
      # a repo was deleted and needs to be re-cloned (notably
      # --with_branch_heads), whereas 'revert' uses default args for clone
      # operations.
      #
      # TODO(mmoss): To be like current official builders, this step could just
      # delete the whole <slave_name>/build/ directory and start each build
      # from scratch. That might be the least bad solution, at least until we
      # have a reliable gclient method to produce a pristine working dir for
      # git-based builds (e.g. maybe some combination of 'git reset/clean -fx'
      # and removing the 'out' directory).
      clean_step = None
      sync_step = gclient(step_name('sync'),
        'sync', '--verbose', '--with_branch_heads', '--nohooks',
        '--reset', '--delete_unversioned_trees', '--force', *revisions)

    steps = [
      gclient(step_name('setup'), 'config', '--spec', spec_string)
    ]
    if clean_step:
      steps.append(clean_step)
    if sync_step:
      steps.append(sync_step)

    self.m.path.set_checkout(self.m.path.slave_build(cfg.solutions[0].name))

    return steps

  def revert(self, step_name_fn=lambda x: 'gclient '+x):
    """Return a gclient_safe_revert step."""
    return self.m.python(
      step_name_fn('revert'),
      self.m.path.build('scripts', 'slave', 'gclient_safe_revert.py'),
      ['.', self.m.path.depot_tools('gclient', wrapper=True)],
    )
