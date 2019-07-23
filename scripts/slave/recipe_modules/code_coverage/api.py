# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import re

from recipe_engine import recipe_api

_DEFAULT_BUCKET_NAME = 'code-coverage-data'

# Name of the file to store the component map.
_COMPONENT_MAPPING_FILE_NAME = 'component_mapping_path.json'

# Name of the file to store the line number mapping from bot to Gerrit.
_BOT_TO_GERRIT_LINE_NUM_MAPPING_FILE_NAME = (
    'bot_to_gerrit_line_num_mapping.json')

# Set of valid extensions for source files that use Clang.
_EXTENSIONS_OF_SOURCE_FILES_SUPPORTED_BY_CLANG = set([
    '.mm', '.S', '.c', '.hh', '.cxx', '.hpp', '.cc', '.cpp', '.ipp', '.h', '.m',
    '.hxx'
])

# Map exclude_sources property value to files that are to be excluded from
# coverage aggregates.
_EXCLUDE_SOURCES = {
    'all_test_files': r'.*test.*',
}


class CodeCoverageApi(recipe_api.RecipeApi):
  """This module contains apis to generate code coverage data."""

  def __init__(self, properties, *args, **kwargs):
    super(CodeCoverageApi, self).__init__(*args, **kwargs)
    # A single temporary directory to contain the profile data for all targets
    # in the build.
    self._base_profdata_dir = None
    # Temp dir for report.
    self._report_dir = None
    # Temp dir for metadata
    self._metadata_dir = None
    # Maps step names to subdirectories of the above.
    self._profdata_dirs = {}
    # When set, subset of source files to include in the coverage report.
    self._affected_source_files = None
    # When set, indicates that current context is per-cl coverage for try jobs.
    self._is_per_cl_coverage = False
    # The location of the scripts used to merge code coverage data (as opposed
    # to test results).
    self._merge_scripts_location = None
    # The map of gn args in args.gn file.
    self._gn_args = {}
    # The bucket to which code coverage data should be uploaded.
    self._gs_bucket = properties.gs_bucket or _DEFAULT_BUCKET_NAME

  @staticmethod
  def _dir_name_for_step(step_name):
    """Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to underscores.

    Adapted from:
    https://stackoverflow.com/questions/295135/turn-a-string-into-a-valid-filename

    Args:
      step_name (str): the name of the step to use.
    """
    value = re.sub('[^\w\s]', '', step_name).strip().lower()
    value = re.sub('[-\s]+', '_', value)
    return value

  @property
  def gn_args(self):
    if not self._gn_args and self.m.path.exists(
        self.m.chromium.output_dir.join('args.gn')):
      # TODO(yliuyliu): find more reliable way to get gn args.
      content = self.m.gn.get_args(self.m.chromium.output_dir)
      self._gn_args = self.m.gn.parse_gn_args(content)
    return self._gn_args

  @property
  def is_clang_coverage(self):
    return (self.m.gclient.c and self.m.gclient.c.solutions and
            'checkout_clang_coverage_tools' in self.m.gclient.c.solutions[0]
            .custom_vars)

  @property
  def is_java_coverage(self):
    return 'jacoco_coverage' in self.gn_args and self.gn_args[
        'jacoco_coverage'] == 'true'

  @property
  def merge_scripts_location(self):
    if not self._merge_scripts_location:  # pragma: no cover
      self._merge_scripts_location = self.m.chromium_checkout.working_dir.join(
          'src', 'testing', 'merge_scripts', 'code_coverage')
    return self._merge_scripts_location

  @property
  def step_merge_script(self):
    """Returns the script that merges indexed profiles from multiple targets."""
    return self.merge_scripts_location.join('merge_steps.py')

  @property
  def raw_profile_merge_script(self):
    """Returns the location of a script that merges raw profiles from shards.

    This is intended to be passed to the swarming recipe module to be called
    upon completion of the shards.
    """
    return self.merge_scripts_location.join('merge_results.py')

  def _llvm_exec(self, name):
    return self.m.path['checkout'].join('third_party', 'llvm-build',
                                        'Release+Asserts', 'bin', name)

  @property
  def profdata_executable(self):
    """Returns the path to the llvm-profdata executable."""
    return self._llvm_exec('llvm-profdata')

  @property
  def cov_executable(self):
    """Returns the path to the llvm-cov executable."""
    return self._llvm_exec('llvm-cov')

  @property
  def report_dir(self):
    """A temporary directory to save a report to. Created on first access."""
    if not self._report_dir:
      self._report_dir = self.m.path.mkdtemp()
    return self._report_dir

  @property
  def metadata_dir(self):
    """A temporary directory for the metadata. Created on first access."""
    if not self._metadata_dir:
      self._metadata_dir = self.m.path.mkdtemp()
    return self._metadata_dir

  def _get_source_exclusion_pattern(self):
    if 'exclude_sources' in self.m.properties:
      return _EXCLUDE_SOURCES.get(self.m.properties['exclude_sources'])
    return []

  def profdata_dir(self, step_name=None):
    """Ensures a directory exists for writing the step-level merged profdata.

    Args:
      step_name (str): The name of the step for the target whose profile we'll
          save in in this dir. None for getting the parent directory to contain
          the dirs for all steps.
    """
    # Create the parent directory when first needed.
    if not self._base_profdata_dir:
      self._base_profdata_dir = self.m.path.mkdtemp()

    if not step_name:
      return self._base_profdata_dir

    if step_name in self._profdata_dirs:
      return self._profdata_dirs[step_name]

    new_dir = self._base_profdata_dir.join(self._dir_name_for_step(step_name))
    self.m.file.ensure_directory('ensure profdata dir for %s' % step_name,
                                 new_dir)
    self._profdata_dirs[step_name] = new_dir
    return new_dir

  @property
  def using_coverage(self):
    """Checks if the current build is running coverage-instrumented targets."""
    # TODO(crbug.com/896751): Implement a cleaner way to determine if the recipe
    # is using code coverage instrumentation.
    return self.is_clang_coverage or self.is_java_coverage

  def _get_binaries(self, tests):
    """Returns paths to the binary for the given test objects.

    By default, use the name of the target as the binary.
    """
    # TODO(crbug.com/899974): Implement a sturdier approach that also works in
    # separate builder-tester setup.
    binaries = []
    for t in tests:
      # There are a number of local isolated scripts such as
      # check_static_initializers, checkdeps, checkperms etc. that introduce
      # extra complexitites, meawhile, it's still unclear if there is any value
      # in collecting code coverage data for them. So, for simplicity, skip
      # tests that don't run on swarming for now.
      if not t.runs_on_swarming:
        continue

      target = t.isolate_target
      # TODO(crbug.com/914213): Remove webkit_layout_tests reference.
      patterns = [
          # Following are scripts based tests that don't build any binaries.
          ['blink_python_tests', None],
          ['grit_python_unittests', None],
          ['metrics_python_tests', None],
          ['telemetry_gpu_unittests', None],
          ['devtools_closure_compile', None],
          ['devtools_eslint', None],

          # Following are mappings from isolate target names to binary names.
          ['telemetry_gpu_integration_test', 'chrome'],
          ['telemetry_unittests', 'chrome'],
          ['telemetry_perf_unittests', 'chrome'],
          ['chromedriver_py_tests', 'chrome'],
          ['chromedriver_replay_unittests', 'chrome'],
          ['chrome_all_tast_tests', 'chrome'],
          ['cros_browser_sanity_test', 'chrome'],
          ['xr_browser_tests', 'xr_browser_tests_binary'],
          ['content_shell_crash_test', 'content_shell'],
          ['.*webkit_layout_tests', 'content_shell'],
          ['.*blink_web_tests', 'content_shell'],
          ['.*_ozone', target[:-len('_ozone')]],
          ['.*', target],
      ]
      for pattern, binary in patterns:
        if re.match(pattern, target):
          if binary is not None:
            binaries.append(self.m.chromium.output_dir.join(binary))

          break

    return list(set(binaries))  # Remove duplicates.

  def _filter_source_file(self, file_paths):
    """Fitlers source files with valid extensions.

    Set of valid extensions is defined in:
      _EXTENSIONS_OF_SOURCE_FILES_SUPPORTED_BY_CLANG.

    Args:
      file_paths: A list of file paths relative to the checkout path.

    Returns:
      A sub-list of the input with valid extensions.
    """
    source_files = []
    for file_path in file_paths:
      if any([
          file_path.endswith(extension)
          for extension in _EXTENSIONS_OF_SOURCE_FILES_SUPPORTED_BY_CLANG
      ]):
        source_files.append(file_path)

    return source_files

  def instrument(self, affected_files):
    """Saves source paths to generate coverage instrumentation for to a file.

    Args:
      affected_files (list of str): paths to the files we want to instrument,
          relative to the checkout path.
    """
    self._is_per_cl_coverage = True

    self.m.file.ensure_directory(
        'create .clang-coverage',
        self.m.path['checkout'].join('.clang-coverage'))
    self._affected_source_files = self._filter_source_file(affected_files)
    return self.m.python(
        'save paths of affected files',
        self.resource('write_paths_to_instrument.py'),
        args=[
            '--write-to',
            self.m.path['checkout'].join('.clang-coverage',
                                         'files_to_instrument.txt'),
            '--src-path',
            self.m.path['checkout'],
            '--build-path',
            self.m.chromium.output_dir,
        ] + self._affected_source_files,
        stdout=self.m.raw_io.output_text(add_output_log=True))

  def process_coverage_data(self, tests):
    """Processes the coverage data for html report or metadata.

    Args:
      tests (list of self.m.chromium_tests.stepsl.Test): A list of test objects
          whose binaries we are to create a coverage report for.
    """
    if self.is_clang_coverage:
      self.process_clang_coverage_data(tests)

    if self.is_java_coverage:
      self.process_java_coverage_data()

  def process_clang_coverage_data(self, tests):
    """Processes the clang coverage data for html report or metadata.

    Args:
      tests (list of self.m.chromium_tests.stepsl.Test): A list of test objects
          whose binaries we are to create a coverage report for.
    """
    if not self._profdata_dirs:  # pragma: no cover.
      return

    with self.m.step.nest('process clang code coverage data'):
      if self._is_per_cl_coverage and not self._affected_source_files:
        self.m.python.succeeding_step(
            'skip processing because no source file is changed', '')
        return

      try:
        merged_profdata = self._merge_profdata()
        self._surface_merging_errors()
        binaries = self._get_binaries(tests)
        binaries = self._get_binaries_with_valid_coverage_data_on_trybot(
            binaries, merged_profdata)

        if not binaries:
          self.m.python.succeeding_step(
              'skip processing because no data is found', '')
          return
        self._generate_and_upload_metadata(binaries, merged_profdata)
        self._generate_and_upload_html_report_on_trybot(binaries,
                                                        merged_profdata)
      except self.m.step.StepFailure:
        self.m.step.active_result.presentation.properties[
            'process_coverage_data_failure'] = True

        if not self._is_per_cl_coverage:
          # Do not raise coverage steps exception for per-cl coverage because
          # per-cl coverage is integrated into Chromium try jobs, coverage steps
          # are expected to be non-fatal.
          raise

  def process_java_coverage_data(self, **kwargs):
    """Generates metadata and JaCoCo HTML report to upload to storage bucket.

    Generates Java coverage metadata and JaCoCo HTML report by scripts, and
    uploads them to the code-coverage-data storage bucket.

    Args:
      **kwargs: Kwargs for python and gsutil steps.
    """
    coverage_dir = self.m.chromium.output_dir.join('coverage')

    with self.m.step.nest('process java coverage'):
      component_mapping_path = self._generate_component_mapping()
      args = [
          '--src-path',
          self.m.path['checkout'],
          '--output-dir',
          coverage_dir,
          '--coverage-dir',
          coverage_dir,
          '--sources-json-dir',
          self.m.chromium.output_dir,
          '--component-mapping-path',
          component_mapping_path,
      ]
      self.m.python(
          'Generate Java coverage metadata',
          self.resource('generate_coverage_metadata_for_java.py'),
          args=args,
          infra_step=True,
          **kwargs)
      self.m.gsutil.upload(
          source=coverage_dir.join('all.json.gz'),
          bucket=self._gs_bucket,
          dest=self._compose_gs_path_for_coverage_data(
              'java_metadata/all.json.gz'),
          name='Upload JSON metadata',
          link_name='Coverage metadata',
          **kwargs)

      jacoco_html_report_dir = coverage_dir.join('coverage_html')
      self.m.python(
          'Generate JaCoCo HTML report',
          self.m.path['checkout'].join('build', 'android',
                                       'generate_jacoco_report.py'),
          args=[
              '--format', 'html', '--coverage-dir', coverage_dir,
              '--sources-json-dir', self.m.chromium.output_dir, '--output-dir',
              jacoco_html_report_dir, '--cleanup'
          ],
          infra_step=True,
          **kwargs)
      # TODO(crbug/980592): Make HTML report display directly on cloud bucket.
      output_zip = coverage_dir.join('jacoco_html_report.zip')
      self.m.zip.directory(
          step_name='Zip generated JaCoCo HTML report files',
          directory=jacoco_html_report_dir,
          output=output_zip)
      self.m.gsutil.upload(
          source=output_zip,
          bucket=self._gs_bucket,
          dest=self._compose_gs_path_for_coverage_data(
              'java_html_report/jacoco_html_report.zip'),
          link_name='JaCoCo HTML report',
          name='Upload zipped JaCoCo HTML report',
          **kwargs)

  def _merge_profdata(self):
    """Merges the profdata generated by each step to a single profdata."""
    merged_profdata = self.profdata_dir().join('merged.profdata')
    self.m.python(
        'merge profile data for %d tests' % len(self._profdata_dirs),
        self.step_merge_script,
        args=[
            '--input-dir',
            self.profdata_dir(),
            '--output-file',
            merged_profdata,
            '--llvm-profdata',
            self.profdata_executable,
        ])

    gs_path = self._compose_gs_path_for_coverage_data('merged.profdata')
    upload_step = self.m.gsutil.upload(
        merged_profdata,
        self._gs_bucket,
        gs_path,
        link_name=None,
        name='upload merged.profdata')
    upload_step.presentation.links['merged.profdata'] = (
        'https://storage.cloud.google.com/%s/%s' % (self._gs_bucket, gs_path))
    upload_step.presentation.properties['merged_profdata_gs_path'] = gs_path

    return merged_profdata

  # TODO(crbug.com/929769): Remove this method when the fix is landed upstream.
  def _get_binaries_with_valid_coverage_data_on_trybot(self, binaries,
                                                       profdata_path):
    """Gets binaries with valid coverage data.

    llvm-cov bails out with error message "No coverage data found" if an
    included binary does not exercise any instrumented file. The long-term
    solution should be making llvm-cov being able to proceed by ignoring the
    binaries without coverage data, however, for short-term, this method
    implements a solution to filter out binaries without coverage data by trying
    to invoke llvm-cov on each binary and decide if there is coverage data based
    on the return code and error message.

    This method is expected to run fast for per-cl coverage because only a small
    number of files are instrumented.

    Args:
      binaryes (list): A list of absolute paths to binaries.
      profdata_path (str): Path to the merged profdata file.

    Returns:
      A list of absolute paths to the binaries with valid coverage data.
    """
    if not (self.m.buildbucket.build.builder.bucket == 'try' and
            self._is_per_cl_coverage and self._affected_source_files):
      # Only gets binaries with valid coverage data for per-cl coverage.
      return binaries

    args = [
        '--profdata-path', profdata_path, '--llvm-cov', self.cov_executable,
        '--output-json',
        self.m.json.output()
    ]

    args.extend(binaries)
    step_result = self.m.python(
        'filter binaries with valid data for %s binaries' % len(binaries),
        self.resource('get_binaries_with_valid_coverage_data.py'),
        args=args,
        step_test_data=lambda: self.m.json.test_api.output([
            '/path/to/base_unittests',
            '/path/to/content_shell',]))
    return step_result.json.output

  def _generate_and_upload_html_report_on_trybot(self, binaries, profdata_path):
    """Generate html coverage report for the given binaries.

    Produce a coverage report for the instrumented test targets and upload to
    the appropriate bucket.
    """
    if not (self.m.buildbucket.build.builder.bucket == 'try' and
            self._is_per_cl_coverage and self._affected_source_files):
      # Only upload html report for CQ coverage bots.
      return

    args = [
        '--report-directory', self.report_dir, '--profdata-path', profdata_path,
        '--llvm-cov', self.cov_executable, '--binaries'
    ]
    args.extend(binaries)
    args.append('--sources')
    args.extend(
        [self.m.path['checkout'].join(s) for s in self._affected_source_files])

    self.m.python(
        'generate html report for %d tests' % len(self._profdata_dirs),
        self.resource('make_report.py'),
        args=args)

    html_report_gs_path = self._compose_gs_path_for_coverage_data('html_report')
    upload_step = self.m.gsutil.upload(
        self.report_dir,
        self._gs_bucket,
        html_report_gs_path,
        link_name=None,
        args=['-r'],
        multithreaded=True,
        name='upload html report')
    upload_step.presentation.links['html report'] = (
        'https://storage.cloud.google.com/%s/%s/index.html' %
        (self._gs_bucket, html_report_gs_path))

  def shard_merge(self, step_name, additional_merge=None):
    """Returns a merge object understood by the swarming module.

    See the docstring for the `merge` parameter of api.chromium_swarming.task.

    |additional_merge| is an additional merge script. This will be invoked from
    the clang coverage merge script.
    """
    new_merge = {
        'script':
            self.raw_profile_merge_script,
        'args': [
            '--profdata-dir',
            self.profdata_dir(step_name),
            '--llvm-profdata',
            self.profdata_executable,
        ],
    }
    if self.is_java_coverage:
      new_merge['args'].extend([
          '--java-coverage-dir',
          self.m.chromium.output_dir.join('coverage'),
          '--jacococli-path',
          self.m.path['checkout'].join('third_party', 'jacoco', 'lib',
                                       'jacococli.jar'),
          '--merged-jacoco-filename',
          self._dir_name_for_step(step_name),
      ])
    if additional_merge:
      new_merge['args'].extend([
          '--additional-merge-script',
          additional_merge['script'],
      ])
      if 'args' in additional_merge:
        new_merge['args'].extend([
            '--additional-merge-script-args',
            self.m.json.dumps(additional_merge['args'])
        ])

    return new_merge

  def _compose_gs_path_for_coverage_data(self, data_type):
    build = self.m.buildbucket.build
    if build.input.gerrit_changes:
      # Assume that there is only one gerrit patchset which is true for
      # Chromium CQ in practice.
      gerrit_change = build.input.gerrit_changes[0]
      return 'presubmit/%s/%s/%s/%s/%s/%s/%s' % (
          gerrit_change.host,
          gerrit_change.change,  # Change id is unique in a Gerrit host.
          gerrit_change.patchset,
          build.builder.bucket,
          build.builder.builder,
          build.id,
          data_type,
      )
    else:
      commit = build.input.gitiles_commit
      assert commit is not None, 'No gitiles commit'
      return 'postsubmit/%s/%s/%s/%s/%s/%s/%s' % (
          commit.host,
          commit.project,
          commit.id,  # A commit HEX SHA1 is unique in a Gitiles project.
          build.builder.bucket,
          build.builder.builder,
          build.id,
          data_type,
      )

  def _generate_component_mapping(self):
    """Generates the mapping from crbug components to directories."""
    component_mapping = self.m.path.mkdtemp().join(_COMPONENT_MAPPING_FILE_NAME)
    command_path = self.m.path['checkout'].join('tools', 'checkteamtags',
                                                'extract_components.py')
    command_parts = [command_path, '-o', component_mapping]
    self.m.step(
        'Run component extraction script to generate mapping',
        command_parts,
        stdout=self.m.raw_io.output_text(add_output_log=True))
    return component_mapping

  def _generate_and_upload_metadata(self, binaries, profdata_path):
    """Generates the coverage info in metadata format."""
    args = [
        '--src-path',
        self.m.path['checkout'],
        '--output-dir',
        self.metadata_dir,
        '--profdata-path',
        profdata_path,
        '--llvm-cov',
        self.cov_executable,
        '--binaries',
    ]
    args.extend(binaries)
    if self._is_per_cl_coverage:
      args.append('--sources')
      args.extend([
          self.m.path['checkout'].join(s) for s in self._affected_source_files
      ])

      # In order to correctly display the (un)covered line numbers on Gerrit.
      # Per-cl metadata's line numbers need to be rebased because the base
      # revision of the change in this build is different from the one on
      # Gerrit.
      self._generate_line_number_mapping_from_bot_to_gerrit(
          self._affected_source_files)
      args.extend([
          '--diff-mapping-path',
          self.metadata_dir.join(_BOT_TO_GERRIT_LINE_NUM_MAPPING_FILE_NAME)
      ])
    else:
      pattern = self._get_source_exclusion_pattern()
      if pattern:
        args.extend(['--exclusion-pattern', pattern])

      args.extend(
          ['--component-mapping-path',
           self._generate_component_mapping()])

    try:
      self.m.python(
          'generate metadata for %d tests' % len(self._profdata_dirs),
          self.resource('generate_coverage_metadata.py'),
          args=args,
          venv=True)
    finally:
      gs_path = self._compose_gs_path_for_coverage_data('metadata')
      upload_step = self.m.gsutil.upload(
          self.metadata_dir,
          self._gs_bucket,
          gs_path,
          link_name=None,
          args=['-r'],
          multithreaded=True,
          name='upload coverage metadata')
      upload_step.presentation.links['metadata report'] = (
          'https://storage.cloud.google.com/%s/%s/index.html' % (
              self._gs_bucket, gs_path))
      upload_step.presentation.properties['coverage_metadata_gs_path'] = gs_path
      upload_step.presentation.properties['coverage_gs_bucket'] = (
          self._gs_bucket)

  def _generate_line_number_mapping_from_bot_to_gerrit(self, source_files):
    """Generates the line number mapping from bot to Gerrit.

    Args:
      source_files: List of source files to generate line number mapping for,
                    the paths are relative to the checkout path.
    """
    gerrit_change = self.m.buildbucket.build.input.gerrit_changes[0]
    local_to_gerrit_diff_mapping_file = self.metadata_dir.join(
        _BOT_TO_GERRIT_LINE_NUM_MAPPING_FILE_NAME)
    self.m.python(
        'generate line number mapping from bot to Gerrit',
        self.resource('rebase_line_number_from_bot_to_gerrit.py'),
        args=[
            '--host', gerrit_change.host, '--project', gerrit_change.project,
            '--change', gerrit_change.change, '--patchset',
            gerrit_change.patchset, '--src-path', self.m.path['checkout'],
            '--output-file', local_to_gerrit_diff_mapping_file
        ] + source_files,
        stdout=self.m.json.output())

  def _surface_merging_errors(self):
    test_data = {
        "failed profiles": {
            "browser_tests": ["/tmp/1/default-123.profraw"]
        },
        "total": 1
    }
    step_result = self.m.python(
        'Finding merging errors',
        self.resource('load_merge_errors.py'),
        args=['--root-dir', self.profdata_dir()],
        step_test_data=lambda: self.m.json.test_api.output_stream(test_data),
        stdout=self.m.json.output())

    if step_result.stdout:
      step_result.presentation.text = 'Found invalid profraw files'
      step_result.presentation.properties[
          'bad_coverage_profiles'] = step_result.stdout
