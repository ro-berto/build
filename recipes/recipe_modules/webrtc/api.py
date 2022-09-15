# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import urllib

from recipe_engine import recipe_api
from RECIPE_MODULES.build.chromium_tests_builder_config import builder_spec

from . import builders

_WEBRTC_GS_BUCKET = 'chromium-webrtc'
_DASHBOARD_UPLOAD_URL = 'https://chromeperf.appspot.com'
_PERF_MACHINE_GROUP = 'WebRTCPerf'
_BINARY_SIZE_TARGETS = (
    'AppRTCMobile',
    'libjingle_peerconnection_so',
    'webrtc',
)


def _sanitize_file_name(name):
  safe_with_spaces = ''.join(c if c.isalnum() else ' ' for c in name)
  return '_'.join(safe_with_spaces.split())


def _replace_string_in_dict(dict_input, old, new):
  dict_output = {}
  for key, values in dict_input.items():
    dict_output[key] = [value.replace(old, new) for value in values]
  return dict_output


def _get_isolated_targets(tests):
  return [t.canonical_name for t in tests if t.runs_on_swarming]


def _get_test_targets_from_config(targets_config, phase):
  if phase is None:
    return [t.canonical_name for t in targets_config.all_tests]
  if phase == 'rtti_no_sctp':
    return [t.canonical_name for t in targets_config.all_tests]
  return []


def _is_triggering_perf_tests(builder_id, builder_config):
  to_trigger = builder_config.builder_db.builder_graph[builder_id]
  return any(builders.BUILDERS_DB[b].perf_id for b in to_trigger)


