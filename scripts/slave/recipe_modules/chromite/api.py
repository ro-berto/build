# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cgi
import re

from slave import recipe_api


class ChromiteApi(recipe_api.RecipeApi):
  chromite_url = 'https://chromium.googlesource.com/chromiumos/chromite.git'
  manifest_url = 'https://chromium.googlesource.com/chromiumos/manifest.git'
  repo_url = 'https://chromium.googlesource.com/external/repo.git'
  chromite_subpath = 'chromite'

  _MANIFEST_CMD_RE = re.compile(r'Automatic:\s+Start\s+([^\s]+)\s+([^\s]+)')
  _BUILD_ID_RE = re.compile(r'CrOS-Build-Id: (.+)')

  def check_repository(self, repo_type_key, value):
    """Scans through registered repositories for a specified value.

    Args:
      repo_type_key (str): The key in the 'repositories' config to scan through.
      value (str): The value to scan for.
    Returns (bool): True if the value was found.
    """
    def remove_tail(v, tail):
      if v.endswith(tail):
        v = v[:-len(tail)]
      return v

    for v in self.c.repositories.get(repo_type_key, ()):
      if remove_tail(v, '.git') == remove_tail(value, '.git'):
        return True
    return False

  def load_try_job(self, repository, revision):
    """Loads try job arguments from the try job repository.

    Loading a tryjob descriptor works as follows:
    - Identify the tryjob commit.
    - Identify the tryjob descriptor file checked into that commit.
    - Load the tryjob descriptor file and parse as JSON.

    Args:
      repository (str): The URL of the try job change repository.
      revision (str): The try job change revision.
    Returns (iterable): The extra arguments specified by the tryjob.
    """
    # Load the job description from Gitiles.
    commit_log = self.m.gitiles.commit_log(
        repository, revision, step_name='Fetch tryjob commit')

    # Get the list of different files.
    desc_path = None
    for diff in commit_log.get('tree_diff', ()):
      if diff.get('type') == 'add':
        desc_path = diff.get('new_path')
        if desc_path:
          break
    else:
      raise self.m.step.StepFailure('Could not find tryjob description.')

    # Load the tryjob description file.
    desc_json = self.m.gitiles.download_file(
        repository, desc_path, branch=revision,
        step_name=str('Fetch tryjob descriptor (%s)' % (desc_path,)))
    result = self.m.step.active_result

    # Parse the commit description from the file (JSON).
    desc = self.m.json.loads(desc_json)
    result.presentation.step_text += '<br/>'.join(
        '%s: %s' % (k, cgi.escape(str(v)))
        for k, v in desc.iteritems())
    return desc.get('extra_args', ())

  def load_manifest_config(self, repository, revision):
    """Loads manifest-specified parameters from the manifest commit.

    This method parses the commit log for the following information:
    - The branch to build (From the "Automatic": tag).
    - The build ID (from the CrOS-Build-Id: tag).

    Args:
      repository (str): The URL of the repository hosting the change.
      revision (str): The revision hash to load the build ID from.
    """
    commit_log = self.m.gitiles.commit_log(
        repository, revision, step_name='Fetch manifest config')
    result = self.m.step.active_result

    # Handle missing/invalid response.
    if not (commit_log and commit_log.get('message')):
      self.m.python.failing_step('Fetch manifest config failure',
                                 'Failed to fetch manifest config.')

    build_id = None
    loaded = []
    for line in reversed(commit_log['message'].splitlines()):
      # Automatic command?
      match = self._MANIFEST_CMD_RE.match(line)
      if match:
        self.c.chromite_revision = match.group(2)
        loaded.append('Chromite branch: %s' % (self.c.chromite_revision,))
        continue

      # Build ID?
      match = self._BUILD_ID_RE.match(line)
      if match:
        self.c.cbb.build_id = match.group(1)
        loaded.append('Build ID: %s' % (self.c.cbb.build_id,))
        continue
    if loaded:
      loaded.insert(0, '')
      result.presentation.step_text += '<br/>'.join(loaded)

  def default_chromite_path(self):
    """Returns: (Path) The default Chromite checkout path."""
    return self.m.path['slave_build'].join(self.chromite_subpath)

  def gclient_config(self):
    """Generate a 'gclient' configuration to check out Chromite.

    Return: (config) A 'gclient' recipe module configuration.
    """
    cfg = self.m.gclient.make_config()
    soln = cfg.solutions.add()
    soln.name = 'chromite'
    soln.url = self.chromite_url
    soln.revision = self.c.chromite_revision
    return cfg

  def checkout(self, manifest_url=None, repo_url=None):
    manifest_url = manifest_url or self.manifest_url
    repo_url = repo_url or self.repo_url

    self.m.repo.init(manifest_url, '--repo-url', repo_url)
    self.m.repo.sync()

  def cbuildbot(self, name, config, args=None, chromite_path=None, **kwargs):
    """Runs the cbuildbot command defined by the arguments.

    Args:
      name: (str) The name of the command step.
      config: (str) The name of the 'cbuildbot' configuration to invoke.
      args: (list) If not None, addition arguments to pass to 'cbuildbot'.
      chromite_path: (str) The path to the Chromite checkout; if None, the
          'default_chromite_path()' will be used.

    Returns: (Step) The step that was run.
    """
    chromite_path = chromite_path or self.default_chromite_path()
    args = (args or [])[:]
    args.append(config)

    cmd = [self.m.path.join(chromite_path, 'bin', 'cbuildbot')] + args

    # TODO(petermayo): Wrap this nested annotation in a stabilizing wrapper.
    return self.m.step(name, cmd, allow_subannotations=True, **kwargs)

  def cros_sdk(self, name, cmd, args=None, environ=None, chromite_path=None,
                 **kwargs):
    """Return a step to run a command inside the cros_sdk."""
    chromite_path = chromite_path or self.default_chromite_path()

    chroot_cmd = self.m.path.join(chromite_path, 'bin', 'cros_sdk')

    arg_list = (args or [])[:]
    for t in sorted((environ or {}).items()):
      arg_list.append('%s=%s' % t)
    arg_list.append('--')
    arg_list.extend(cmd)

    self.m.python(name, chroot_cmd, arg_list, **kwargs)

  def setup_board(self, board, args=None, **kwargs):
    """Run the setup_board script inside the chroot."""
    self.cros_sdk('setup board',
                  ['./setup_board', '--board', board],
                  args, **kwargs)

  def build_packages(self, board, args=None, **kwargs):
    """Run the build_packages script inside the chroot."""
    self.cros_sdk('build packages',
                  ['./build_packages', '--board', board],
                  args, **kwargs)

  def configure(self, config_map, master, variant=None):
    """Applies configurations to this recipe.

    Args:
      config_map (dict): The configuration map to use.
      master (str): The name of the master configuration.
      variant (str): If not None, the name of the master variant configs to
          apply.
    """
    config_map = config_map.get(master, {})

    # Set the master's base configuration.
    master_config = config_map.get('master_config')
    assert master_config, (
        "No 'master_config' configuration for '%s'" % (master,))
    self.set_config(master_config)

    # Apply any variant configurations.
    if variant:
      for config_name in config_map.get('variants', {}).get(variant, ()):
        self.apply_config(config_name)

  def run_cbuildbot(self, config, tryjob=False):
    """Runs a 'cbuildbot' checkout-and-build workflow.

    This workflow uses the registered configuration dictionary to make master-
    and builder-specific changes to the standard workflow.

    The specific workflow paths that are taken are also influenced by several
    build properties.

    TODO(dnj): When CrOS migrates away from BuildBot, replace property
        inferences with command-line parameters.

    This workflow:
    - Checks out the specified 'cbuildbot' repository.
    - Pulls information based on the configured change's repository/revision
      to pass to 'cbuildbot'.
    - Executes the 'cbuildbot' command.

    Args:
      config (str): The name of the 'cbuildbot' configuration target to build.
      tryjob (bool): If True, load a tryjob description from the source
          repository and augment the cbuildbot command-line with it.
    Returns: (Step) the 'cbuildbot' execution step.
    """

    # Assert correct configuration.
    assert config, 'An empty configuration was specified.'
    assert self.c.cbb.builddir, 'A build directory name must be specified.'

    # Load properties from the commit being processed. This requires both a
    # repository and revision to proceed.
    repository = self.m.properties.get('repository')
    revision = self.m.properties.get('revision')
    tryjob_args = []
    if repository and revision:
      if tryjob:
        assert self.check_repository('tryjob', repository), (
            "Refusing to query unknown tryjob repository: %s" % (repository,))
        # If we are a tryjob, add parameters specified in the description.
        tryjob_args = self.load_try_job(repository, revision)

      # Pull more information from the commit if it came from certain known
      # repositories.
      if (self.c.use_chrome_version and
          self.check_repository('chromium', repository)):
        # If our change comes from a Chromium repository, add the
        # '--chrome_version' flag.
        self.c.cbb.chrome_version = self.m.properties['revision']
      if (self.c.read_cros_manifest and
          self.check_repository('cros_manifest', repository)):
        # This change comes from a manifest repository. Load configuration
        # parameters from the manifest command.
        self.load_manifest_config(repository, revision)

    buildroot = self.m.path['root'].join('cbuild', self.c.cbb.builddir)
    cbb_args = [
        '--buildroot', buildroot,
    ]
    if not tryjob:
      cbb_args.append('--buildbot')
    if self.m.properties.get('buildnumber') is not None:
      # On a developer system, it's been noted that when the build number is
      # zero, it's passed as an empty string in the properties JSON blob.
      buildnumber = self.m.properties['buildnumber'] or 0
      cbb_args.extend(['--buildnumber', buildnumber])
    if self.c.cbb.chrome_rev:
      cbb_args.extend(['--chrome_rev', self.c.cbb.chrome_rev])
    if self.c.cbb.debug:
      cbb_args.extend(['--debug'])
    if self.c.cbb.clobber:
      cbb_args.extend(['--clobber'])
    if self.c.cbb.chrome_version:
      cbb_args.extend(['--chrome_version', self.c.cbb.chrome_version])

    # Set the build ID, if specified.
    if self.c.cbb.build_id:
      cbb_args.extend(['--master-build-id', self.c.cbb.build_id])

    # Add tryjob args, if there are any.
    cbb_args.extend(tryjob_args)

    # Checkout Chromite.
    self.m.bot_update.ensure_checkout(
        gclient_config=self.gclient_config(),
        force=True)

    # Run cbuildbot.
    return self.cbuildbot(str('cbuildbot [%s]' % (config,)),
                          config,
                          args=cbb_args,
                          chromite_path=self.m.path['checkout'],
                          cwd=self.m.path['slave_root'])
