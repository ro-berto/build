# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy

from recipe_engine import recipe_api


class iOSApi(recipe_api.RecipeApi):

  # Mapping of common names of supported iOS devices to product types
  # exposed by the Swarming server.
  PRODUCT_TYPES = {
    'iPad 4 GSM CDMA': 'iPad3,6',
    'iPad 5th Gen':    'iPad6,11',
    'iPad Air':        'iPad4,1',
    'iPad Air 2':      'iPad5,3',
    'iPhone 5':        'iPhone5,1',
    'iPhone 5s':       'iPhone6,1',
    'iPhone 6s':       'iPhone8,1',
    'iPhone 7':        'iPhone9,1',
  }

  def __init__(self, *args, **kwargs):
    super(iOSApi, self).__init__(*args, **kwargs)
    self.__config = None
    self._include_cache = {}
    self.compilation_targets = None
    self._checkout_dir = None

  @property
  def bucket(self):
    assert self.__config is not None
    return self.__config.get('bucket')

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
  def use_goma(self):
    assert self.__config is not None
    return 'use_goma=true' in self.__config['gn_args']

  def _ensure_checkout_dir(self):
    if not self._checkout_dir:
      self._checkout_dir = self.m.chromium_checkout.get_checkout_dir({})
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
    master_name=None,
    build_config_base_dir=None,
    buildername=None,
  ):
    """Reads the iOS build config for this bot.

    Args:
      master_name: Name of a master to read the build config from, or None
        to read from buildbot properties at run-time.
      build_config_base_dir: Directory to search for build config master and
        test include directories.
    """
    buildername = buildername or self.m.properties['buildername']
    master_name = master_name or self.m.properties['mastername']
    build_config_base_dir = build_config_base_dir or (
        self.m.path['checkout'].join('ios', 'build', 'bots'))
    build_config_dir = build_config_base_dir.join(master_name)
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
    self.__config.setdefault('env', {})
    self.__config.setdefault('explain', False)
    self.__config.setdefault('gn_args', [])
    self.__config.setdefault('tests', [])
    self.__config.setdefault('triggered bots', {})
    self.__config.setdefault('upload', [])

    self.__config['mastername'] = master_name

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

    if self.use_goma:
      # Make sure these chromium configs are applied consistently for the
      # rest of the recipe; they are needed in order for m.chromium.compile()
      # to work correctly.
      self.m.chromium.apply_config('ninja')
      self.m.chromium.apply_config('default_compiler')
      self.m.chromium.apply_config('goma')

      # apply_config('goma') sets the old (wrong) directory for goma in
      # chromium.c.compile_py.goma_dir, but calling ensure_goma() after
      # that fixes things, and makes sure that goma is actually
      # available as well.
      self.m.chromium.ensure_goma(canary=self.__config.get('use_goma_canary'))

    return copy.deepcopy(self.__config)

  def build(
      self,
      analyze=False,
      default_gn_args_path=None,
      mb_path=None,
      setup_gn=False,
      suffix=None,
      use_mb=True,
  ):
    """Builds from this bot's build config.

    Args:
      analyze: Whether to use the gyp_chromium analyzer to only build affected
        targets and filter out unaffected tests.
      default_gn_args_path: Path to default gn args file to import with
        setup-gn.py.
      mb_path: Custom path to MB. Uses the default if unspecified.
      setup_gn: Whether or not to call setup-gn.py.
      suffix: Suffix to use at the end of step names.
      use_mb: Whether or not to use mb to generate build files.
    """
    assert self.__config is not None

    suffix = ' (%s)' % suffix if suffix else ''

    env = {
      'LANDMINES_VERBOSE': '1',
      'FORCE_MAC_TOOLCHAIN': '1',
    }
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

    if setup_gn:
      cmd = [
        self.m.path['checkout'].join('ios', 'build', 'tools', 'setup-gn.py'),
      ]
      if default_gn_args_path:
        cmd.extend(['--import', default_gn_args_path])
      with self.m.context(env={
          'CHROMIUM_BUILDTOOLS_PATH':
          self.m.path['checkout'].join('buildtools')}):
        self.m.step('setup-gn.py', cmd)

    if use_mb:
      with self.m.context(env=env):
        self.m.chromium.run_mb(
            self.__config['mastername'],
            self.m.properties['buildername'],
            build_dir='//out/%s' % build_sub_path,
            mb_path=mb_path,
            name='generate build files (mb)' + suffix,
            use_goma=self.use_goma,
        )
    else:
      # If mb is not being used, set goma_dir before generating build files.
      if self.use_goma:
        self.__config['gn_args'].append('goma_dir="%s"' % self.m.goma.goma_dir)

      self.m.file.write_text(
        'write args.gn' + suffix,
        self.m.path['checkout'].join('out', build_sub_path, 'args.gn'),
        '%s\n' % '\n'.join(self.__config['gn_args']),
      )
      self.m.step.active_result.presentation.step_text = (
        '<br />%s' % '<br />'.join(self.__config['gn_args']))
      with self.m.context(
          cwd=self.m.path['checkout'].join('out', build_sub_path),
          env=env):
        self.m.step('generate build files (gn)' + suffix, [
          self.m.path['checkout'].join('buildtools', 'mac', 'gn'),
          'gen',
          '--check',
          '//out/%s' % build_sub_path,
        ])

    # The same test may be configured to run on multiple platforms.
    tests = sorted(set(test['app'] for test in self.__config['tests']))

    if self.compilation_targets is None:
      if analyze:
        with self.m.context(cwd=self.m.path['checkout']):
          affected_files = (
            self.m.chromium_checkout.get_files_affected_by_patch())

        test_targets, self.compilation_targets = (
          self.m.filter.analyze(
            affected_files,
            tests,
            self.__config['additional_compile_targets'],
            'trybot_analyze_config.json',
            additional_names=['chromium', 'ios'],
            mb_mastername=self.__config['mastername'],
          )
        )

        test_targets = set(test_targets)

        for test in self.__config['tests']:
          if test['app'] not in test_targets:
            test['skip'] = True

        if not self.compilation_targets:
          return
      else:
        self.compilation_targets = []
        self.compilation_targets.extend(tests)
        self.compilation_targets.extend(
          self.__config['additional_compile_targets'])

      self.compilation_targets.sort()

    cmd = ['ninja', '-C', cwd]
    cmd.extend(self.__config['compiler flags'])

    if self.use_goma:
      cmd.extend(['-j', '50'])
      self.m.goma.start()

    cmd.extend(self.compilation_targets)
    exit_status = -1
    try:
      with self.m.context(cwd=cwd, env=env):
        if self.__config['explain']:
          self.m.step('explain compile' + suffix, cmd + ['-d', 'explain', '-n'])
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
            ninja_log_exit_status=exit_status)

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

  def upload_tgz(self, artifact, bucket, path):
    """Tar gzips and uploads the given artifact to Google Storage.

    Args:
      artifact: Name of the artifact to upload. Will be found relative to the
        out directory, so must have already been compiled.
      bucket: Name of the Google Storage bucket to upload to.
      path: Path to upload the artifact to relative to the bucket.
    """
    tgz = self.m.path.basename(path)
    archive = self.m.path.mkdtemp('tgz').join(tgz)
    cwd = self.most_recent_app_path
    cmd = [
        'tar',
        '--create',
        '--directory', cwd,
        '--file', archive,
        '--gzip',
        '--verbose',
        artifact,
    ]
    with self.m.context(cwd=cwd):
      self.m.step('tar %s' % tgz, cmd)
    self.m.gsutil.upload(
        archive,
        bucket,
        path,
        link_name=tgz,
        name='upload %s' % tgz,
    )

  def upload(self, base_path=None):
    """Uploads built artifacts as instructed by this bot's build config."""
    assert self.__config

    if not base_path:
      base_path = '%s/%s' % (
          self.m.properties['buildername'],
          str(self.m.time.utcnow().strftime('%Y%m%d%H%M%S')),
      )

    for artifact in self.__config['upload']:
      name = str(artifact['artifact'])
      if artifact.get('symupload'):
        self.symupload(name, artifact['symupload'])
      elif artifact.get('compress'):
        with self.m.step.nest('upload %s' % name):
          self.upload_tgz(
              name,
              artifact.get('bucket', self.bucket),
              '%s/%s' % (base_path, '%s.tar.gz' % (name.split('.', 1)[0])),
          )
      else:
        self.m.gsutil.upload(
            self.most_recent_app_path.join(name),
            artifact.get('bucket', self.bucket),
            '%s/%s' % (base_path, name),
            link_name=name,
            name='upload %s' % name,
        )

  def bootstrap_swarming(self):
    """Bootstraps Swarming."""
    self.m.swarming.show_isolated_out_in_collect_step = False
    self.m.swarming.show_shards_in_collect_step = True
    self.m.swarming_client.checkout('stable')
    self.m.swarming_client.query_script_version('swarming.py')

  @staticmethod
  def get_step_name(test):
    return str('%s (%s iOS %s)' % (
        test['app'], test['device type'], test['os']))

  def isolate_test(self, test, tmp_dir, isolate_template):
    """Isolates a single test."""
    task = {
        'isolate.gen': None,
        'isolated hash': None,
        'skip': 'skip' in test,
        'step name': self.get_step_name(test),
        'task': None,
        'test': copy.deepcopy(test),
        'tmp dir': None,
    }
    if task['skip']:
      return task

    app_path = self.m.path.join(self.most_recent_app_dir,
                                '%s.app' % test['app'])
    task['isolate.gen'] = tmp_dir.join('%s.isolate.gen.json' % test['id'])

    args = [
      '--config-variable', 'OS', 'ios',
      '--config-variable', 'app_path', app_path,
      '--config-variable', 'restart', (
        'true' if test.get('restart') else 'false'),
      '--config-variable', 'test_args', self.m.json.dumps(
          test.get('test args') or []),
      '--config-variable', 'xcode_version', test.get(
        'xcode version', self.__config['xcode version']),
      '--config-variable', 'xctest', (
        'true' if test.get('xctest') else 'false'),
      '--isolate', isolate_template,
      '--isolated', tmp_dir.join('%s.isolated' % test['id']),
      '--path-variable', 'app_path', app_path,
    ]
    if self.platform == 'simulator':
      args.extend([
        '--config-variable', 'platform', test['device type'],
        '--config-variable', 'version', test['os'],
      ])
    isolate_gen_file_contents = self.m.json.dumps({
      'args': args,
      'dir': self._ensure_checkout_dir(),
      'version': 1,
    }, indent=2)
    try:
      self.m.file.write_text(
        'generate %s.isolate.gen.json' % test['id'],
        task['isolate.gen'],
        isolate_gen_file_contents,
      )
      pres = self.m.step.active_result.presentation
      pres.logs['%s.isolate.gen.json' % test['id']] = (
        isolate_gen_file_contents.splitlines())
      pres.step_text = task['step name']
    except self.m.step.StepFailure as f:
      f.result.presentation.status = self.m.step.EXCEPTION
      task['isolate.gen'] = None

    return task

  def isolate(self, scripts_dir='src/ios/build/bots/scripts'):
    """Isolates the tests specified in this bot's build config."""
    assert self.__config

    tasks = []

    cmd = [
      '%s/run.py' % scripts_dir,
      '--app', '<(app_path)',
      '--args-json',
      '{"test_args": <(test_args), "xctest": <(xctest), "restart": <(restart)}',
      '--out-dir', '${ISOLATED_OUTDIR}',
      '--retries', '3',
      '--xcode-version', '<(xcode_version)',
    ]
    files = [
      # .apps are directories. Need the trailing slash to isolate the
      # contents of a directory.
      '<(app_path)/',
      '%s/' % scripts_dir,
    ]
    if self.platform == 'simulator':
      iossim = self.most_recent_iossim
      cmd.extend([
        '--iossim', iossim,
        '--platform', '<(platform)',
        '--version', '<(version)',
      ])
      files.append(iossim)
    isolate_template_contents = {
      'conditions': [
        ['OS == "ios"', {
          'variables': {
            'command': cmd,
            'files': files,
          },
        }],
      ],
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

    for test in self.__config['tests']:
      tasks.append(self.isolate_test(test, tmp_dir, isolate_template))
      tasks[-1]['buildername'] = self.m.properties['buildername']
    for bot, tests in self.__config['triggered tests'].iteritems():
      for test in tests:
        tasks.append(self.isolate_test(test, tmp_dir, isolate_template))
        tasks[-1]['buildername'] = bot

    gen_files = []
    for task in tasks:
      if task['isolate.gen'] and not task['skip']:
        gen_files.append(task['isolate.gen'])
    if not gen_files:
      return tasks

    cmd = [
      self.m.path['checkout'].join('tools', 'luci-go', 'mac64', 'isolate'),
      'batcharchive',
      '--dump-json', self.m.json.output(),
      '--isolate-server', self.m.isolate.isolate_server,
      '--verbose',
    ]
    cmd.extend(gen_files)
    step_result = self.m.step(
      'archive',
      cmd,
      infra_step=True,
      step_test_data=lambda: self.m.json.test_api.output({
        task['test']['id']: 'fake-hash-%s' % task['test']['id']
        for task in tasks
        if task['isolate.gen'] and not task['skip']
      }),
    )
    for task in tasks:
      if task['test']['id'] in step_result.json.output:
        task['isolated hash'] = step_result.json.output[task['test']['id']]

    return tasks

  def trigger(self, tasks):
    """Triggers the given Swarming tasks."""
    for task in tasks:
      if not task['isolated hash']: # pragma: no cover
        continue
      if task['buildername'] != self.m.properties['buildername']:
        continue

      task['tmp_dir'] = self.m.path.mkdtemp(task['test']['id'])
      swarming_task = self.m.swarming.task(
        task['step name'],
        task['isolated hash'],
        task_output_dir=task['tmp_dir'],
      )

      swarming_task.dimensions = {
        'pool': 'Chrome',
        'xcode_version': task['test'].get(
          'xcode version', self.__config['xcode version'])
      }
      if ('internal' not in self.m.properties['mastername'] and
        'official' not in self.m.properties['mastername']):
        # 4 cores are better than 8! See https://crbug.com/711845.
        swarming_task.dimensions['cores'] = '4'
      if self.platform == 'simulator':
        swarming_task.dimensions['os'] = 'Mac'
      elif self.platform == 'device':
        swarming_task.dimensions['os'] = 'iOS-%s' % str(task['test']['os'])
        swarming_task.dimensions['device_status'] = 'available'
        swarming_task.dimensions['device'] = self.PRODUCT_TYPES.get(
          task['test']['device type'])
        if not swarming_task.dimensions['device']:
          # Create a dummy step so we can annotate it to explain what
          # went wrong.
          step_result = self.m.step('[trigger] %s' % task['step name'], [])
          step_result.presentation.status = self.m.step.EXCEPTION
          step_result.presentation.logs['supported devices'] = sorted(
            self.PRODUCT_TYPES.keys())
          step_result.presentation.step_text = (
            'Requested unsupported device type.')
          continue

      spec = [
        self.m.properties['mastername'],
        self.m.properties['buildername'],
        task['test']['app'],
        self.platform,
        task['test']['device type'],
        task['test']['os'],
        swarming_task.dimensions['xcode_version'],
      ]
      # e.g.
      # chromium.mac:ios-simulator:base_unittests:simulator:iPad Air:10.0:8.0
      swarming_task.tags.add('spec_name:%s' % str(':'.join(spec)))

      swarming_task.tags.add(
          'device_type:%s' % str(task['test']['device type']))
      swarming_task.tags.add('ios_version:%s' % str(task['test']['os']))
      swarming_task.tags.add('platform:%s' % self.platform)
      swarming_task.tags.add('test:%s' % str(task['test']['app']))

      try:
        self.m.swarming.trigger_task(swarming_task)
        task['task'] = swarming_task
      except self.m.step.StepFailure as f:
        f.result.presentation.status = self.m.step.EXCEPTION

    return tasks

  def collect(self, tasks, upload_test_results=True):
    """Collects the given Swarming task results."""
    failures = set()
    infra_failure = False

    for task in tasks:
      if task['buildername'] != self.m.properties['buildername']:
        # This task isn't for this builder to collect.
        continue

      if task['skip']:
        # Create a dummy step to indicate we skipped this test.
        step_result = self.m.step('[skipped] %s' % task['step name'], [])
        step_result.presentation.step_text = (
            'This test was skipped because it was not affected.')
        continue

      if not task['task']:
        # We failed to trigger this test.
        # Create a dummy step for it and mark it as failed.
        step_result = self.m.step(task['step name'], [])
        step_result.presentation.status = self.m.step.EXCEPTION
        if not task['isolate.gen']:
          step_result.presentation.step_text = 'Failed to isolate the test.'
        else:
          step_result.presentation.step_text = 'Failed to trigger the test.'
        failures.add(task['step name'])
        infra_failure = True
        continue

      try:
        step_result = self.m.swarming.collect_task(task['task'])
      except self.m.step.StepFailure as f:
        step_result = f.result

      # We only run one shard, so the results we're interested in will
      # always be shard 0.
      swarming_summary = step_result.swarming.summary['shards'][0]
      state = swarming_summary['state']
      exit_code = (swarming_summary.get('exit_codes') or [None])[0]

      # Link to isolate file browser for files emitted by the test.
      if swarming_summary.get('isolated_out'):
        if swarming_summary['isolated_out'].get('view_url'):
          step_result.presentation.links['test data'] = (
              swarming_summary['isolated_out']['view_url'])

      # Interpret the result and set the display appropriately.
      if state == self.m.swarming.State.COMPLETED and exit_code is not None:
        # Task completed and we got an exit code from the iOS test runner.
        if exit_code == 1:
          step_result.presentation.status = self.m.step.FAILURE
          failures.add(task['step name'])
        elif exit_code == 2:
          # The iOS test runner exits 2 to indicate an infrastructure failure.
          step_result.presentation.status = self.m.step.EXCEPTION
          failures.add(task['step name'])
          infra_failure = True
      elif state == self.m.swarming.State.TIMED_OUT:
        # The task was killed for taking too long. This is a test failure
        # because the test itself hung.
        step_result.presentation.status = self.m.step.FAILURE
        step_result.presentation.step_text = 'Test timed out.'
        failures.add(task['step name'])
      elif state == self.m.swarming.State.EXPIRED:
        # No Swarming bot accepted the task in time.
        step_result.presentation.status = self.m.step.EXCEPTION
        step_result.presentation.step_text = (
          'No suitable Swarming bot found in time.'
        )
        failures.add(task['step name'])
        infra_failure = True
      else:
        step_result.presentation.status = self.m.step.EXCEPTION
        step_result.presentation.step_text = (
          'Unexpected infrastructure failure.'
        )
        failures.add(task['step name'])
        infra_failure = True

      # Add any iOS test runner results to the display.
      test_summary = self.m.path.join(
        task['task'].task_output_dir, '0', 'summary.json')
      if self.m.path.exists(test_summary): # pragma: no cover
        with open(test_summary) as f:
          test_summary_json = self.m.json.loads(f.read())
        step_result.presentation.logs['test_summary.json'] = self.m.json.dumps(
          test_summary_json, indent=2).splitlines()
        step_result.presentation.logs.update(test_summary_json.get('logs', {}))
        step_result.presentation.links.update(
          test_summary_json.get('links', {}))
        if test_summary_json.get('step_text'):
          step_result.presentation.step_text = '%s<br />%s' % (
            step_result.presentation.step_text, test_summary_json['step_text'])

      # Upload test results JSON to the flakiness dashboard.
      if self.m.bot_update.last_returned_properties and upload_test_results:
        test_results = self.m.path.join(
          task['task'].task_output_dir, '0', 'full_results.json')
        if self.m.path.exists(test_results):
          self.m.test_results.upload(
            test_results,
            task['test']['app'],
            self.m.bot_update.last_returned_properties.get(
              'got_revision_cp', 'x@{#0}'),
            builder_name_suffix='%s-%s' % (
              task['test']['device type'], task['test']['os']),
            test_results_server='test-results.appspot.com',
          )

      # Upload performance data result to the perf dashboard.
      perf_results = self.m.path.join(
        task['task'].task_output_dir, '0', 'Documents', 'perf_result.json')
      if self.m.path.exists(perf_results):
        data = self.get_perftest_data(perf_results)
        data_decode = data['Perf Data']
        data_result = []
        for testcase in data_decode:
          for trace in data_decode[testcase]['value']:
            data_point = self.m.perf_dashboard.get_skeleton_point(
              'chrome_ios_perf/%s/%s' % (testcase, trace),
              # TODO(huangml): Use revision.
              int(self.m.time.time()),
              data_decode[testcase]['value'][trace]
            )
            data_point['units'] = data_decode[testcase]['unit']
            data_result.extend([data_point])
        self.m.perf_dashboard.set_default_config()
        self.m.perf_dashboard.add_point(data_result)

    if failures:
      failure = self.m.step.StepFailure
      if infra_failure:
        failure = self.m.step.InfraFailure
      raise failure('Failed %s.' % ', '.join(sorted(failures)))

  def get_perftest_data(self, path):
    # Use fake data for recipe testing.
    if self._test_data.enabled:
      data = {
        'Perf Data' : {
          'startup test' : {
            'unit' : 'seconds',
            'value' : {
              'finish_launching' : 0.55,
              'become_active' : 0.68,
            }
          }
        }
      }
    else:
      with open(path) as f: # pragma: no cover
        data = self.m.json.loads(f.read())
    return data

  def test_swarming(self, scripts_dir='src/ios/build/bots/scripts',
                    upload_test_results=True):
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

      with self.m.step.nest('trigger'):
        self.trigger(tasks)

      self.collect(tasks, upload_test_results)

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