class WebRTCApi(recipe_api.RecipeApi):

  @property
  def revision(self):
    return self.m.chromium.build_properties.get('got_revision')

  @property
  def revision_cp(self):
    return self.m.chromium.build_properties.get('got_revision_cp')

  @property
  def revision_number(self):
    branch, number = self.m.commit_position.parse(self.revision_cp)
    assert branch.endswith('/main')
    return number

  def apply_bot_config(self, builder_id, builder_config):
    self.m.chromium_tests.configure_build(builder_config)
    if self.m.tryserver.is_tryserver:
      self.m.chromium.apply_config('trybot_flavor')

    if builders.BUILDERS_DB[builder_id].perf_id:
      assert self.m.chromium.c.BUILD_CONFIG == 'Release', (
          'Perf tests should only be run with Release builds.')
    if builders.BUILDERS_DB[builder_id].execution_mode == builder_spec.TEST:
      assert self.m.properties.get('parent_got_revision'), (
          'Testers should only be run with "parent_got_revision" property.')

  def determine_compilation_targets(self, builder_id, targets_config, phase):
    """ Returns the tests to run and the targets to compile."""
    test_targets = _get_test_targets_from_config(targets_config, phase)

    patch_root = self.m.gclient.get_gerrit_patch_root()
    affected_files = self.m.chromium_checkout.get_files_affected_by_patch(
        relative_to=patch_root, cwd=self.m.path['checkout'])

    # CI bots can rebuild everything; they're less time sensitive than trybots.
    if not self.m.tryserver.is_tryserver:
      # Perf testers are a special case; they only need the catapult protos.
      spec = builders.BUILDERS_DB[builder_id]
      if spec.execution_mode == builder_spec.TEST and spec.perf_id:
        return test_targets, ['webrtc_dashboard_upload']
      return test_targets, ['all']

    test_targets, compile_targets = self.m.filter.analyze(
        affected_files,
        test_targets,
        additional_compile_targets=['all'],
        mb_path=self.m.path['checkout'].join('tools_webrtc', 'mb'),
        phase=phase)

    # Some trybots are used to calculate the binary size impact of the current
    # CL. These targets should always be built.
    binary_size_files = builders.BUILDERS_DB[builder_id].binary_size_files or []
    for filename in binary_size_files:
      compile_targets += [t for t in _BINARY_SIZE_TARGETS if t in filename]
    return test_targets, sorted(set(compile_targets))

  def should_download_audio_quality_tools(self, builder_id, builder_config):
    # Perf test low_bandwidth_audio_perf_test doesn't run on iOS and Mac M1
    # Arm64, presumably because the tools are not compiled for arm64.
    if any(b in builder_id.builder.lower() for b in ('ios', 'm1 arm64')):
      return False
    return (builders.BUILDERS_DB[builder_id].perf_id or
            _is_triggering_perf_tests(builder_id, builder_config))

  def should_download_video_quality_tools(self, builder_id, builder_config):
    if 'android' not in builder_id.builder.lower():
      return False
    return (builders.BUILDERS_DB[builder_id].perf_id or
            _is_triggering_perf_tests(builder_id, builder_config))

  def download_audio_quality_tools(self):
    args = [self.m.path['checkout'].join('tools_webrtc', 'audio_quality')]
    script = self.m.path['checkout'].join('tools_webrtc', 'download_tools.py')
    cmd = ['vpython3', '-u', script] + args

    with self.m.depot_tools.on_path():
      self.m.step('download audio quality tools', cmd)

  def download_video_quality_tools(self):
    with self.m.depot_tools.on_path():
      # Video quality tools
      args_tools = [
          self.m.path['checkout'].join('tools_webrtc',
                                       'video_quality_toolchain', 'linux')
      ]
      script_tools = self.m.path['checkout'].join('tools_webrtc',
                                                  'download_tools.py')
      cmd_tools = ['vpython3', '-u', script_tools] + args_tools
      self.m.step('download video quality tools', cmd_tools)

      # AppRTC
      args_apprtc = [
          '--bucket=chromium-webrtc-resources', '--directory',
          self.m.path['checkout'].join('rtc_tools', 'testing')
      ]
      script_apprtc = self.m.depot_tools.download_from_google_storage_path
      cmd_apprtc = ['vpython3', '-u', script_apprtc] + args_apprtc
      self.m.step('download apprtc', cmd_apprtc)

      # Golang
      args_golang = [
          '--bucket=chromium-webrtc-resources', '--directory',
          self.m.path['checkout'].join('rtc_tools', 'testing', 'golang',
                                       'linux')
      ]
      script_golang = self.m.depot_tools.download_from_google_storage_path
      cmd_golang = ['vpython3', '-u', script_golang] + args_golang
      self.m.step('download golang', cmd_golang)

  def override_relient_mb_config(self):
    """Override mb_config.pyl to use reclient."""

    mb_config_path = self.m.path['checkout'].join('tools_webrtc', 'mb',
                                                  'mb_config.pyl')
    mb_config = self.m.file.read_text('Read %s' % mb_config_path,
                                      mb_config_path)
    mb_config = mb_config.replace('use_goma=true', 'use_remoteexec=true')
    new_mb_config_path = self.m.path['tmp_base'].join('mb_config.pyl')
    self.m.file.write_text(
        'Override MB config to use reclient',
        new_mb_config_path,
        mb_config,
    )
    return new_mb_config_path

  def run_mb(self, builder_id, phase=None, tests=None, mb_config_path=None):
    if phase:
      # Set the out folder to be the same as the phase name, so caches of
      # consecutive builds don't interfere with each other.
      self.m.chromium.c.build_config_fs = _sanitize_file_name(phase)
    elif 'ios' in builder_id.builder.lower():
      # TODO(crbug.com/1048758): The out folder is hardcoded when calling otool
      # in the ios script logic for running the tests on multiple shards.
      pass
    else:
      # Set the out folder to be the same as the builder name, so the whole
      # 'src' folder can be shared between builder types.
      self.m.chromium.c.build_config_fs = _sanitize_file_name(
          builder_id.builder)

    return self.m.chromium.mb_gen(
        builder_id,
        phase=phase,
        mb_path=self.m.path['checkout'].join('tools_webrtc', 'mb'),
        mb_config_path=mb_config_path,
        isolated_targets=_get_isolated_targets(tests or []))

  def isolate(self, builder_id, builder_config, tests):
    if builders.BUILDERS_DB[builder_id].execution_mode == builder_spec.TEST:
      # The tests running on a 'tester' bot are isolated by the 'builder'.
      self.m.isolate.check_swarm_hashes(_get_isolated_targets(tests))
    elif _is_triggering_perf_tests(builder_id, builder_config):
      # Set the swarm_hashes name so that it is found by pinpoint.
      commit_position = self.revision_cp.replace('@', '(at)')
      swarm_hashes_property_name = '_'.join(
          ('swarm_hashes', commit_position, 'without_patch'))

      self.m.isolate.isolate_tests(
          self.m.chromium.output_dir,
          targets=_get_isolated_targets(tests),
          swarm_hashes_property_name=swarm_hashes_property_name)

      # Upload the input files to the pinpoint server.
      self.m.perf_dashboard.upload_isolate(
          builder_id.builder,
          self.m.perf_dashboard.get_change_info([{
              'repository': 'webrtc',
              'git_hash': self.revision
          }]), self.m.cas.instance, self.m.isolate.isolated_tests)
    else:
      self.m.isolate.isolate_tests(
          self.m.chromium.output_dir, targets=_get_isolated_targets(tests))

  def set_upload_build_properties(self, builder_id):
    experiment_prefix = 'Experimental' if self.m.runtime.is_experimental else ''
    bucketname = self.m.buildbucket.bucket_v1
    build_url = 'https://ci.chromium.org/p/%s/builders/%s/%s/%s' % (
        urllib.parse.quote(self.m.buildbucket.build.builder.project),
        urllib.parse.quote(bucketname), urllib.parse.quote(builder_id.builder),
        urllib.parse.quote(str(self.m.buildbucket.build.number)))
    # Don't overwrite existing chromium build_properties
    build_props = self.m.chromium.build_properties or {}
    build_props.update({
        'build_page_url': build_url,
        'bot': builders.BUILDERS_DB[builder_id].perf_id,
        'dashboard_url': _DASHBOARD_UPLOAD_URL,
        'commit_position': self.revision_number,
        'webrtc_git_hash': self.revision,
        'perf_dashboard_machine_group': experiment_prefix + _PERF_MACHINE_GROUP,
        'outdir': self.m.chromium.output_dir,
    })
    self.m.chromium.set_build_properties(build_props)

  def set_test_command_lines(self, builder_id, tests):
    if builders.BUILDERS_DB[builder_id].execution_mode != builder_spec.TEST:
      return self.m.chromium_tests.set_swarming_test_execution_info(
          tests, self.m.chromium_tests.find_swarming_command_lines(''),
          self.m.path.relpath(self.m.chromium.output_dir,
                              self.m.path['checkout']))

    # Tester builders only triggers swarming tests built on 'builder' bots
    # so the swarming command line needs to be retrieved from build
    # parameters.
    swarming_command_lines = _replace_string_in_dict(
        self.m.properties.get('swarming_command_lines'),
        'WILL_BE_ISOLATED_OUTDIR',
        'ISOLATED_OUTDIR',
    )
    # Tester builders run their tests in the parent builder out directory.
    parent_buildername = builders.BUILDERS_DB[builder_id].parent_buildername
    output_dir = str(self.m.chromium.output_dir).replace(
        _sanitize_file_name(builder_id.builder),
        _sanitize_file_name(parent_buildername))

    relative_cwd = self.m.path.relpath(output_dir, self.m.path['checkout'])
    for test in tests:
      if test.runs_on_swarming:
        command_line = swarming_command_lines.get(test.canonical_name, [])
        if command_line:
          test.raw_cmd = command_line
          test.relative_cwd = relative_cwd

  def get_binary_sizes(self, files, base_dir=None):
    args = [
        '--base-dir', base_dir or self.m.chromium.output_dir, '--output',
        self.m.json.output(), '--'
    ] + list(files)
    cmd = ['vpython3', '-u', self.resource('binary_sizes.py')] + args

    result = self.m.step(
        'get binary sizes',
        cmd,
        infra_step=True,
        step_test_data=self.test_api.example_binary_sizes)
    result.presentation.properties['binary_sizes'] = result.json.output

  def build_with_reclient(self, step_name, cmd):
    cmd += ['--use-remoteexec']
    # TODO(b/243628179): get ninja command generated in build_aar.py
    ninja_command = ""
    with self.m.reclient.process(step_name, ninja_command) as p:
      step_result = self.m.step(step_name, cmd)
      p.build_exit_status = step_result.retcode

  def build_with_goma(self, step_name, cmd):
    goma_dir = self.m.goma.ensure_goma()
    self.m.goma.start()

    cmd += ['--use-goma', '--extra-gn-args', 'goma_dir=\"%s\"' % goma_dir]

    build_exit_status = 1
    try:
      step_result = self.m.step(step_name, cmd)
      build_exit_status = step_result.retcode
    except self.m.step.StepFailure as e:
      build_exit_status = e.retcode
      raise e
    finally:
      self.m.goma.stop(
          ninja_log_compiler='goma', build_exit_status=build_exit_status)

  def build_android_archive(self, use_reclient):
    # Build the Android .aar archive and upload it to Google storage (except for
    # trybots). This should only be run on a single bot or the archive will be
    # overwritten (and it's a multi-arch build so one is enough).
    build_script = self.m.path['checkout'].join('tools_webrtc', 'android',
                                                'build_aar.py')
    args = ['--verbose']
    if self.m.tryserver.is_tryserver:
      # To benefit from incremental builds for speed.
      args.append('--build-dir=out/android-archive')

    cmd = ['vpython3', '-u', build_script] + args

    with self.m.context(cwd=self.m.path['checkout']):
      with self.m.depot_tools.on_path():
        build_step_name = 'build android archive'
        if use_reclient:
          build_dir = self.m.path.join(self.m.path['checkout'],
                                       'andriod-archive')
          cmd += ['--build-dir', build_dir]
          self.build_with_reclient(build_step_name, cmd)
          self.m.file.rmtree('Remove android archive dir', build_dir)
        else:
          self.build_with_goma(build_step_name, cmd)

    if not self.m.tryserver.is_tryserver and not self.m.runtime.is_experimental:
      self.m.gsutil.upload(
          self.m.path['checkout'].join('libwebrtc.aar'),
          'chromium-webrtc',
          'android_archive/webrtc_android_%s.aar' % self.revision_number,
          args=['-a', 'public-read'],
          unauthenticated_url=True)

  def package_apprtcmobile(self, builder_id):
    # Zip and upload out/{Debug,Release}/apks/AppRTCMobile.apk
    apk_root = self.m.chromium.c.build_dir.join(
        self.m.chromium.c.build_config_fs, 'apks')
    zip_path = self.m.path['start_dir'].join('AppRTCMobile_apk.zip')

    pkg = self.m.zip.make_package(apk_root, zip_path)
    pkg.add_file(apk_root.join('AppRTCMobile.apk'))
    pkg.zip('AppRTCMobile zip archive')

    apk_upload_url = 'client.webrtc/%s/AppRTCMobile_apk_%s.zip' % (
        builder_id.builder, self.revision_number)
    if not self.m.runtime.is_experimental:
      self.m.gsutil.upload(
          zip_path,
          _WEBRTC_GS_BUCKET,
          apk_upload_url,
          args=['-a', 'public-read'],
          unauthenticated_url=True)

  def run_tests(self, builder_id, tests):
    if not tests:
      return

    if builders.BUILDERS_DB[builder_id].perf_id:
      self.set_upload_build_properties(builder_id)

    self.set_test_command_lines(builder_id, tests)
    test_runner = self.m.chromium_tests.create_test_runner(
        tests, enable_infra_failure=True)
    return test_runner()

  def trigger_child_builds(self, builder_id, builder_config, update_step):
    # If the builder is triggered by pinpoint, don't trigger any bots.
    if any('pinpoint_job_id' in t.key for t in self.m.buildbucket.build.tags):
      return

    if _is_triggering_perf_tests(builder_id, builder_config):
      # Replace ISOLATED_OUTDIR by WILL_BE_ISOLATED_OUTDIR to prevent
      # the variable to be expanded by the builder instead of the tester.
      swarming_command_lines = _replace_string_in_dict(
          self.m.chromium_tests.find_swarming_command_lines(suffix=''),
          'ISOLATED_OUTDIR',
          'WILL_BE_ISOLATED_OUTDIR',
      )
      properties = {
          'swarming_command_lines': swarming_command_lines,
          'swarm_hashes': self.m.isolate.isolated_tests,
      }
      self.m.chromium_tests.trigger_child_builds(
          builder_id, update_step, builder_config, properties,
          self.m.buildbucket.gitiles_commit)
