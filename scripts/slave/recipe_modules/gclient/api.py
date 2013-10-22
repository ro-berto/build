# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

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
        "%s: %s" % (repr(str(k)), jsonish_to_python(spec[k]))
        for k in sorted(spec)
      )
      ret += '}'
    elif isinstance(spec, list):
      ret += '['
      ret += ', '.join(jsonish_to_python(x) for x in spec)
      ret += ']'
    elif isinstance(spec, basestring):
      ret = repr(str(spec))
    else:
      ret = repr(spec)
  return ret

class GclientApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(GclientApi, self).__init__(**kwargs)
    self.USE_MIRROR = None
    self._spec_alias = None

  def __call__(self, name, cmd, **kwargs):
    """Wrapper for easy calling of gclient steps."""
    assert isinstance(cmd, (list, tuple))
    prefix = 'gclient '
    if self.spec_alias:
      prefix = ('[spec: %s] ' % self.spec_alias) + prefix

    return self.m.python(
        prefix + name, self.m.path.depot_tools('gclient.py'), cmd, **kwargs)

  @property
  def use_mirror(self):
    """Indicates if gclient will use mirrors in its configuration."""
    if self.USE_MIRROR is None:
      self.USE_MIRROR = self.m.properties.get('use_mirror', True)
    return self.USE_MIRROR

  @use_mirror.setter
  def use_mirror(self, val):  # pragma: no cover
    self.USE_MIRROR = val

  @property
  def spec_alias(self):
    """Optional name for the current spec for step naming."""
    return self._spec_alias

  @spec_alias.setter
  def spec_alias(self, name):
    self._spec_alias = name

  @spec_alias.deleter
  def spec_alias(self):
    self._spec_alias = None

  def get_config_defaults(self):
    ret = {
      'USE_MIRROR': self.use_mirror
    }
    ret['CACHE_DIR'] = self.m.path.root('git_cache')
    return ret

  @recipe_api.inject_test_data
  def sync(self, cfg, **kwargs):
    revisions = []
    for s in cfg.solutions:
      if s.revision is not None:
        revisions.extend(['--revision', '%s@%s' % (s.name, s.revision)])

    def parse_got_revision(step_result):
      data = step_result.json.output
      for path, info in data['solutions'].iteritems():
        # gclient json paths always end with a slash
        path = path.rstrip('/')
        if path in cfg.got_revision_mapping:
          propname = cfg.got_revision_mapping[path]
          step_result.presentation.properties[propname] = info['revision']

    if not cfg.GIT_MODE:
      return self('sync', ['sync', '--nohooks'] + revisions +
                  ['--output-json', self.m.json.output()],
                  followup_fn=parse_got_revision, **kwargs)
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
      j = '-j2' if self.m.platform.is_win else '-j8'
      return self('sync',
                  ['sync', '--verbose', '--with_branch_heads', '--nohooks', j,
                   '--reset', '--delete_unversioned_trees', '--force',
                   '--upstream', '--no-nag-max'] + revisions +
                  ['--output-json', self.m.json.output()],
                  followup_fn=parse_got_revision,
                  **kwargs)


  def checkout(self, gclient_config=None, revert=True, **kwargs):
    """Return a step generator function for gclient checkouts."""
    cfg = gclient_config or self.c
    assert cfg.complete()

    spec_string = jsonish_to_python(cfg.as_jsonish(), True)

    steps = [
      self('setup', ['config', '--spec', spec_string], **kwargs)
    ]

    if not cfg.GIT_MODE:
      if revert:
        steps.append(self.revert(**kwargs))
      steps.append(self.sync(cfg, **kwargs))
    else:
      steps.append(self.sync(cfg, **kwargs))

      cfg_cmds = [
        ('user.name', 'local_bot'),
        ('user.email', 'local_bot@example.com'),
      ]
      for var, val in cfg_cmds:
        name = 'recurse (git config %s)' % var
        steps.append(self(name, ['recurse', 'git', 'config', var, val],
                          **kwargs))

    cwd = kwargs.get('cwd', self.m.path.slave_build)
    self.m.path.set_dynamic_path(
      'checkout', cwd(*cfg.solutions[0].name.split(self.m.path.sep)),
      overwrite=False)

    return steps

  def revert(self, **kwargs):
    """Return a gclient_safe_revert step."""
    # Not directly calling gclient, so don't use self().
    prefix = 'gclient '
    if self.spec_alias:
      prefix = ('[spec: %s] ' % self.spec_alias) + prefix

    return self.m.python(prefix + 'revert',
        self.m.path.build('scripts', 'slave', 'gclient_safe_revert.py'),
        ['.', self.m.path.depot_tools('gclient', platform_ext={'win': '.bat'})],
        **kwargs
    )

  def runhooks(self, args=None, **kwargs):
    """Return a 'gclient runhooks' step."""
    args = args or []
    assert isinstance(args, (list, tuple))
    return self('runhooks', ['runhooks'] + list(args), **kwargs)

  @property
  def is_blink_mode(self):
    """ Indicates wether the caller is to use the Blink config rather than the
    Chromium config. This may happen for one of two reasons:
    1. The builder is configured to always use TOT Blink. (factory property
       top_of_tree_blink=True)
    2. A try job comes in that applies to the Blink tree. (root is
       src/third_party/WebKit)
    """
    if self.m.properties.get('top_of_tree_blink'):
      return True

    # Normalize slashes to take into account possible Windows paths.
    root = self.m.properties.get('root', '').replace('\\', '/').lower()

    if root.endswith('third_party/webkit'):
      return True

    return False
