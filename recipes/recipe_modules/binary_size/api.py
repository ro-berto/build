# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Binary size analysis for patchsets."""

import os
import re
from recipe_engine import recipe_api
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

from . import constants


def _normalize_name(v):
  # The real normalization function is in the infra/infra repo in
  # //luci/client/libs/logdog/streamname.py. This is a not so close
  # approximation that only works if you don't look too hard (eg: does not
  # handle case where first character is illegal).
  return re.sub(r'[^0-9A-Za-z:\-\./]', '_', v)


class BinarySizeApi(recipe_api.RecipeApi):

  def __init__(self, properties, **kwargs):
    super(BinarySizeApi, self).__init__(**kwargs)
    self._analyze_targets = list(properties.analyze_targets or
                                 constants.DEFAULT_ANALYZE_TARGETS)
    self.compile_targets = list(properties.compile_targets or
                                constants.DEFAULT_COMPILE_TARGETS)
    self.results_bucket = (
        properties.results_bucket or constants.NDJSON_GS_BUCKET)

    self._use_legacy_flow = not bool(properties.size_config_json)
    if self._use_legacy_flow:
      # TODO(huangs): Remove by mid 2020-11.
      apk_name = (
          properties.android.apk_name or constants.DEFAULT_PARAMS['apk_name'])
      mapping_names = (
          properties.android.mapping_names or
          constants.DEFAULT_PARAMS['mapping_file_names'])
      self._size_config_json = None
      # Store into |_size_config| for compatibility. Files are specified
      # relative to Chromium output directory.
      self._size_config = {
          'mapping_files': [
              os.path.join('apks', name) for name in mapping_names
          ],
          'resource_sizes_args': None,
          'supersize_input_file': os.path.join('apks', apk_name),
          'version': constants.VERSION_LEGACY_FLOW,
      }
    else:  # The "upcoming flow".
      # Path relative to chromium output directory.
      self._size_config_json = properties.size_config_json
      self._size_config = None  # Initialized in _ensure_size_config().

  def _ensure_size_config(self):
    """Load size config JSON if |_size_config| is not initialized.

    Load from JSON cannot take place in __init__() because it's a step.
    """
    if not self._size_config:
      path = self.m.chromium.output_dir.join(self._size_config_json)
      step_result = self.m.json.read(
          name=constants.READ_SIZE_CONFIG_JSON_STEP_NAME,
          path=path,
          step_test_data=lambda: self.m.json.test_api.output({
              'mapping_files': constants.TEST_MAPPING_FILES,
              'resource_sizes_args': {
                  'apk_name': constants.TEST_SUPERSIZE_INPUT_FILE,
              },
              'supersize_input_file': constants.TEST_SUPERSIZE_INPUT_FILE,
              'version': constants.TEST_VERSION_OLD,
          }))
      self._size_config = step_result.json.output

  def _make_version_string(self, supersize_input_file, version):
    """Helper to render version string."""
    return os.path.basename(supersize_input_file) + ',' + version

  def get_analysis_file_version_string(self):
    """Returns a version string for uploaded gs:// files.

    On significant binary package restructure (e.g., transitioning between
    Monochrome and Trichrome), the latest "without change" results stored in
    gs:// would be too stale to be used (i.e., recomputation is needed). This
    function returns a version string for staleness tagging and detection.
    """
    self._ensure_size_config()
    return self._make_version_string(self._size_config['supersize_input_file'],
                                     self._size_config['version'])

  def android_binary_size(self,
                          chromium_config,
                          gclient_config,
                          chromium_apply_configs=None,
                          gclient_apply_configs=None):
    """Determines the increase in binary size caused by the patch under test.

    To do so, this function:
     - syncs with the patch
     - exits early if none of the configured analyze targets were affected.
     - builds the configured compile targets with the patch
     - measures the size of the configured APK with the patch
     - syncs without the patch
     - builds the same targets without the patch
     - measures the size of the configured APK without the patch
     - reapplies the patch and compares the results

    In general, this recipe is responsible only for driving the execution of
    these steps and failing when necessary. The analysis and measurement logic
    is largely in //tools/binary_size in chromium/src.

    See http://bit.ly/2up0mcA for more information.

    Args:
      chromium_config: A string containing the name of the chromium
        recipe_module config to use.
      gclient_config: A string containing the name of the gclient
        recipe_module config to use.
      chromium_apply_configs: An optional list of strings containing the names
        of additional chromium recipe_module configs to apply.
      gclient_apply_configs: An optional list of strings containing the names
        of additional gclient recipe_module configs to apply.
    """
    assert self.m.tryserver.is_tryserver

    # Don't want milestone try builds to use gs analysis. The 'project' field
    # looks like 'chromium-m86'
    is_trunk_builder = (
        self.m.buildbucket.build.builder.project == 'chromium' and
        self.m.buildbucket.build.builder.bucket == 'try')
    use_gs_analysis = gclient_config == 'chromium' and is_trunk_builder

    with self.m.chromium.chromium_layout():
      self.m.gclient.set_config(gclient_config)
      for gclient_apply_config in gclient_apply_configs or []:
        self.m.gclient.apply_config(gclient_apply_config)
      self.m.chromium.set_config(chromium_config)
      for chromium_apply_config in chromium_apply_configs or []:
        self.m.chromium.apply_config(chromium_apply_config)
      self.m.chromium_android.set_config('base_config')

      revision_info = self.m.gerrit.get_revision_info(
          'https://%s' % self.m.tryserver.gerrit_change.host,
          self.m.tryserver.gerrit_change.change,
          self.m.tryserver.gerrit_change.patchset)
      author = revision_info['commit']['author']['email']
      commit_message = revision_info['commit']['message']
      is_revert = commit_message.startswith('Revert')
      # get_footer returns a list of footer values.
      has_size_footer = bool(
          self.m.tryserver.get_footer('Binary-Size', patch_text=commit_message))
      allow_regressions = is_revert or has_size_footer

      if use_gs_analysis:
        gs_zip_path = self._check_for_recent_tot_analysis()
        if gs_zip_path:
          recent_upload_revision = self._parse_gs_zip_path(gs_zip_path)[1]
          self.m.gclient.c.solutions[0].revision = recent_upload_revision

        try:
          bot_update_step = self.m.chromium_checkout.ensure_checkout(
              # Make sure that the git cache is refreshed with another origin
              # fetch to get a correct diff of the patch
              enforce_fetch=True)
        except self.m.step.StepFailure:
          # CL patch is incompatible with revision used in recently uploaded
          # analysis. Use the most recent trunk commit instead.
          self.m.gclient.c.solutions[0].revision = None
          use_gs_analysis = False
          bot_update_step = self.m.chromium_checkout.ensure_checkout()

      else:  # pragma: no cover
        bot_update_step = self.m.chromium_checkout.ensure_checkout()

      suffix = ' (with patch)'
      self.m.chromium.runhooks(name='runhooks' + suffix)

      self._clear_failed_expectation_files()

      affected_files = self.m.chromium_checkout.get_files_affected_by_patch()
      if not self.m.filter.analyze(affected_files, self._analyze_targets, None,
                                   'trybot_analyze_config.json')[0]:
        step_result = self.m.step.active_result
        step_result.presentation.properties[constants
                                            .PLUGIN_OUTPUT_PROPERTY_NAME] = {
                                                'listings': [],
                                                'extras': [],
                                            }
        return

      self.m.chromium.ensure_goma()
      staging_dir = self.m.path.mkdtemp('binary-size-trybot')
      expectations_result_path = staging_dir.join('expectations_result.json')

      # expectations_without_patch_json is never set when using cached reference
      # builds (via use_gs_analysis). This is fine since we expect
      # expectations_without_patch_json to exist only when using base
      # expectation files in different repositiories (e.g. //clank), and in this
      # case use_gs_analysis == False.
      expectations_without_patch_json = None
      with_results_dir, raw_result = self._build_and_measure(True, staging_dir)

      if raw_result and raw_result.status != common_pb.SUCCESS:
        return raw_result

      expectations_with_patch_json = self._check_for_failed_expectation_files(
          expectations_result_path, suffix)

      if use_gs_analysis and gs_zip_path:
        without_results_dir = self._download_recent_tot_analysis(
            gs_zip_path,
            staging_dir,
        )
      else:
        with self.m.context(cwd=self.m.chromium_checkout.working_dir):
          self.m.bot_update.deapply_patch(bot_update_step)

        with self.m.context(cwd=self.m.path['checkout']):
          suffix = ' (without patch)'

          self.m.chromium.runhooks(name='runhooks' + suffix)
          without_results_dir, raw_result = self._build_and_measure(
              False, staging_dir)

          if raw_result and raw_result.status != common_pb.SUCCESS:
            self.m.python.succeeding_step(constants.PATCH_FIXED_BUILD_STEP_NAME,
                                          '')
            return raw_result

        expectations_without_patch_json = (
            self._check_for_failed_expectation_files(expectations_result_path,
                                                     suffix))

        # Re-apply patch so that the diff scripts can be tested via tryjobs.
        # We could build without-patch first to avoid having to apply the patch
        # twice, but it's nicer to fail fast when the patch does not compile.
        suffix = ' (with patch again)'
        with self.m.context(cwd=self.m.chromium_checkout.checkout_dir):
          bot_update_step = self.m.bot_update.ensure_checkout(
              suffix=suffix, patch=True)
        self.m.chromium.runhooks(name='runhooks' + suffix)

      with self.m.context(cwd=self.m.path['checkout']):
        size_results_path = staging_dir.join('size_results.json')
        self._create_diffs(author, without_results_dir, with_results_dir,
                           size_results_path, staging_dir)
        expectation_success = self._maybe_fail_for_expectation_files(
            expectations_with_patch_json, expectations_without_patch_json)
        binary_size_success = self._check_for_undocumented_increase(
            size_results_path, staging_dir, allow_regressions)
        if not expectation_success or not binary_size_success:
          raise self.m.step.StepFailure(
              'Failed Checks. See Failing steps for details')

  def get_size_analysis_command(self, staging_dir):
    """Returns the command to compute size analysis files.

    Args:
      staging_dir: Staging directory to pass input files and and retrieve output
        size analysis files (e.g., .size and size JSON files).
    """
    self._ensure_size_config()
    generator_script = self.m.path['checkout'].join(
        'tools', 'binary_size', 'generate_commit_size_analysis.py')
    cmd = [generator_script]

    if self._use_legacy_flow:
      # The old arguments filename (not path), so apply os.path.basename().
      cmd += [
          '--apk-name',
          os.path.basename(self._size_config['supersize_input_file']),
      ]
      for mapping_name in self._size_config['mapping_files']:
        cmd += ['--mapping-name', os.path.basename(mapping_name)]
    else:
      assert self._size_config_json
      cmd += ['--size-config-json', self._size_config_json]
    cmd += ['--staging-dir', staging_dir]
    cmd += ['--chromium-output-directory', self.m.chromium.output_dir]
    return cmd

  def _parse_gs_zip_path(self, gs_zip_path):
    # Returns (timestamp, revision sha)
    # Example path: 'android-binary-size/commit_size_analysis/
    # 1592001045_551be50f2e3dae7dd1b31522fce7a91374c0efab.zip'
    m = re.search(r'.*\/(.*)_(.*)\.zip', gs_zip_path)
    return int(m.group(1)), m.group(2)

  def _check_for_recent_tot_analysis(self):
    gs_directory = 'android-binary-size/commit_size_analysis/'

    def generate_test_data():
      yield ('android-binary-size/commit_size_analysis/'
             '{}_551be50f2e3dae7dd1b31522fce7a91374c0efab.zip'.format(
                 constants.TEST_TIME))
      yield self._make_version_string(constants.TEST_SUPERSIZE_INPUT_FILE,
                                      constants.TEST_VERSION_OLD)

    lines = self.m.gsutil.cat(
        'gs://{bucket}/{source}'.format(
            bucket=self.results_bucket, source=gs_directory + 'LATEST'),
        stdout=self.m.raw_io.output(),
        step_test_data=lambda: self.m.raw_io.test_api.stream_output('\n'.join(
            generate_test_data())),
        name='cat LATEST').stdout.splitlines()
    gs_zip_path = lines[0]
    latest_upload_timestamp = self._parse_gs_zip_path(gs_zip_path)[0]

    # If the most recent upload was created over 2 hours ago, don't use it
    if int(self.m.time.time()) - int(latest_upload_timestamp) > 7200:
      return

    # Detect significant binary package restructure between the latest gs://
    # upload and the current CL. If detected, don't use the latest upload.
    prev_analysis_file_version_string = lines[1] if len(lines) > 1 else None
    if (prev_analysis_file_version_string !=
        self.get_analysis_file_version_string()):
      return

    return gs_zip_path

  def _download_recent_tot_analysis(self, gs_zip_path, staging_dir):
    local_zip = self.m.path.mkstemp()
    self.m.gsutil.download(
        bucket=self.results_bucket,
        source=gs_zip_path,
        dest=local_zip,
        name='Downloading zip')

    results_dir = staging_dir.join('without_patch')
    self.m.zip.unzip('Unzipping tot analysis', local_zip, results_dir)
    return results_dir

  def _build_and_measure(self, with_patch, staging_dir):
    suffix = ' (with patch)' if with_patch else ' (without patch)'
    results_basename = 'with_patch' if with_patch else 'without_patch'

    raw_result = self.m.chromium_tests.run_mb_and_compile(
        self.compile_targets, None, suffix)

    if raw_result.status != common_pb.SUCCESS:
      return None, raw_result

    results_dir = staging_dir.join(results_basename)
    self.m.file.ensure_directory('mkdir ' + results_basename, results_dir)

    self.m.step(
        name='Generate commit size analysis files',
        cmd=self.get_size_analysis_command(results_dir))

    return results_dir, None

  def _check_for_undocumented_increase(self, results_path, staging_dir,
                                       allow_regressions):
    step_result = self.m.json.read(
        constants.RESULT_JSON_STEP_NAME, results_path,
        step_test_data=lambda: self.m.json.test_api.output({
          'status_code': 0,
          'summary': '\n!summary!',
          'archive_filenames': [ 'result.ndjson', 'result.txt' ],
          'links': [
              {
                  'name': 'Resource Sizes Diff (high-level metrics)',
                  'lines': ['!resource_sizes!'],
                  'log_name': 'resource_sizes_log',
              }, {
                  'name': 'SuperSize Text Diff',
                  'lines': [u'!supersize text with \u0394!'],
              }, {
                  'name': 'Dex Method Diff',
                  'lines': ['!dex_methods!'],
                  'log_name': 'dex_methods_log',
              }, {
                  'name': 'Supersize HTML Diff',
                  'url': 'https://foo.com/{{result.ndjson}}',
              },
          ],
          'gerrit_plugin_details': {
            'listings': [
                {
                    'name': 'Normalised APK size',
                    'delta': '500 bytes',
                    'allowed': True,
                    'log_name': 'resource_sizes_log',
                },
            ],
            'extras': [
                {
                    'text': 'Supersize HTML Diff',
                    'url': 'https://foo.com/{{result.ndjson}}',
                },
                {
                    'text': 'SuperSize Text Diff',
                    'url': '{{result.txt}}',
                },
            ],
          }
      }))
    result_json = step_result.json.output
    # Upload files (.ndjson) to storage bucket.
    filename_map = {}
    for filename in result_json['archive_filenames']:
      filename_map[filename] = self._archive_artifact(staging_dir, filename)

    step_result = self.m.python.succeeding_step(constants.RESULTS_STEP_NAME,
                                                result_json['summary'])
    logname_map = {}
    for link in result_json['links']:
      if 'lines' in link:
        step_result.presentation.logs[link['name']] = link['lines']
        if 'log_name' in link:
          logname_map[link['log_name']] = self._synthesize_log_link(
              constants.RESULTS_STEP_NAME, link['name'])
      else:
        url = self._linkify_filenames(link['url'], filename_map)
        step_result.presentation.links[link['name']] = url

    gerrit_plugin_details = result_json.get('gerrit_plugin_details')
    if gerrit_plugin_details:
      for listing in gerrit_plugin_details['listings']:
        if 'log_name' in listing and listing['log_name'] in logname_map:
          listing['url'] = logname_map[listing['log_name']]
      for extra in gerrit_plugin_details['extras']:
        if 'url' in extra:
          url = extra['url']
          url = self._linkify_filenames(url, filename_map)
          extra['url'] = url
      step_result.presentation.properties[
          constants.PLUGIN_OUTPUT_PROPERTY_NAME] = gerrit_plugin_details

    if not allow_regressions and result_json['status_code'] != 0:
      step_result.presentation.status = self.m.step.FAILURE
      return False
    return True

  def _linkify_filenames(self, url, filename_map):
    for filename, archived_url in filename_map.iteritems():
      url = url.replace('{{' + filename + '}}', archived_url)
    return url

  def _synthesize_log_link(self, step_name, log_name):
    normalized_log_name = _normalize_name(log_name)
    normalized_step_name = _normalize_name(step_name)
    logdog = self.m.buildbucket.build.infra.logdog
    url = 'https://{}/logs/{}/{}/+/steps/{}/0/logs/{}/0'.format(
        logdog.hostname, logdog.project, logdog.prefix, normalized_step_name,
        normalized_log_name)
    return url

  def _create_diffs(self, author, before_dir, after_dir, results_path,
                    staging_dir):
    self._ensure_size_config()
    checker_script = self.m.path['checkout'].join(
        'tools', 'binary_size', 'trybot_commit_size_checker.py')

    with self.m.context(env={'PYTHONUNBUFFERED': '1'}):
      cmd = [checker_script]
      cmd += ['--author', author]
      if self._use_legacy_flow:
        cmd += [
            '--apk-name',
            os.path.basename(self._size_config['supersize_input_file'])
        ]
      else:
        cmd += [
            '--size-config-json-name',
            os.path.basename(self._size_config_json)
        ]
      cmd += ['--before-dir', before_dir]
      cmd += ['--after-dir', after_dir]
      cmd += ['--results-path', results_path]
      cmd += ['--staging-dir', staging_dir]
      self.m.step(name='Generate diffs', cmd=cmd)

  def _archive_artifact(self, staging_dir, filename):
    today = self.m.time.utcnow().date()
    gs_dest = '{}/{}/{}/{}'.format(self.m.buildbucket.builder_name,
                                   today.strftime('%Y/%m/%d'),
                                   self.m.buildbucket.build.number, filename)
    self.m.gsutil.upload(
        source=staging_dir.join(filename),
        bucket=self.results_bucket,
        dest=gs_dest,
        name='archive ' + filename,
        unauthenticated_url=True)
    return constants.ARCHIVED_URL_FMT.format(
        bucket=self.results_bucket, dest=gs_dest)

  def _check_for_failed_expectation_files(self, results_path, suffix):
    with self.m.context(cwd=self.m.chromium.output_dir):
      checker_script = self.resource('trybot_failed_expectations_checker.py')

      TEST_DATA = lambda: self.m.json.test_api.output({
          'success': True,
          'failed_messages': [],
      })
      step_result = self.m.python(
          'Run Expectations Script' + suffix,
          checker_script, [
              '--check-expectations',
              '--results-path',
              self.m.json.output(),
              '--output-directory',
              self.m.chromium.output_dir,
              '--clear-expectations',
          ],
          step_test_data=TEST_DATA)
      return step_result.json.output

  def _maybe_fail_for_expectation_files(self, expectations_with_patch_json,
                                        expectations_without_patch_json):
    with self.m.step.nest(constants.EXPECTATIONS_STEP_NAME) as presentation:
      if expectations_with_patch_json['success']:
        presentation.step_text += '<br/>Expectations are up-to-date.'
      else:
        presentation.logs['failed expectations'] = (
            expectations_with_patch_json['failed_messages'])
        # For android-internal-binary-size, expectations are diffs against base
        # expectations in //src, and sometimes changes to the base files can
        # cause the diffs to become stale. Don't fail trybots in this case.
        if expectations_with_patch_json != expectations_without_patch_json:
          presentation.step_text += (
              '<br/>Expectations file need to be updated.')
          if (expectations_without_patch_json and
              not expectations_without_patch_json['success']):
            presentation.step_text += (
                '<br/>Note: Expectations did not match both with and '
                'without patch. You need to update the expecations to '
                'account for your change as well as some unrelated changes '
                '(this is fine / normal).')
          presentation.status = self.m.step.FAILURE
          return False
        else:
          presentation.status = self.m.step.WARNING
          presentation.step_text += (
              '<br/>Expectations did not match without patch either.')
    return True

  def _clear_failed_expectation_files(self):
    """Clear expectation files from a previous run of the bot"""

    checker_script = self.resource('trybot_failed_expectations_checker.py')

    # This step needs to happen after gn gen but before compile since it
    # requires a var to be written to build_vars.txt. Otherwise, it raises an
    # exception if this is the first run of the bot after a gn clean.
    # But that is not possible because both are combined into one step.
    # However, we can safely ignore said exception because if build_vars.txt is
    # empty, then there are no expectation files regardless. If the problem is
    # more serious, it will be caught later in
    # _check_for_failed_expectation_files.
    self.m.python(
        'Clear Expectation Files',
        checker_script, [
            '--clear-expectations',
            '--output-directory',
            self.m.chromium.output_dir,
        ],
        ok_ret='any')
