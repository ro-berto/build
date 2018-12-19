# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class ChromiumCheckoutApi(recipe_api.RecipeApi):
  def __init__(self, *args, **kwargs):
    super(ChromiumCheckoutApi, self).__init__(*args, **kwargs)
    # Keep track of working directory (which contains the checkout).
    # None means "default value".
    self._working_dir = None

  @property
  def working_dir(self):
    """Returns parent directory of the checkout.

    Requires |ensure_checkout| to be called first.
    """
    # TODO(phajdan.jr): assert ensure_checkout has been called.
    return self._working_dir

  def get_checkout_dir(self, bot_config):
    """Returns directory where checkout can be created.

    TODO: Cache this result for a given "bot_config.checkout_dir" value so we
    don't have to "makedirs" each time the checkout dir is queried.
    """
    if self.m.runtime.is_luci:
      # On LUCI, Buildbucket by default maps a per-builder unique directory in
      # as the 'builder' cache. Builders that are intended to share a cache
      # should have a CacheEntry config like:
      #
      #   caches {
      #     path: "builder"
      #     name: "some common name shared by different builders"
      #   }
      #
      # Which will mount that named cache to exactly the same folder.
      #
      # It's important to maintain the same mounted location because file paths
      # can end up in cached goma keys/objects; mounting the named cache to an
      # alternate location could result in goma cache bloating.
      return self.m.path['cache'].join('builder')

    # If explicitly specified, use the named builder cache base directory.
    try:
      builder_cache = self.m.path['builder_cache']
    except KeyError:
      # No explicit builder cache directory defined. Use the "start_dir"
      # directory.
      return self.m.path['start_dir']

    checkout_name = ''.join(
        c if c.isalnum() else '_' for c in self.m.buildbucket.builder_name)
    checkout_dir = builder_cache.join(
        bot_config.get('checkout_dir', checkout_name))
    self.m.file.ensure_directory('makedirs checkout path', checkout_dir)
    return checkout_dir

  def get_files_affected_by_patch(self, relative_to='src/', cwd=None):
    """Returns list of POSIX paths of files affected by patch for "analyze".

    Paths are relative to `relative_to` which for analyze should be 'src/'.
    """
    if not self.m.tryserver.gerrit_change:
      # There is no patch to begin with.
      return []
    patch_root = self.m.gclient.get_gerrit_patch_root()
    assert patch_root, (
        'local path is not configured for %s' %
            self.m.tryserver.gerrit_change_repo_url)
    if not cwd and self.working_dir:
      cwd = self.working_dir.join(patch_root)
    with self.m.context(cwd=cwd):
      files = self.m.tryserver.get_files_affected_by_patch(patch_root)
    for i, path in enumerate(files):
      path = str(path)
      assert path.startswith(relative_to), (path, relative_to)
      files[i] = path[len(relative_to):]
    return files

  def ensure_checkout(self, bot_config, **kwargs):
    """Wrapper for bot_update.ensure_checkout with chromium-specific additions.
    """
    if self.m.platform.is_win:
      self.m.chromium.taskkill()

    self._working_dir = self.get_checkout_dir(bot_config)

    # Bot Update re-uses the gclient configs.
    with self.m.context(cwd=self._working_dir):
      update_step = self.m.bot_update.ensure_checkout(
          patch_root=bot_config.get('patch_root'),
          clobber=bot_config.get('clobber', False),
          **kwargs)

    assert update_step.json.output['did_run']
    # HACK(dnj): Remove after 'crbug.com/398105' has landed
    self.m.chromium.set_build_properties(update_step.json.output['properties'])

    return update_step
