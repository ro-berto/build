# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""API for the perf try job recipe module.

This API is meant to enable the perf try job recipe on any chromium-supported
platform for any test that can be run via buildbot, perf or otherwise.
"""

import re
import urllib
import uuid

from recipe_engine import recipe_api
from . import build_state

PERF_CONFIG_FILE = 'tools/run-perf-test.cfg'
WEBKIT_PERF_CONFIG_FILE = 'third_party/WebKit/Tools/run-perf-test.cfg'

CLOUD_RESULTS_LINK = (r'\s(?P<VALUES>https://console.developers.google.com/'
    'm/cloudstorage/b/chromium-telemetry/o/html-results/results-[a-z0-9-_]+)\s')
PROFILER_RESULTS_LINK = (r'\s(?P<VALUES>https://console.developers.google.com/'
                         'm/cloudstorage/b/[a-z-]+/o/profiler-[a-z0-9-_.]+)\s')
RESULTS_BANNER = """
===== PERF TRY JOB RESULTS =====

Test Command: %(command)s
Test Metric: %(metric)s
Relative Change: %(relative_change).05f%%
Standard Error: +- %(std_err).05f delta

%(results)s
"""

class PerfTryJobApi(recipe_api.RecipeApi):

  def __init__(self, *args, **kwargs):
    super(PerfTryJobApi, self).__init__(*args, **kwargs)
    self.is_internal = False

  def set_internal(self):
    self.is_internal = True  # pragma: no cover

  def start_perf_try_job(self, api, affected_files, bot_update_step, bot_db):
    """Entry point pert tryjob or CQ tryjob."""
    perf_config = self._get_perf_config(api, affected_files)
    if perf_config:
      self._run_perf_job(perf_config, bot_update_step, bot_db)
    else:
      self.m.halt('Could not load config file. Double check your changes to '
                  'config files for syntax errors.')

  def _run_perf_job(self, perf_cfg, bot_update_step, bot_db):
    """Runs performance try job with and without patch."""
    r = self._resolve_revisions_from_config(perf_cfg)
    test_cfg = self.m.bisect_tester_staging.load_config_from_dict(perf_cfg)

    # TODO(prasadv): This is tempory hack to prepend 'src' to test command,
    # until dashboard and trybot scripts are changed.
    _prepend_src_to_path_in_command(test_cfg)

    # Always set the upload bucket to public for perf try jobs on the public
    # waterfall, and private on internal ones.
    _modify_upload_bucket(test_cfg, not self.is_internal)

    # Run with patch.
    with self.m.step.nest('Running WITH patch'):
      results_label = 'Patch'
      if r[0]:
        results_label += '_%s' % r[0]
      results_with_patch = self._build_and_run_tests(
          test_cfg, bot_update_step, bot_db, r[0],
          name='With Patch',
          reset_on_first_run=True,
          upload_on_last_run=True,
          results_label=results_label,
          allow_flakes=False)

    with self.m.step.nest('De-applying patch'):
      if not any(r):
        # Revert changes.
        self.m.chromium_tests.deapply_patch(bot_update_step)

    # Run without patch.
    results_label_without_patch = 'TOT' if r[1] is None else r[1]
    with self.m.step.nest('Running WITHOUT patch'):
      results_name = 'Without Patch'
      results_without_patch = self._build_and_run_tests(
          test_cfg, bot_update_step, bot_db, r[1],
          name=results_name,
          reset_on_first_run=False,
          upload_on_last_run=True,
          results_label=results_label_without_patch,
          allow_flakes=False)

    labels = {
        'profiler_link1': ('%s - Profiler Data' % 'With Patch'
                           if r[0] is None else r[0]),
        'profiler_link2': ('%s - Profiler Data' % 'Without Patch'
                           if r[1] is None else r[1])
    }

    # TODO(chrisphan): Deprecate this.  perf_dashboard.post_bisect_results below
    # already outputs data in json format.
    with self.m.step.nest('Results'):
      self._compare_and_present_results(
          test_cfg, results_without_patch, results_with_patch, labels,
          results_label_without_patch)

    with self.m.step.nest('Notify dashboard'):
      bisect_results = self.get_result(
          test_cfg, results_without_patch, results_with_patch, labels)
      self.m.perf_dashboard.set_default_config()
      self.m.perf_dashboard.post_bisect_results(
          bisect_results, halt_on_failure=True)

  def _checkout_revision(self, update_step, revision=None):
    """Checkouts specific revisions and updates bot_update step."""
    if revision:
      if self.m.platform.is_win:  # pragma: no cover
        self.m.chromium.taskkill()
      self.m.gclient.c.revisions['src'] = str(revision)
      update_step = self.m.bot_update.ensure_checkout(
          suffix=str(revision), patch=False, update_presentation=False)
      assert update_step.json.output['did_run']
      with self.m.context(cwd=self.m.path['checkout']):
        self.m.chromium.runhooks(name='runhooks on %s' % str(revision))

    return update_step

  def _run_test(self, cfg, **kwargs):
    """Runs test from config and return results."""
    all_values = self.m.bisect_tester_staging.run_test(
        cfg, **kwargs)
    overall_success = True
    if (not kwargs.get('allow_flakes', True) and
        cfg.get('test_type', 'perf') != 'return_code'):
      overall_success = all(v == 0 for v in all_values['retcodes'])
    return {
        'results': all_values,
        'ret_code': overall_success,
        'output': ''.join(all_values['output'])
    }

  def _build_and_run_tests(self, cfg, update_step, bot_db, revision_hash,
                           **kwargs):
    """Compiles binaries and runs tests for a given a revision."""
    with_patch = 'With Patch' in kwargs.get('name')  # pragma: no cover

    # We don't need to do a checkout if there's a patch applied, since that will
    # overwrite the local changes and potentially change the test results.
    if not with_patch:  # pragma: no cover
      update_step = self._checkout_revision(update_step, revision_hash)
    if not revision_hash:
      if update_step.presentation.properties:
        revision_hash = update_step.presentation.properties['got_revision']
    revision = build_state.BuildState(self, revision_hash, with_patch)
    # request build and wait for it only when the build is nonexistent
    if with_patch or not self._gsutil_file_exists(revision.build_file_path):
      revision.request_build()
      revision.wait_for()
    revision.download_build(update_step, bot_db)
    if self.m.chromium.c.TARGET_PLATFORM == 'android':
      self.m.chromium_android.adb_install_apk('ChromePublic.apk')

    return self._run_test(cfg, **kwargs)

  def _gsutil_file_exists(self, path):
    """Returns True if a file exists at the given GS path."""
    try:
      self.m.gsutil(['ls', path], name='exists')
    except self.m.step.StepFailure:  # pragma: no cover
      return False
    return True # pragma: no cover

  def _load_config_file(self, name, src_path, **kwargs):
    """Attempts to load the specified config file and grab config dict."""
    step_result = self.m.python(
        name,
        self.resource('load_config_to_json.py'),
        ['--source', src_path, '--output_json', self.m.json.output()],
        **kwargs)
    if not step_result.json.output:  # pragma: no cover
      raise self.m.step.StepFailure('Loading config file failed. [%s]' %
                                    src_path)
    return step_result.json.output

  def _get_perf_config(self, api, affected_files):
    """Checks affected config file and loads the config params to a dict."""
    perf_cfg_files = [PERF_CONFIG_FILE, WEBKIT_PERF_CONFIG_FILE]
    cfg_file = [f for f in perf_cfg_files if str(f) in affected_files]
    if cfg_file:  # pragma: no cover
      # Try reading any possible perf test config files.
      cfg_content = self._load_config_file(
          'load config', self.m.path['checkout'].join(cfg_file[0]))
    elif api.properties.get('perf_try_config'):  # pragma: no cover
      cfg_content = dict(api.m.properties.get('perf_try_config'))
    else:
      return None

    cfg_is_valid = _validate_perf_config(
        cfg_content, required_parameters=['command'])
    if cfg_content and cfg_is_valid:
      return cfg_content

    return None

  def _get_hash(self, rev):
    """Returns git hash for the given commit position."""
    def _check_if_hash(s):  # pragma: no cover
      if len(s) <= 8:
        try:
          int(s)
          return False
        except ValueError:
          pass
      elif not re.match(r'[a-fA-F0-9]{40}$', str(s)):
        raise RuntimeError('Error, Unsupported revision %s' % s)
      return True

    if _check_if_hash(rev):  # pragma: no cover
      return rev

    try:
      result = self.m.commit_position.chromium_hash_from_commit_position(rev)
    except self.m.step.StepFailure as sf:  # pragma: no cover
      self.m.halt(('Failed to resolve commit position %s- ' % rev) + sf.reason)
      raise
    return result

  def _resolve_revisions_from_config(self, config):
    """Resolves commit position into git hash for good and bad revisions."""
    if 'good_revision' not in config and 'bad_revision' not in config:
      return (None, None)
    return (self._get_hash(config.get('bad_revision')),
            self._get_hash(config.get('good_revision')))

  def _compare_and_present_results(
      self, cfg, results_without_patch, results_with_patch, labels,
      results_label_without_patch):
    """Parses results and creates Results step."""
    step_result = self.m.step.active_result

    output_with_patch = results_with_patch.get('output')
    output_without_patch = results_without_patch.get('output')
    values_with_patch, values_without_patch = self.parse_values(
        results_with_patch.get('results'),
        results_without_patch.get('results'),
        cfg.get('metric'),
        _output_format(cfg.get('command')))

    cloud_links_without_patch = self.parse_cloud_links(output_without_patch)
    cloud_links_with_patch = self.parse_cloud_links(output_with_patch)

    results_link = (cloud_links_without_patch['html'][0]
                    if cloud_links_without_patch['html'] else '')

    if results_link:
      # Automatically compare the Patch column against the TOT column and set
      # the summary statistic to percent delta average:
      # Use URL fragment since cloudstorage loses query.
      results_link += '#r=' + results_label_without_patch
      results_link += '&s=%25' + unichr(916) + 'avg'

      step_result.presentation.links.update({'HTML Results': results_link})

    profiler_with_patch = cloud_links_with_patch['profiler']
    profiler_without_patch = cloud_links_without_patch['profiler']

    if profiler_with_patch and profiler_without_patch:
      for i in xrange(len(profiler_with_patch)):  # pragma: no cover
        step_result.presentation.links.update({
            '%s[%d]' % (
                labels.get('profiler_link1'), i): profiler_with_patch[i]
        })
      for i in xrange(len(profiler_without_patch)):  # pragma: no cover
        step_result.presentation.links.update({
            '%s[%d]' % (
                labels.get('profiler_link2'), i): profiler_without_patch[i]
        })

    if not values_with_patch or not values_without_patch:
      return

    mean_with_patch = self.m.math_utils.mean(values_with_patch)
    mean_without_patch = self.m.math_utils.mean(values_without_patch)

    # TODO(qyearsley): Change this to print either std. dev. and sample
    # size if that makes sense, or remove this computation altogether if
    # values_with_patch and values_without_patch are expected to always
    # contain only one value.
    stderr_with_patch = self.m.math_utils.standard_error(values_with_patch)
    stderr_without_patch = self.m.math_utils.standard_error(
        values_without_patch)

    # Calculate the % difference in the means of the 2 runs.
    relative_change = None
    std_err = None
    if mean_with_patch and values_with_patch:
      relative_change = self.m.math_utils.relative_change(
          mean_without_patch, mean_with_patch) * 100
      std_err = self.m.math_utils.pooled_standard_error(
          [values_with_patch, values_without_patch])

    if relative_change is not None and std_err is not None:
      data = [
          ['Revision', 'Mean', 'Std.Error'],
          ['Patch', str(mean_with_patch), str(stderr_with_patch)],
          ['No Patch', str(mean_without_patch), str(stderr_without_patch)]
      ]
      display_results = RESULTS_BANNER % {
          'command': cfg.get('command'),
          'metric': cfg.get('metric', 'NO SPECIFIED'),
          'relative_change': relative_change,
          'std_err': std_err,
          'results': _pretty_table(data),
      }
      step_result.presentation.step_text += (
          self.m.test_utils.format_step_text([[display_results]]))

  def parse_cloud_links(self, output):
    html_results_pattern = re.compile(CLOUD_RESULTS_LINK, re.MULTILINE)
    profiler_pattern = re.compile(PROFILER_RESULTS_LINK, re.MULTILINE)

    results = {
        'html': html_results_pattern.findall(output),
        'profiler': profiler_pattern.findall(output),
    }
    return results


  def get_result(self, config, results_without_patch, results_with_patch,
                 labels):
    """Returns the results as a dict."""
    output_with_patch = results_with_patch.get('output')
    output_without_patch = results_without_patch.get('output')

    values_with_patch, values_without_patch = self.parse_values(
        results_with_patch.get('results'),
        results_without_patch.get('results'),
        config.get('metric'),
        _output_format(config.get('command')))

    cloud_links_without_patch = self.parse_cloud_links(output_without_patch)
    cloud_links_with_patch = self.parse_cloud_links(output_with_patch)

    cloud_link = (cloud_links_without_patch['html'][0]
                  if cloud_links_without_patch['html'] else '')

    results = {
        'try_job_id': config.get('try_job_id'),
        'status': 'completed',  # TODO(chrisphan) Get partial results state.
        'buildbot_log_url': self._get_build_url(),
        'bisect_bot': self.m.properties.get('buildername', 'Not found'),
        'command': config.get('command'),
        'metric': config.get('metric'),
        'cloud_link': cloud_link,
    }

    if not values_with_patch or not values_without_patch:
      results['warnings'] = ['No values from test with patch, or none '
          'from test without patch.\n Output with patch:\n%s\n\nOutput without '
          'patch:\n%s' % (output_with_patch, output_without_patch)]
      return results

    mean_with_patch = self.m.math_utils.mean(values_with_patch)
    mean_without_patch = self.m.math_utils.mean(values_without_patch)

    stderr_with_patch = self.m.math_utils.standard_error(values_with_patch)
    stderr_without_patch = self.m.math_utils.standard_error(
        values_without_patch)

    profiler_with_patch = cloud_links_with_patch['profiler']
    profiler_without_patch = cloud_links_without_patch['profiler']

    # Calculate the % difference in the means of the 2 runs.
    relative_change = None
    std_err = None
    if mean_with_patch and values_with_patch:
      relative_change = self.m.math_utils.relative_change(
          mean_without_patch, mean_with_patch) * 100
      std_err = self.m.math_utils.pooled_standard_error(
          [values_with_patch, values_without_patch])

    if relative_change is not None and std_err is not None:
      data = [
          ['Revision', 'Mean', 'Std.Error'],
          ['Patch', str(mean_with_patch), str(stderr_with_patch)],
          ['No Patch', str(mean_without_patch), str(stderr_without_patch)]
      ]
      results['change'] = relative_change
      results['std_err'] = std_err
      results['result'] = _pretty_table(data)

    profiler_links = []
    if profiler_with_patch and profiler_without_patch:
      for i in xrange(len(profiler_with_patch)):  # pragma: no cover
        profiler_links.append({
          'title': '%s[%d]' % (labels.get('profiler_link1'), i),
          'link': profiler_with_patch[i]
        })
      for i in xrange(len(profiler_without_patch)):  # pragma: no cover
        profiler_links.append({
          'title': '%s[%d]' % (labels.get('profiler_link2'), i),
          'link': profiler_without_patch[i]
        })
    results['profiler_links'] = profiler_links

    return results

  def _get_build_url(self):
    properties = self.m.properties
    bot_url = properties.get('buildbotURL',
                             'http://build.chromium.org/p/chromium/')
    builder_name = urllib.quote(properties.get('buildername', ''))
    builder_number = str(properties.get('buildnumber', ''))
    return '%sbuilders/%s/builds/%s' % (bot_url, builder_name, builder_number)


  def parse_values(self, results_a, results_b, metric, output_format, **kwargs):
    """Parse the values for a given metric for the given results.

    This is meant to be used by tryjobs with a metric."""
    if not metric:
      return None, None

    results_index = None
    if output_format == 'buildbot':
      results_index = 'stdout_paths'
    elif output_format == 'chartjson':
      results_index = 'chartjson_paths'
    elif output_format == 'valueset':
      results_index = 'valueset_paths'
    else:  # pragma: no cover
      raise self.m.step.StepFailure('Unsupported format: ' + output_format)

    files_a = ','.join(map(str, results_a[results_index]))
    files_b = ','.join(map(str, results_b[results_index]))

    # Apply str to files to constrain cmdline args to ascii, as this used to
    # break when unicode things were passed instead.
    args = [files_a, files_b, str(metric), '--' + output_format]
    script = self.m.path['catapult'].join(
        'tracing', 'bin', 'compare_samples')
    result = self.m.python(
        'Parse metric values',
        script=script,
        args=args,
        stdout=self.m.json.output(),
        step_test_data=lambda: self.m.json.test_api.output_stream(
            {'sampleA':[1, 1, 1], 'sampleB':[9, 9, 9]}),
        **kwargs).stdout

    sample_a = result.get('sampleA', [])
    sample_b = result.get('sampleB', [])
    return sample_a, sample_b


def _validate_perf_config(config_contents, required_parameters):
  """Validates the perf config file contents.

  This is used when we're doing a perf try job, the config file is called
  run-perf-test.cfg by default.

  The parameters checked are the required parameters; any additional optional
  parameters won't be checked and validation will still pass.

  Args:
    config_contents: A config dictionary.
    required_parameters: List of parameter names to confirm in config.

  Returns:
    True if valid.
  """
  for parameter in required_parameters:
    if not config_contents.get(parameter):
      return False
    value = config_contents[parameter]
    if not value or not isinstance(value, basestring):  # pragma: no cover
      return False

  return True


def _pretty_table(data):
  results = []
  for row in data:
    results.append(('%-12s' * len(row) % tuple(row)).rstrip())
  return '\n'.join(results)


def _modify_upload_bucket(test_cfg, is_public):
  bucket = 'public' if is_public else 'private'
  new_arg = '--upload-bucket=' + bucket
  command = test_cfg.get('command')

  if not '--upload-bucket' in command:
    command = '%s %s' % (command, new_arg)
  else:
    out_dir_regex = re.compile(
        r"--upload-bucket[= ](?P<path>([a-zA-Z]+))")
    command = out_dir_regex.sub(new_arg, command)
  test_cfg.update({'command': command})


def _prepend_src_to_path_in_command(test_cfg):
  command_to_run = []
  for v in test_cfg.get('command').split():
    if v in ['./tools/perf/run_benchmark',
             'tools/perf/run_benchmark',
             'tools\\perf\\run_benchmark']:
      v = 'src/tools/perf/run_benchmark'
    command_to_run.append(v)
  test_cfg.update({'command': ' '.join(command_to_run)})


def _output_format(command):
  """Determine the output format for a given command."""
  if 'chartjson' in command:
    return 'chartjson'
  elif 'valueset' in command:
    return 'valueset'
  return 'buildbot'
