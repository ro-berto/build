# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import copy
import json
import os
import re

from recipe_engine import recipe_api

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.chromium_tests import steps

TEST_NAMES_DEBUG_APP_PATTERN = re.compile(
    'imp +(?:0[xX][0-9a-fA-F]+ )?-\[(?P<testSuite>[A-Za-z_][A-Za-z0-9_]'
    '*Test[Case]*) (?P<testMethod>test[A-Za-z0-9_]*)\]')

TEST_CLASS_RELEASE_APP_PATTERN = re.compile(
    r'name +0[xX]\w+ '
    '(?P<testSuite>[A-Za-z_][A-Za-z0-9_]*Test(?:Case|))\n')
TEST_NAME_RELEASE_APP_PATTERN = re.compile(
    r'name +0[xX]\w+ (?P<testCase>test[A-Za-z0-9_]+)\n')


class iOSApi(recipe_api.RecipeApi):

  # Service account to use in swarming tasks.
  SWARMING_SERVICE_ACCOUNT = \
    'ios-isolated-tester@chops-service-accounts.iam.gserviceaccount.com'

  # Map Xcode short version to Xcode build version.
  XCODE_BUILD_VERSIONS = {
      '8.0':   '8a218a',
      '8.3.3': '8e3004b',
      '9.0':   '9a235',
      '9.2':   '9c40b',
  }
  XCODE_BUILD_VERSION_DEFAULT = '9c40b'

  XCODE_APP_PATH        = 'Xcode.app'

  def __init__(self, *args, **kwargs):
    super(iOSApi, self).__init__(*args, **kwargs)
    self.__config = None
    self._include_cache = {}
    self.compilation_targets = None
    self._checkout_dir = None
    self._swarming_service_account = self.SWARMING_SERVICE_ACCOUNT
    self._xcode_build_version = None

  @property
  def bucket(self):
    assert self.__config is not None
    return self.__config.get('bucket')

  @property
  def builder_id(self):
    return chromium.BuilderId.create_for_group(self.__config['builder_group'],
                                               self.m.buildbucket.builder_name)

  @property
  def configuration(self):
    assert self.__config is not None
    if 'is_debug=true' in self.__config['gn_args']:
      return 'Debug'
    if 'is_debug=false' in self.__config['gn_args']:
      return 'Release'
    raise self.m.step.StepFailure('Missing required gn_arg: is_debug')

  @property
  def platform(self):
    assert self.__config is not None
    if 'target_cpu="arm"' in self.__config['gn_args']:
      return 'device'
    if 'target_cpu="arm64"' in self.__config['gn_args']:
      return 'device'
    if 'target_cpu="x86"' in self.__config['gn_args']:
      return 'simulator'
    if 'target_cpu="x64"' in self.__config['gn_args']:
      return 'simulator'
    raise self.m.step.StepFailure('Missing required gn_arg: target_cpu')

  @property
  def swarming_service_account(self):
    return self._swarming_service_account

  @swarming_service_account.setter
  def swarming_service_account(self, val):
    self._swarming_service_account = val

  @property
  def use_goma(self):
    assert self.__config is not None
    return 'use_goma=true' in self.__config['gn_args']

  @property
  def xcode_build_version(self):
    if not self._xcode_build_version:
      self._xcode_build_version = self.__config.get('xcode build version')
    if not self._xcode_build_version:
      self._xcode_build_version = self._deprecate_xcode_version(
          self.__config.get('xcode version'))
    if not self._xcode_build_version:  # pragma: no cover
      raise self.m.step.StepFailure('Missing required "xcode build version"')
    return self._xcode_build_version

  def _deprecate_xcode_version(self, xcode_version, location='top level'):
    # Let the caller handle the missing "xcode version".
    if not xcode_version:  # pragma: no cover
      return None
    xcode_build_version = self.XCODE_BUILD_VERSIONS.get(
        xcode_version, self.XCODE_BUILD_VERSION_DEFAULT)
    step_result = self.m.step('"xcode version" is DEPRECATED', None)
    step_result.presentation.status = self.m.step.FAILURE
    step_result.presentation.step_text = (
        'Implicitly using "xcode build version": "%s" at %s.<br />'
        'Please update your configs.') % (
        xcode_build_version, location)
    return xcode_build_version

  def _ensure_checkout_dir(self):
    if not self._checkout_dir:
      self._checkout_dir = self.m.chromium_checkout.checkout_dir
    return self._checkout_dir

  def checkout(self, gclient_apply_config=None, **kwargs):
    """Checks out Chromium."""
    self.m.gclient.set_config('ios')

    gclient_apply_config = gclient_apply_config or []
    for config in gclient_apply_config:
      self.m.gclient.apply_config(config)

    checkout_dir = self._ensure_checkout_dir()

    # Support for legacy buildbot clobber. If the "clobber" property is
    # present at all with any value, clobber the whole checkout.
    if 'clobber' in self.m.properties:
      self.m.file.rmcontents('rmcontents checkout', checkout_dir)

    with self.m.context(cwd=kwargs.get('cwd', checkout_dir)):
      return self.m.bot_update.ensure_checkout(**kwargs)

  def parse_tests(self, tests, include_dir, start_index=0):
    """Parses the tests dict, reading necessary includes.

    Args:
      tests: A list of test dicts.
    """
    # Elements of the "tests" list are dicts. There are two types of elements,
    # determined by the presence of one of these mutually exclusive keys:
    #   "app": This says to run a particular app.
    #   "include": This says to include a common set of tests from include_dir.
    # So now we go through the "tests" list replacing any "include" keys.
    # The value of an "include" key is the name of a set of tests to include,
    # which can be found as a .json file in include_dir. Read the contents
    # lazily as needed into includes.

    # expanded_tests_list will be the list of test dicts, with
    # any "include" replaced with the tests from that include.
    expanded_tests_list = []

    # Generate a unique ID we can use to refer to each test, since the config
    # may specify to run the exact same test multiple times.
    i = start_index

    for element in tests:
      if element.get('include'):
        # This is an include dict.
        include = str(element.pop('include'))

        # Lazily read the include if we haven't already.
        if include not in self._include_cache:
          self._include_cache[include] = self.m.json.read(
            'include %s' % include,
            include_dir.join(include),
            step_test_data=lambda: self.m.json.test_api.output({
              'tests': [
                {
                  'app': 'fake included test 1',
                },
                {
                  'app': 'fake included test 2',
                },
              ],
            }),
          ).json.output

        # Now take each test dict from the include, update it with the
        # extra keys (e.g. device, OS), and append to the list of tests.
        for included_test in self._include_cache[include]['tests']:
          expanded_tests_list.append(copy.deepcopy(included_test))
          expanded_tests_list[-1].update(element)
          expanded_tests_list[-1]['id'] = str(i)
          i += 1

      else:
        # This is a test dict.
        expanded_tests_list.append(copy.deepcopy(element))
        expanded_tests_list[-1]['id'] = str(i)
        i += 1

    return expanded_tests_list

  def read_build_config(
      self,
      builder_group=None,
      build_config_base_dir=None,
      buildername=None,
  ):
    """Reads the iOS build config for this bot.

    Args:
      builder_group: Name of a builder group to read the build config from,
        or None to read from properties at run-time.
      build_config_base_dir: Directory to search for build config group and
        test include directories.
    """
    builder_group = builder_group or self.m.builder_group.for_current
    buildername = buildername or self.m.buildbucket.builder_name

    build_config_base_dir = build_config_base_dir or (
        self.m.path['checkout'].join('ios', 'build', 'bots'))
    build_config_dir = build_config_base_dir.join(builder_group)
    include_dir = build_config_base_dir.join('tests')

    self.__config = self.m.json.read(
      'read build config',
      build_config_dir.join('%s.json' % buildername),
      step_test_data=lambda: self.m.json.test_api.output(
        self._test_data['build_config']
      ),
    ).json.output

    # If this bot is triggered by another bot, then the build configuration
    # has to be read from the parent's build config. A triggered bot only
    # specifies the tests.
    parent = str(self.__config.get('triggered by', ''))

    if parent:
      parent_config = self.m.json.read(
        'read parent build config (%s)' % parent,
        build_config_dir.join('%s.json' % parent),
        step_test_data=lambda: self.m.json.test_api.output(
          self._test_data['parent_build_config'],
        ),
      ).json.output

      for key, value in parent_config.iteritems():
        # Inherit the config of the parent, except for triggered bots.
        # Otherwise this builder will infinitely trigger itself.
        if key != 'triggered bots':
          self.__config[key] = value

    # In order to simplify the code that uses the values of self.__config, here
    # we default to empty values of their respective types, so in other places
    # we can iterate over them without having to check if they are in the dict
    # at all.
    self.__config.setdefault('additional_compile_targets', [])
    self.__config.setdefault('clobber', False)
    self.__config.setdefault('compiler flags', [])
    self.__config.setdefault('device check', True)
    self.__config.setdefault('env', {})
    self.__config.setdefault('gn_args', [])
    self.__config.setdefault('tests', [])
    self.__config.setdefault('triggered bots', {})
    self.__config.setdefault('upload', [])

    self.__config['builder_group'] = builder_group

    self.__config['tests'] = self.parse_tests(
        self.__config['tests'], include_dir)
    next_index = len(self.__config['tests'])
    self.__config['triggered tests'] = {}
    for i, bot in enumerate(self.__config['triggered bots']):
      bot = str(bot)
      child_config = self.m.json.read(
        'read build config (%s)' % bot,
        build_config_dir.join('%s.json' % bot),
        step_test_data=lambda: self.m.json.test_api.output(
          self._test_data['child_build_configs'][i],
        ),
      ).json.output
      self.__config['triggered tests'][bot] = self.parse_tests(
        child_config.get('tests', []), include_dir, start_index=next_index)
      next_index += len(self.__config['triggered tests'][bot])

    cfg = self.m.chromium.make_config()

    self.m.chromium.c = cfg

    self.m.chromium.apply_config('BASE')
    self.m.chromium.apply_config('ninja')
    if self.use_goma:
      # Make sure these chromium configs are applied consistently for the
      # rest of the recipe; they are needed in order for m.chromium.compile()
      # to work correctly.
      self.m.chromium.apply_config('default_compiler')
      self.m.chromium.apply_config('goma')

      # apply_config('goma') sets the old (wrong) directory for goma in
      # chromium.c.compile_py.goma_dir, but calling ensure_goma() after
      # that fixes things, and makes sure that goma is actually
      # available as well.
      self.m.chromium.ensure_goma(
          client_type=self.__config.get('goma_client_type'))

    return copy.deepcopy(self.__config)

  def ensure_xcode(self, xcode_build_version):
    xcode_build_version = xcode_build_version.lower()

    self.m.chromium._xcode_build_version = xcode_build_version
    self.m.chromium.c.mac_toolchain.enabled = True
    self.m.chromium.c.mac_toolchain.kind = 'ios'

    self.m.chromium.ensure_mac_toolchain()

  def build(
      self,
      analyze=False,
      mb_path=None,
      suffix=None,
      use_mb=True,
  ):
    """Builds from this bot's build config.

    Args:
      analyze: Whether to use the gyp_chromium analyzer to only build affected
        targets and filter out unaffected tests.
      mb_path: Custom path to MB. Uses the default if unspecified.
      suffix: Suffix to use at the end of step names.
      use_mb: Whether or not to use mb to generate build files.
    """
    assert self.__config is not None

    suffix = ' (%s)' % suffix if suffix else ''

    env = {
      'LANDMINES_VERBOSE': '1',
    }
    self.ensure_xcode(self.xcode_build_version)
    self.m.chromium.c.env.FORCE_MAC_TOOLCHAIN = 0
    env['FORCE_MAC_TOOLCHAIN'] = ''

    env.update(self.__config['env'])

    build_sub_path = '%s-%s' % (self.configuration, {
      'simulator': 'iphonesimulator',
      'device': 'iphoneos',
    }[self.platform])
    cwd = self.m.path['checkout'].join('out', build_sub_path)

    if self.__config['clobber']:
      self.m.file.rmcontents('rmcontents out', cwd)

    with self.m.context(cwd=self.m.path['checkout'], env=env):
      self.m.gclient.runhooks(name='runhooks' + suffix)

    with self.m.chromium.guard_compile(suffix=suffix or ''):

      if use_mb:
        with self.m.context(env=env):
          self.m.chromium.mb_gen(
              self.builder_id,
              build_dir='//out/%s' % build_sub_path,
              mb_path=mb_path,
              name='generate build files (mb)' + suffix,
              use_goma=self.use_goma,
          )
      else:
        # Ensure the directory containing args.gn exists before creating
        # the file.
        self.m.file.ensure_directory(
            'ensure_directory //out/%s' % build_sub_path,
            self.m.path['checkout'].join('out', build_sub_path))

        # If mb is not being used, set goma_dir before generating build files.
        if self.use_goma:
          self.__config['gn_args'].append(
              'goma_dir="%s"' % self.m.goma.goma_dir)

        self.m.file.write_text(
            'write args.gn' + suffix,
            self.m.path['checkout'].join('out', build_sub_path, 'args.gn'),
            '%s\n' % '\n'.join(self.__config['gn_args']),
        )
        self.m.step.active_result.presentation.step_text = (
            '<br />%s' % '<br />'.join(self.__config['gn_args']))
        with self.m.context(
            cwd=self.m.path['checkout'].join('out', build_sub_path), env=env):
          self.m.step('generate build files (gn)' + suffix, [
              self.m.path['checkout'].join('buildtools', 'mac', 'gn'),
              'gen',
              '--check',
              '//out/%s' % build_sub_path,
          ])

      # The same test may be configured to run on multiple platforms.
      tests = sorted(set(test['app'] for test in self.__config['tests']))

      if self.compilation_targets is None:
        self.compilation_targets = []
        self.compilation_targets.extend(tests)
        self.compilation_targets.extend(
            self.__config['additional_compile_targets'])

        self.compilation_targets.sort()

      cmd = [str(self.m.depot_tools.ninja_path), '-C', cwd]
      cmd.extend(self.__config['compiler flags'])

      if self.use_goma:
        cmd.extend(['-j', '50'])
        self.m.goma.start()

      cmd.extend(self.compilation_targets)
      exit_status = -1
      try:
        with self.m.context(cwd=cwd, env=env):
          self.m.step('compile' + suffix, cmd)
        exit_status = 0
      except self.m.step.StepFailure as e:
        exit_status = e.retcode
        raise e
      finally:
        if self.use_goma:
          self.m.goma.stop(
              ninja_log_outdir=cwd,
              ninja_log_compiler='goma',
              ninja_log_command=cmd,
              build_exit_status=exit_status)

  def symupload(self, artifact, url):
    """Uploads the given symbols file.

    Args:
      artifact: Name of the artifact to upload. Will be found relative to the
        out directory, so must have already been compiled.
      url: URL of the symbol server to upload to.
    """
    cmd = [
        self.most_recent_app_path.join('symupload'),
        self.most_recent_app_path.join(artifact),
        url,
    ]
    self.m.step('symupload %s' % artifact, cmd)

  def upload(self, base_path=None, revision=None):
    """Uploads built artifacts as instructed by this bot's build config."""
    assert self.__config

    if not base_path:
      base_path = '%s/%s' % (
          self.m.buildbucket.builder_name,
          str(self.m.time.utcnow().strftime('%Y%m%d%H%M%S')),
      )

    for artifact in self.__config['upload']:
      name = str(artifact['artifact'])

      # Allow overriding of the base path to a provided upload_path
      upload_path = artifact.get('upload_path')

      # Support dynamic replacements for pathing with current revision
      revision_placeholder = '{%revision%}'
      if upload_path and revision_placeholder in upload_path:
        # some builders get the current revision from the bot_update call
        # so we'll let those builders pass it the revision, and default
        # to buildbucket's gitiles commit id.
        revision = revision or self.m.buildbucket.gitiles_commit.id
        upload_path = upload_path.replace(revision_placeholder, revision)

      timestamp_placeholder = '{%timestamp%}'
      if upload_path and timestamp_placeholder in upload_path:
        # timestamp is required by clusterfuzz for fetching latest
        timestamp = str(self.m.time.utcnow().strftime('%Y%m%d%H%M%S'))
        upload_path = upload_path.replace(timestamp_placeholder, timestamp)

      if artifact.get('symupload'):
        self.symupload(name, artifact['symupload'])
      else:
        self.m.gsutil.upload(
            self.most_recent_app_path.join(name),
            artifact.get('bucket', self.bucket),
            upload_path or '%s/%s' % (base_path, name),
            link_name=name,
            name='upload %s' % name,
        )

  def bootstrap_swarming(self):
    """Bootstraps Swarming."""
    self.m.chromium_swarming.show_outputs_ref_in_collect_step = False

  @staticmethod
  def get_step_name(test):
    return str('%s (%s iOS %s)' % (
        test['app'], test['device type'], test['os']))

  def _ensure_xcode_version(self, task):
    """Update task with xcode version if needed."""
    if task.get('xcode build version'):
      task['xcode build version'] = task['xcode build version'].lower()
      return
    if task.get('xcode version'):
      task['xcode build version'] = self._deprecate_xcode_version(
        task['xcode version'], location=task['step name'])
      # Keep task['xcode version'] for backwards compatibility.
      return
    # If there is build-global "xcode version", add it here for backwards
    # compatibility.
    if self.__config.get('xcode version'):
      task['xcode version'] = self.__config.get('xcode version')
    task['xcode build version'] = self.xcode_build_version

  def isolate_test(self,
                   test,
                   tmp_dir,
                   isolate_template,
                   scripts_dir,
                   test_cases=None,
                   shard_num=None):
    """Isolates a single test."""
    test_cases = test_cases or []
    step_name = self.get_step_name(test)
    test_id = test['id']
    if test_cases and shard_num is not None:
      test_id = '%s_%s' % (test_id, shard_num)
      step_name = '%s shard %s' % (step_name, shard_num)
    task = {
        'bot id': test.get('bot id'),
        'isolated.gen': None,
        'isolated hash': None,
        'pool': test.get('pool'),
        'skip': 'skip' in test,
        'step name': step_name,
        'task': None,
        'task_id': test_id,
        'test': copy.deepcopy(test),
        'tmp dir': None,
        'xcode version': test.get('xcode version'),
        'xcode build version': test.get('xcode build version', ''),
    }
    self._ensure_xcode_version(task)

    app = '%s.app' % test['app']
    host_app_path = 'NO_PATH'

    # Handling for EG2
    if 'host' in test:
      app = '%s-Runner.app' % test['app']
      host_app_path = self.m.path.join(self.most_recent_app_dir,
                                       '%s.app' % test['host'])

    app_path = self.m.path.join(self.most_recent_app_dir, app)
    restart = 'true' if test.get('restart') else 'false'
    shards = str(self.m.json.dumps(test.get('shards') or 1))
    test_args = test.get('test args') or []
    xcode_parallelization = 'true' if test.get(
        'xcode parallelization') else 'false'
    xcodebuild_device_runner = 'true' if test.get(
        'xcodebuild device runner') else 'false'
    test_cases = test_cases or []
    xctest = 'true' if test.get('xctest') else 'false'
    use_trusted_cert = 'true' if test.get('use trusted cert') else 'false'
    use_replay = test.get('replay package name')
    replay_path = steps.WPR_REPLAY_DATA_ROOT if use_replay else 'NO_PATH'
    use_wpr_tools = test.get('use trusted cert') or use_replay
    wpr_tools_path = steps.WPR_TOOLS_ROOT if use_wpr_tools else 'NO_PATH'
    xcode_build_version = task['xcode build version']

    task['isolated.gen'] = tmp_dir.join('%s.isolated.gen.json' % test_id)

    args = [
        '--config-variable',
        'app_path',
        app_path,
        '--config-variable',
        'host_app_path',
        host_app_path,
        '--config-variable',
        'restart',
        restart,
        '--config-variable',
        'shards',
        shards,
        '--config-variable',
        'test_args',
        self.m.json.dumps(test_args),
        '--config-variable',
        'xcode_parallelization',
        xcode_parallelization,
        '--config-variable',
        'xcodebuild_device_runner',
        xcodebuild_device_runner,
        '--config-variable',
        'test_cases',
        self.m.json.dumps(test_cases),
        '--config-variable',
        'xctest',
        xctest,
        '--config-variable',
        'use_trusted_cert',
        use_trusted_cert,
        '--config-variable',
        'replay_path',
        replay_path,
        '--config-variable',
        'wpr_tools_path',
        wpr_tools_path,
        '--config-variable',
        'xcode_version',
        xcode_build_version,
        '--isolate',
        isolate_template,
        '--isolated',
        tmp_dir.join('%s.isolated' % test_id),
        '--path-variable',
        'app_path',
        app_path,
    ]

    # Additional_app_path is a mandatory variable defining the path to a second
    # app which will be included in the isolate's files. This is for EG2 tests
    # which uses two apps; tests that use one app will have this variable
    # equal to app_path (effectively being a no-op).
    args.extend([
        '--path-variable',
        'additional_app_path',
        (host_app_path if host_app_path != 'NO_PATH' else app_path),
    ])

    sim_platform = test.get('device type')
    sim_os = test.get('os')
    if self.platform == 'simulator' and sim_platform and sim_os:
      args.extend([
          '--config-variable',
          'platform',
          sim_platform,
          '--config-variable',
          'version',
          sim_os,
      ])

    # relative_cwd and raw_cmd need to be passed to the Swarming invocation
    # as relative_cwd and command are deprecated properties from isolate
    # and isolated.

    # The SwarmingIosTest object sets relative_cwd and raw_cmd from this
    # task dict in the constructor and passes it to the Swarming task
    # constructor as part of pre_run.

    # Because command is deprecated from isolate/isolated, we'll need to
    # build the raw command separately and pass this to the task instead.
    # command is no longer available from the isolated file.

    # * See crbug/1069704 for the deprecation of relative_cwd and command
    # from isolate.
    # * See crbug/1144638 for the motivation to build this command.

    # According to the current usage of this code, the 'relative_cwd'
    # is always '.' (and commands always start with src/). Hardcoding
    # this value is not a good long-term idea.
    def _build_command():
      retries = str(self.__config.get('retries', 3))
      mac_toolchain_path = '%s/mac_toolchain' % steps.MAC_TOOLCHAIN_ROOT

      command_template = [
          '%s/run.py' % scripts_dir, '--app', app_path, '--host-app',
          host_app_path, '--out-dir', '${ISOLATED_OUTDIR}', '--retries',
          retries, '--shards', shards, '--xcode-build-version',
          xcode_build_version, '--mac-toolchain-cmd', mac_toolchain_path,
          '--xcode-path', self.XCODE_APP_PATH, '--wpr-tools-path',
          wpr_tools_path, '--replay-path', replay_path
      ]

      if test_cases:
        for test in test_cases:
          command_template.extend(['-t', test])
      if test_args:
        command_template.extend(
            ['--args-json',
             self.m.json.dumps({
                 'test_args': test_args,
             })])

      if self.platform == 'simulator' and sim_platform and sim_os:
        iossim = self.most_recent_iossim
        command_template.extend([
            '--iossim', iossim, '--platform', sim_platform, '--version', sim_os
        ])

      # These values have not been converted to boolean values to retain
      # existing format, so we parse it this way. This is also in favor of
      # deprecating args-json.
      if xctest == 'true':
        command_template += ['--xctest']
      if restart == 'true':
        command_template += ['--restart']
      if xcode_parallelization == 'true':
        command_template += ['--xcode-parallelization']
      if xcodebuild_device_runner == 'true':
        command_template += ['--xcodebuild-device-runner']

      return command_template

    task['relative_cwd'] = '.'
    task['raw_cmd'] = _build_command()

    isolate_gen_file_contents = self.m.json.dumps({
      'args': args,
      'dir': self._ensure_checkout_dir(),
      'version': 1,
    }, indent=2)
    try:
      self.m.file.write_text(
        'generate %s.isolated.gen.json' % test_id,
        task['isolated.gen'],
        isolate_gen_file_contents,
      )
      pres = self.m.step.active_result.presentation
      pres.logs['%s.isolated.gen.json' % test_id] = (
        isolate_gen_file_contents.splitlines())
      pres.step_text = task['step name']
    except self.m.step.StepFailure as f:
      f.result.presentation.status = self.m.step.EXCEPTION
      task['isolated.gen'] = None

    return task

  def _get_test_counts_debug_app(self, test_app, ignored_classes):
    """Gets test counts from Debug app using `otool -ov` command.

      Args:
        test_app: A path to test app.
        ignored_classes: A list of classes to be ignored.

      Returns:
        A dictionary {"test_class": number_of_test_case_methods}
    """
    # Indention patterns of both Xcode version < 11.4 and == 11.4 are mimicked
    # in test data.
    debug_app_test_output = '\n'.join([
        'Meta Class', 'name 0x1064b8438 CacheTestCase',
        'baseMethods 0x1068586d8 (struct method_list_t *)',
        'imp 0x1075e6887 -[CacheTestCase testA]', 'types 0x1064cc3e1',
        'imp 0x1075e6887 -[CacheTestCase testB]',
        'imp 0x1075e6887 -[CacheTestCase testc]',
        'name 0x1064b8438 TabUITestCase',
        'baseMethods 0x1068586d8 (struct method_list_t *)',
        'imp 0x1075e6887 -[TabUITestCase testD]', 'types 0x1064cc3e1 v16@0:8',
        '    imp    0x1075e6887 -[TabUITestCase testE]',
        '    name   0x1064b8438 KeyboardTestCase',
        '    imp    0x1075e6887 -[KeyboardTestCase testF]',
        '    name   0x1064b8438 PasswordsTestCase',
        '    imp    0x1075e6887 -[PasswordsTestCase testG]',
        '    name   0x1064b8438 ToolBarTestCase',
        '    imp    0x1075e6887 -[ToolBarTestCase testH]', 'version 0'
    ])
    cmd = ['otool', '-ov', test_app]
    step_result = self.m.step(
        'shard EarlGrey test',
        cmd,
        stdout=self.m.raw_io.output(),
        step_test_data=(
            lambda: self.m.raw_io.test_api.stream_output(debug_app_test_output)
        ))
    test_names = TEST_NAMES_DEBUG_APP_PATTERN.findall(step_result.stdout)
    test_counts = collections.Counter(
      test_class for test_class, _ in test_names
      if test_class not in ignored_classes)
    return collections.Counter(test_counts)

  def _get_test_counts_release_app(self, test_app, ignored_classes):
    """Gets test counts from Release app using `otool -ov` command.

    Args:
      test_app: A path to test app.
      ignored_classes: A list of classes to be ignored.

    Returns:
      A dictionary {"test_class": number_of_test_case_methods}
    """
    # Indention patterns of both Xcode version < 11.4 and == 11.4 are mimicked
    # in test data.
    release_app_test_output = '\n'.join([
        'Meta Class', 'name 0x1064b8438 CacheTestCase',
        'baseMethods 0x1068586d8 (struct method_list_t *)',
        'name 0x1075e6887 testA', 'types 0x1064cc3e1', 'name 0x1075e6887 testB',
        'name 0x1075e6887 testc', 'baseProtocols 0x0', 'Meta Class',
        'name 0x1064b8438 TabUITestCase',
        'baseMethods 0x1068586d8 (struct method_list_t *)',
        '    name    0x1064b8438 KeyboardTest', '    name    0x1075e6887 testD',
        '    types   0x1064cc3e1 v16@0:8', '    name    0x1075e6887 testE',
        '    name    0x1075e6887 testF', 'baseProtocols 0x0',
        '    name    0x1064b8438 ChromeTestCase',
        '    name    0x1064b8438 setUp', 'baseProtocols 0x0',
        '    name    0x1064b8438 ToolBarTestCase',
        '    name    0x1075e6887 testG', '    name    0x1075e6887 testH',
        'baseProtocols 0x0', 'version 0'
    ])
    cmd = ['otool', '-ov', test_app]
    step_result = self.m.step(
        'shard EarlGrey test',
        cmd,
        stdout=self.m.raw_io.output(),
        step_test_data=(
            lambda: self.m.raw_io.test_api.stream_output(
                release_app_test_output)
        ))
    # For Release builds `otool -ov` command generates output that is
    # different from Debug builds.
    # Parsing implemented in such a way:
    # 1. Parse test class names.
    # 2. If they are not in ignored list, parse test method names.
    # 3. Calculate test count per test class.
    test_counts = {}
    res = re.split(TEST_CLASS_RELEASE_APP_PATTERN, step_result.stdout)
    # Ignore 1st element in split since it does not have any test class data
    test_classes_output = res[1:]
    for test_class, class_output in zip(test_classes_output[0::2],
                                        test_classes_output[1::2]):
      if test_class in ignored_classes:
        continue
      names = TEST_NAME_RELEASE_APP_PATTERN.findall(class_output)
      test_counts[test_class] = test_counts.get(
          test_class, 0) + len(set(names))
    return collections.Counter(test_counts)

  def _get_test_counts(self, test_app):
    """Gets test names from test app using `otool -ov` command.

    Args:
      test_app: A path to test app.

    Returns:
      A dictionary {"test_class": number_of_test_case_methods}
    """
    # 'ChromeTestCase' and 'BaseEarlGreyTestCase' are parent classes
    # of all EarlGrey/EarlGrey2 test classes. They have no real tests.
    ignored_classes = {'BaseEarlGreyTestCase', 'ChromeTestCase'}

    # Requires to test release app output and have 100% coverage
    if 'Release' in test_app:
      return self._get_test_counts_release_app(test_app, ignored_classes)
    return self._get_test_counts_debug_app(test_app, ignored_classes)

  def isolate_earlgrey_test(self,
                            test,
                            swarming_tasks,
                            tmp_dir,
                            isolate_template,
                            scripts_dir,
                            bot=None):
    """Isolate earlgrey test into small shards"""
    if 'host' in test:
      # For EG2 test info is stored in Plugins/*.xctest/.
      test_app = '%s/%s' % (
          self.m.path.join(
              self.most_recent_app_path,
              '{0}-Runner.app/PlugIns/{0}.xctest'.format(test['app'])),
          test['app'])
    else:
      test_app = '%s/%s' % (
          self.m.path.join(self.most_recent_app_path, '%s.app' % test['app']),
          test['app'])
    # Shard tests by testSuites first.  Get the information of testMethods
    # as well in case we want to shard tests more evenly.
    test_counts = self._get_test_counts(test_app)

    # Stores list of test classes and number of all tests
    class Shard(object):

      def __init__(self):
        self.test_classes = []
        self.size = 0

    shards = [Shard() for i in range(swarming_tasks)]
    # Balances test classes between shards to have
    # approximately equal number of tests per shard.
    for test_class, number_of_test_methods in test_counts.most_common():
      min_shard = min(shards, key=lambda shard: shard.size)
      min_shard.test_classes.append(test_class)
      min_shard.size += number_of_test_methods

    sublists = [shard.test_classes for shard in shards]
    tasks = []
    bot = bot or self.m.buildbucket.builder_name
    for i, sublist in enumerate(sublists):
      tasks.append(
          self.isolate_test(
              test,
              tmp_dir,
              isolate_template,
              scripts_dir,
              test_cases=sublist,
              shard_num=i))
      tasks[-1]['buildername'] = bot
    return tasks

  def isolate(self, scripts_dir='src/ios/build/bots/scripts'):
    """Isolates the tests specified in this bot's build config."""
    assert self.__config

    tasks = []


    # crbug/1144638 - Please ensure args_json and cmd are kept in sync with
    # the template found in _build_command().
    args_json = ('{"test_args": <(test_args), "xctest": <(xctest), ' +
                 '"test_cases": <(test_cases), "restart": <(restart), ' +
                 '"xcode_parallelization": <(xcode_parallelization), ' +
                 '"xcodebuild_device_runner": <(xcodebuild_device_runner)}')

    cmd = [
        '%s/run.py' % scripts_dir, '--app', '<(app_path)', '--host-app',
        '<(host_app_path)', '--args-json', args_json, '--out-dir',
        '${ISOLATED_OUTDIR}', '--retries',
        self.__config.get('retries', '3'), '--shards', '<(shards)',
        '--xcode-build-version', '<(xcode_version)', '--mac-toolchain-cmd',
        '%s/mac_toolchain' % steps.MAC_TOOLCHAIN_ROOT, '--xcode-path',
        self.XCODE_APP_PATH, '--wpr-tools-path', '<(wpr_tools_path)',
        '--replay-path', '<(replay_path)'
    ]

    files = [
      # .apps are directories. Need the trailing slash to isolate the
      # contents of a directory.
      '<(app_path)/',
      '<(additional_app_path)/',
      '%s/' % scripts_dir,
      'src/.vpython',
    ]
    if self.__config.get('additional files'):
      files.extend(self.__config.get('additional files'))
    if self.platform == 'simulator':
      iossim = self.most_recent_iossim
      cmd.extend([
        '--iossim', iossim,
        '--platform', '<(platform)',
        '--version', '<(version)',
      ])
      files.append(iossim)
    isolate_template_contents = {
        'variables': {
            'command': cmd,
            'files': files,
        },
    }

    isolate_template = self._ensure_checkout_dir().join('template.isolate')
    self.m.file.write_text(
      'generate template.isolate',
      isolate_template,
      str(isolate_template_contents),
    )
    self.m.step.active_result.presentation.logs['template.isolate'] = (
      self.m.json.dumps(isolate_template_contents, indent=2).splitlines())

    tmp_dir = self.m.path.mkdtemp('isolate')

    bots_and_tests = [(self.m.buildbucket.builder_name, self.__config['tests'])]
    bots_and_tests.extend(self.__config['triggered tests'].items())
    # Create swarming tasks with tests per bot.
    for bot, tests in bots_and_tests:
      for test in tests:
        # Split tests to a few bots.
        # Swarming tasks is defined usually in tests/ under each app.
        if test.get('swarming tasks') and 'skip' not in test:
          tasks += self.isolate_earlgrey_test(
              test,
              test['swarming tasks'],
              tmp_dir,
              isolate_template,
              scripts_dir,
              bot=bot)
        else:
          # Add tests to a bot.
          tasks.append(
              self.isolate_test(test, tmp_dir, isolate_template, scripts_dir))
          tasks[-1]['buildername'] = bot

    targets_to_isolate = [
        t['task_id'] for t in tasks
        if t['isolated.gen'] and not t['skip']]

    if targets_to_isolate:
      step_result = self.m.isolate.isolate_tests(
          tmp_dir, targets=targets_to_isolate, verbose=True)

      for task in tasks:
        if task['task_id'] in step_result.json.output:
          task['isolated hash'] = step_result.json.output[task['task_id']]

    return tasks

  def generate_test_from_task(self, task, upload_test_results=True,
                              result_callback=None):
    """Generates a Test subclass that can run tests and parse/store results.

    Returns:
      None if no tests should be run, otherwise an instance of SwarmingIosTest.
    """
    if not task['isolated hash']: # pragma: no cover
      return None
    if task['buildername'] != self.m.buildbucket.builder_name:
      return None
    if task['skip']: # pragma: no cover
      # Create a dummy step to indicate we skipped this test.
      step_result = self.m.step('[skipped] %s' % task['step name'], [])
      step_result.presentation.step_text = (
          'This test was skipped because it was not affected.')
      return None

    if self.platform == 'device':
      if not steps.IOS_PRODUCT_TYPES.get(task['test']['device type']):
        # Create a dummy step so we can annotate it to explain what
        # went wrong.
        step_result = self.m.step('[trigger] %s' % task['step name'], [])
        step_result.presentation.status = self.m.step.EXCEPTION
        step_result.presentation.logs['supported devices'] = sorted(
            steps.IOS_PRODUCT_TYPES.keys())
        step_result.presentation.step_text = (
          'Requested unsupported device type.')
        return None

    self._ensure_xcode_version(task)
    test_spec = steps.SwarmingIosTestSpec.create(self.swarming_service_account,
                                                 self.platform, self.__config,
                                                 task, upload_test_results,
                                                 result_callback)
    return test_spec.get_test()

  def collect(self, triggered_tests):
    failures = set()
    infra_failure = False
    for test in triggered_tests:
      test.run(self.m, suffix='')

    self.m.chromium_swarming.report_stats()

    for test in triggered_tests:
      results_valid = test.has_valid_results(suffix='')
      if not results_valid:
        infra_failure = True
        failures.add(test.name)
        continue

      deterministic_failures = test.deterministic_failures(suffix='')
      if deterministic_failures:
        failures.add(test.name)

    if failures:
      exception_type = (
          self.m.step.InfraFailure if infra_failure
          else self.m.step.StepFailure)
      raise exception_type('Failed %s.' % ', '.join(sorted(failures)))

  def test_swarming(self, scripts_dir='src/ios/build/bots/scripts',
                    upload_test_results=True, retry_failed_shards=False):
    """Runs tests on Swarming as instructed by this bot's build config."""
    assert self.__config

    with self.m.context(cwd=self.m.path['checkout']):
      with self.m.step.nest('bootstrap swarming'):
        self.bootstrap_swarming()

      with self.m.step.nest('isolate'):
        tasks = self.isolate(scripts_dir=scripts_dir)
        if self.__config['triggered bots']:
          self.m.file.write_text(
              'generate isolated_tasks.json',
              self._ensure_checkout_dir().join('isolated_tasks.json'),
              self.m.json.dumps(tasks),
          )

      tests = []
      with self.m.step.nest('trigger'):
        for task in tasks:
          test = self.generate_test_from_task(task, upload_test_results)
          if test:
            tests.append(test)

      invalid_test_suites, failing_test_suites = (
          self.m.test_utils.run_tests_with_patch(
              self.m, tests, retry_failed_shards=retry_failed_shards))
      all_failures = invalid_test_suites + failing_test_suites
      if all_failures:
        exception_type = (
            self.m.step.InfraFailure if invalid_test_suites
            else self.m.step.StepFailure)
        failing_step_names = [x.name for x in all_failures]
        raise exception_type('Failed %s.' % ', '.join(
            sorted(failing_step_names)))

  @property
  def most_recent_app_path(self):
    """Returns the Path to the directory of the most recently compiled apps."""
    platform = {
      'device': 'iphoneos',
      'simulator': 'iphonesimulator',
    }[self.platform]

    return self.m.path['checkout'].join(
      'out',
      '%s-%s' % (self.configuration, platform),
    )

  @property
  def most_recent_app_dir(self):
    """Returns the path (relative to checkout working dir) of the most recently
    compiled apps."""
    platform = {
      'device': 'iphoneos',
      'simulator': 'iphonesimulator',
    }[self.platform]

    return self.m.path.join(
      'src',
      'out',
      '%s-%s' % (self.configuration, platform),
    )

  @property
  def most_recent_iossim(self):
    """Returns the path to the most recently compiled iossim."""
    return self.m.path.join(self.most_recent_app_dir, 'iossim')
