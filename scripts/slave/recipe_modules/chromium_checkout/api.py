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
    """
    # If explicitly specified, use the named builder cache base directory.
    try:
      builder_cache = self.m.path['builder_cache']
    except KeyError:
      # No explicit builder cache directory defined. Use the "start_dir"
      # directory.
      return self.m.path['start_dir']

    checkout_name = ''.join(
        c if c.isalnum() else '_' for c in self.m.properties['buildername'])
    checkout_dir = builder_cache.join(
        bot_config.get('checkout_dir', checkout_name))
    self.m.shutil.makedirs('checkout path', checkout_dir)
    return checkout_dir

  def get_files_affected_by_patch(self, relative_to='src/', cwd=None):
    """Returns list of POSIX paths of files affected by patch for "analyze".

    Paths are relative to `relative_to` which for analyze should be 'src/'.
    """
    patch_root = self.m.gclient.calculate_patch_root(
        self.m.properties.get('patch_project'))
    if not cwd and self.working_dir:
      cwd = self.working_dir.join(patch_root)
    context = {}
    if cwd:
      context['cwd'] = cwd
    with self.m.step.context(context):
      files = self.m.tryserver.get_files_affected_by_patch(patch_root)
    for i, path in enumerate(files):
      path = str(path)
      assert path.startswith(relative_to)
      files[i] = path[len(relative_to):]
    return files

  def ensure_checkout(self, bot_config, root_solution_revision=None):
    """Wrapper for bot_update.ensure_checkout with chromium-specific additions.
    """
    if self.m.platform.is_win:
      self.m.chromium.taskkill()

    self._working_dir = self.get_checkout_dir(bot_config)
    context = {'cwd': self._working_dir}

    # Bot Update re-uses the gclient configs.
    with self.m.step.context(context):
      update_step = self.m.bot_update.ensure_checkout(
          patch_root=bot_config.get('patch_root'),
          root_solution_revision=root_solution_revision,
          clobber=bot_config.get('clobber', False))

      # Run a non-fatal gclient validation step, allowing us to collect
      # metrics using event_mon.
      # TODO(phajdan.jr): always enable or remove (http://crbug.com/570091).
      if not update_step.json.output.get('patch_failure'):
        try:
          self.m.gclient('validate', ['validate'])
        except self.m.step.StepFailure:  # pragma: no cover
          pass
    assert update_step.json.output['did_run']
    # HACK(dnj): Remove after 'crbug.com/398105' has landed
    self.m.chromium.set_build_properties(update_step.json.output['properties'])

    return update_step
