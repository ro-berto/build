# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import re
import sys

from recipe_engine import recipe_api

from RECIPE_MODULES.build import chromium_swarming

from . import constants


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
    # When set, subset of source files to include in the coverage report.
    self._affected_source_files = []
    # When set, indicates that current context is per-cl coverage for try jobs.
    self._is_per_cl_coverage = False
    # The list of profdata gs paths to be uploaded.
    self._merged_profdata_gs_paths = []
    # The list of coverage metadata gs paths to be uploaded.
    self._coverage_metadata_gs_paths = []
    # The list of mimic builder names to be uploaded.
    self._mimic_builder_names = []
    # The bucket to which code coverage data should be uploaded.
    self._gs_bucket = properties.gs_bucket or constants.DEFAULT_BUCKET_NAME
    # List of test types to run in a builder. By default, it runs overall
    # coverage. This is only used in Clang coverage at present.
    self._test_types = properties.coverage_test_types or ['overall']
    # The key in constants.EXCLUDE_SOURCES to get corresponding excluded file
    # pattern.
    self._exclude_sources_key = properties.coverage_exclude_sources
    # Current test type that's being processed.
    self._current_processing_test_type = 'overall'
    # When set True, Clang coverage is enabled.
    self._use_clang_coverage = properties.use_clang_coverage
    # When set True, Java coverage is enabled.
    self._use_java_coverage = properties.use_java_coverage
    # When set True, JavaScript coverage is enabled.
    self._use_javascript_coverage = properties.use_javascript_coverage
    # Platform for which this build is running.
    self._platform = None
    # Determines whether a component mapping should be used for non-per-cl
    # coverage runs.
    self._include_component_mapping = True

  @property
  def use_clang_coverage(self):
    return self._use_clang_coverage

  @property
  def use_java_coverage(self):
    return self._use_java_coverage

  @property
  def use_javascript_coverage(self):
    return self._use_javascript_coverage

  @property
  def platform(self):
    if not self._platform:
      self._platform = self.m.chromium.c.TARGET_PLATFORM
    return self._platform

  @property
  def cov_executable(self):
    """Returns the path to the llvm-cov executable."""
    return self.m.profiles.llvm_exec_path('llvm-cov')

  @property
  def report_dir(self):
    """A temporary directory to save a report to. Created on first access."""
    if not self._report_dir:
      self._report_dir = self.m.path.mkdtemp()
    return self._report_dir

  @property
  def metadata_dir(self):
    """A temporary directory for the metadata.

    It's a temporary directory with a sub directory named in current test type.
    Temp dir is created on first access to this property. Subdirs are created
    on first access when processing each test type.
    """
    if not self._metadata_dir:
      self._metadata_dir = self.m.path.mkdtemp()
    metadata_test_type_dir = self._metadata_dir.join(
        self._current_processing_test_type)
    self.m.file.ensure_directory(
        'ensure metadata dir for %s tests' % self._current_processing_test_type,
        metadata_test_type_dir)
    return metadata_test_type_dir

  def _compose_current_mimic_builder_name(self):
    """Current mimic builder name composed from the test type being processed.

    If currently processing overall coverage data, return real builder name.
    Otherwise, return {real_builder_name}_{current_test_type}.
    """
    suffix = '' if self._current_processing_test_type == 'overall' else (
        '_' + self._current_processing_test_type)
    return self.m.buildbucket.build.builder.builder + suffix

  @property
  def using_coverage(self):
    """Checks if the current build is running coverage-instrumented targets."""
    return self.use_clang_coverage or self.use_java_coverage \
           or self.use_javascript_coverage

  def _get_binaries(self, tests):
    """Returns paths to the binary for the given test objects.

    By default, use the name of the target as the binary.
    """
    # TODO(crbug.com/899974): Implement a sturdier approach that also works in
    # separate builder-tester setup.
    binaries = set()

    # Android platform needs to use unstripped files for llvm-cov.
    # The unstripped artifacts will be generated under lib.unstripped/ or
    # exe.unstripped/.
    if self.platform == 'android':
      step_result = self.m.python(
          'Get all Android unstripped artifacts paths',
          self.resource('get_android_unstripped_paths.py'),
          args=[
              '--chromium-output-dir', self.m.chromium.output_dir,
              '--output-json',
              self.m.json.output()
          ])
      android_paths = step_result.json.output

    for t in tests:
      # There are a number of local isolated scripts such as
      # check_static_initializers, checkdeps, checkperms etc. that introduce
      # extra complexitites, meawhile, it's still unclear if there is any value
      # in collecting code coverage data for them. So, for simplicity, skip
      # tests that don't run on swarming for now.
      if not t.runs_on_swarming:
        continue

      target = t.isolate_target

      if not re.search(
          constants.TEST_TYPE_TO_TARGET_NAME_PATTERN_MAP[
              self._current_processing_test_type], target):
        continue

      patterns = [
          # Following are scripts based tests that don't build any binaries.
          ['blink_python_tests', None],
          ['extension_docserver_python_unittests', None],
          ['grit_python_unittests', None],
          ['metrics_python_tests', None],
          ['mojo_python_unittests', None],
          ['python3_smoketest', None],
          ['telemetry_gpu_unittests', None],

          # Following are mappings from isolate target names to binary names.
          ['telemetry_gpu_integration_test', 'chrome'],
          ['telemetry_unittests', 'chrome'],
          ['telemetry_perf_unittests', 'chrome'],
          ['chromedriver_py_tests', 'chrome'],
          ['chromedriver_replay_unittests', 'chrome'],
          ['chrome_all_tast_tests', 'chrome'],
          ['cros_browser_sanity_test', 'chrome'],
          ['webdriver_wpt_tests', 'chrome'],
          ['xr_browser_tests', 'xr_browser_tests_binary'],
          ['content_shell_crash_test', 'content_shell'],
          ['.*blink_web_tests', 'content_shell'],
          ['.*_ozone', target[:-len('_ozone')]],
          ['.*_eg2tests_module', 'ios_chrome_eg2tests'],
          ['.*', target],
      ]
      for pattern, binary in patterns:
        if not re.match(pattern, target):
          continue
        if binary is None:
          break

        if self.platform == 'android':
          so_library_name = 'lib' + binary + '__library.so'
          for android_path in android_paths:
            if android_path.endswith(binary) or android_path.endswith(
                so_library_name):
              binaries.add(android_path)
              break
        elif self.platform == 'ios':
          if binary == 'ios_web_view_inttests':
            binaries.add(
                self.m.chromium.output_dir.join('ChromeWebView.framework',
                                                'ChromeWebView'))
            break
          # Actual binary file is at {binary}.app/{binary} for iOS.
          binaries.add(self.m.chromium.output_dir.join(binary + '.app', binary))
        else:
          binaries.add(
              self.m.chromium.output_dir.join(
                  binary, platform_ext={'win': '.exe'}))

        break

    return sorted(binaries)


  def _filter_source_file(self, file_paths, extensions):
    """Filters source files with valid extensions.

    Args:
      file_paths: A list of file paths relative to the checkout path.
      extensions: A list of extensions to filter source files.

    Returns:
      A sub-list of the input with valid extensions.
    """
    source_files = []
    for file_path in file_paths:
      if any([file_path.endswith(extension) for extension in extensions]):
        source_files.append(file_path)

    return source_files

  def _validate_test_types(self):
    """Validates that test type to process in build is supported."""
    for test_type in self._test_types:
      if test_type not in constants.SUPPORTED_TEST_TYPES:
        raise Exception('Unsupported test type %s.' % test_type)

    if self._is_per_cl_coverage and len(self._test_types) > 1:
      raise Exception('Only one test type is supported for per-cl coverage '
          'but %d found in builder properties.' % len(self._test_types))

  def _set_builder_output_properties_for_uploads(self):
    """Sets the output property of the builder."""
    result = self.m.python.succeeding_step('Set builder output properties', '')
    result.presentation.properties['coverage_metadata_gs_paths'] = (
        self._coverage_metadata_gs_paths)
    result.presentation.properties['mimic_builder_names'] = (
        self._mimic_builder_names)
    result.presentation.properties['merged_profdata_gs_paths'] = (
        self._merged_profdata_gs_paths)
    result.presentation.properties['coverage_gs_bucket'] = (self._gs_bucket)
    result.presentation.properties['coverage_is_presubmit'] = (
        self._is_per_cl_coverage)

  def instrument(self, affected_files, output_dir=None):
    """Saves source paths to generate coverage instrumentation for to a file.

    Args:
      affected_files (list of str): paths to the files we want to instrument,
          relative to the checkout path.
    """
    if len(affected_files) > 200:
      # Skip instrumentation if there are too many files because:
      # 1. They cause problems such as crash due to too many cmd line arguments.
      # 2. These CLs typically does mechanial refactorings, and coverage
      #    information is useless.
      # 3. Has non-trivial performance implications in terms of CQ cycle time.
      affected_files = []
      self.m.python.succeeding_step(
          'skip instrumenting code coverage because >200 files are modified',
          '')

    if not output_dir:
      output_dir = self.m.chromium.output_dir

    self._is_per_cl_coverage = True

    if self.use_clang_coverage:
      self._affected_source_files = self._filter_source_file(
          affected_files, constants.TOOLS_TO_EXTENSIONS_MAP['clang'])
    elif self.use_java_coverage:
      self._affected_source_files = self._filter_source_file(
          affected_files, constants.TOOLS_TO_EXTENSIONS_MAP['jacoco'])

    self.m.file.ensure_directory('create .code-coverage',
                                 self.m.path['checkout'].join('.code-coverage'))
    self.m.python(
        'save paths of affected files',
        self.resource('write_paths_to_instrument.py'),
        args=[
            '--write-to',
            self.m.path['checkout'].join('.code-coverage',
                                         'files_to_instrument.txt'),
            '--src-path',
            self.m.path['checkout'],
            '--build-path',
            output_dir,
        ] + self._affected_source_files,
        stdout=self.m.raw_io.output_text(add_output_log=True))

  def process_coverage_data(self, tests):
    """Processes the coverage data for html report or metadata.

    Args:
      tests (list of steps.Test): A list of test objects
          whose binaries we are to create a coverage report for.
    """
    try:
      self._validate_test_types()
    except Exception as e:
      if self._is_per_cl_coverage:
        self.m.python.succeeding_step('skip processing because of an exception '
            'when validating test types to process: %s' % e.message, '')
      else:
        self.m.python.failing_step('Exception when validating test types to '
            'process: %s' % e.message, '')
      return

    if self._is_per_cl_coverage:
      unsupported_projects = self._get_unsupported_projects()
      if unsupported_projects:
        self.m.python.succeeding_step(
            'skip processing coverage data, project(s) %s is(are) unsupported' %
            unsupported_projects, '')
        return

    if self.use_clang_coverage:
      for test_type in self._test_types:
        self._current_processing_test_type = test_type
        self.process_clang_coverage_data(tests)

    if self.use_java_coverage:
      try:
        self.process_java_coverage_data()
      finally:
        self.m.python(
            'Clean up Java coverage files',
            self.resource('clean_up_java_coverage_files.py'),
            args=[
                '--sources-json-dir',
                self.m.chromium.output_dir,
                '--java-coverage-dir',
                self.m.chromium.output_dir.join('coverage'),
            ])

    if self.use_javascript_coverage:
      self.process_javascript_coverage_data()

    self._set_builder_output_properties_for_uploads()

  def _get_unsupported_projects(self):
    """If the build input has changes in unsupported projects, return them."""
    result = []
    for change in self.m.buildbucket.build.input.gerrit_changes:
      if (change.host,
          change.project) not in constants.SUPPORTED_PATCH_PROJECTS:
        result.append((change.host, change.project))
    return ', '.join('/'.join(p) for p in result)

  def _process_clang_coverage_data(self, tests=None, binaries=None):
    """Processes the clang coverage data for html report or metadata.

    Args:
      tests (list of steps.Test): A list of test objects
          whose binaries we are to create a coverage report for.
      binaries: A list of binaries for which coverage reports should be
          created.

      NOTE: Only one of the two above should be present.
    """
    assert (tests and not binaries) or (not tests and binaries), \
        'One of tests or binaries must be provided'
    if self._is_per_cl_coverage and not self._affected_source_files:
      self.m.python.succeeding_step(
          'skip processing coverage data because no source file changed', '')
      return

    if not self.m.profiles.profile_subdirs:  # pragma: no cover.
      self.m.python.succeeding_step(
          'skip processing coverage data because no profile data collected', '')
      return

    with self.m.step.nest(
        'process clang code coverage data for %s test coverage' %
        self._current_processing_test_type) as processing_step:
      try:
        merged_profdata = self._merge_and_upload_profdata()
        if not merged_profdata:
          self.m.python.succeeding_step(
              'skip processing because no profdata was generated', '')
          return

        merge_errors = self.m.profiles.find_merge_errors()
        if merge_errors.stdout:
          result = self.m.step.active_result
          result.presentation.text = 'Found invalid profraw files'
          result.presentation.properties['merge errors'] = merge_errors.stdout

        if not binaries:
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
      except:  # pylint: disable=bare-except
        self.m.step.active_result.presentation.properties[
            'process_coverage_data_failure'] = True

        if self._is_per_cl_coverage:
          # Do not raise coverage steps exception for per-cl coverage because
          # per-cl coverage is integrated into Chromium try jobs, coverage steps
          # are expected to be non-fatal.
          processing_step.logs['error'] = '\n'.join(
              str(x) for x in sys.exc_info())
        else:
          raise

  def process_clang_coverage_data(self, tests):
    """Processes the clang coverage data for html report or metadata.

    Args:
      tests (list of steps.Test): A list of test objects
          whose binaries we are to create a coverage report for.
    """
    self._process_clang_coverage_data(tests)

  def process_java_coverage_data(self, **kwargs):
    """Generates metadata and JaCoCo HTML report to upload to storage bucket.

    Generates Java coverage metadata and JaCoCo HTML report by scripts, and
    uploads them to the code-coverage-data storage bucket.

    Args:
      **kwargs: Kwargs for python and gsutil steps.
    """
    if self._is_per_cl_coverage and not self._affected_source_files:
      self.m.python.succeeding_step(
          'skip processing coverage data because no source file changed', '')
      return

    with self.m.step.nest('process java coverage'):
      try:
        coverage_dir = self.m.chromium.output_dir.join('coverage')
        args = [
            '--src-path',
            self.m.path['checkout'],
            '--output-dir',
            coverage_dir,
            '--coverage-dir',
            coverage_dir,
            '--sources-json-dir',
            self.m.chromium.output_dir,
        ]

        if self._is_per_cl_coverage:
          args.append('--source-files')
          args.extend(self._affected_source_files)
          self._generate_line_number_mapping_from_bot_to_gerrit(
              self._affected_source_files, coverage_dir)
          args.extend([
              '--diff-mapping-path',
              coverage_dir.join(
                  constants.BOT_TO_GERRIT_LINE_NUM_MAPPING_FILE_NAME),
          ])
        else:
          dir_metadata_path = self._generate_dir_metadata()
          args.extend([
              '--dir-metadata-path',
              dir_metadata_path,
          ])

        self.m.python(
            'Generate Java coverage metadata',
            self.resource('generate_coverage_metadata_for_java.py'),
            args=args,
            **kwargs)
        metadata_path = coverage_dir.join('all.json.gz')
        if not self.m.path.exists(metadata_path):
          self.m.python.succeeding_step(
              'skip processing because no metadata was generated', '')
          return

        gs_path = self._compose_gs_path_for_coverage_data('java_metadata')
        self.m.gsutil.upload(
            source=metadata_path,
            bucket=self._gs_bucket,
            dest='%s/all.json.gz' % gs_path,
            name='Upload JSON metadata',
            link_name='Coverage metadata',
            **kwargs)
        self._coverage_metadata_gs_paths.append(gs_path)
        self._mimic_builder_names.append(
            self._compose_current_mimic_builder_name())

        jacoco_html_report_dir = coverage_dir.join('coverage_html')
        self.m.python(
            'Generate JaCoCo HTML report',
            self.m.path['checkout'].join('build', 'android',
                                         'generate_jacoco_report.py'),
            args=[
                '--format', 'html', '--coverage-dir', coverage_dir,
                '--sources-json-dir', self.m.chromium.output_dir,
                '--output-dir', jacoco_html_report_dir, '--cleanup'
            ],
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
      except self.m.step.StepFailure:
        self.m.step.active_result.presentation.properties[
            'process_coverage_data_failure'] = True
        if not self._is_per_cl_coverage:
          # Do not raise coverage steps exception for per-cl coverage.
          raise

  def process_javascript_coverage_data(self):
    # TODO(benreich): Add support for per CL coverage.
    if self._is_per_cl_coverage:
      self.m.python.succeeding_step(
          'per cl coverage is not supported for javascript code coverage', '')
      return

    with self.m.step.nest('process javascript coverage'):
      try:
        dir_metadata_path = self._generate_dir_metadata()

        coverage_dir = self.m.chromium.output_dir.join('devtools_code_coverage')
        args = [
            '--src-path',
            self.m.path['checkout'],
            '--output-dir',
            coverage_dir,
            '--coverage-dir',
            coverage_dir,
            '--dir-metadata-path',
            dir_metadata_path,
        ]

        self.m.python(
            'Generate JavaScript coverage metadata',
            self.resource('generate_coverage_metadata_for_javascript.py'),
            args=args)
      except self.m.step.StepFailure:
        self.m.step.active_result.presentation.properties[
            'process_coverage_data_failure'] = True
        raise
      # TODO(benreich): Upload the coverage metadata to GCS.

  def _merge_and_upload_profdata(self):
    """Merges the profdata generated by each step to a single profdata.

    Returns:
      A path to the {test_type}-merged.profdata file if it exists, otherwise,
      None. One possible reason that profdata doesn't exist is that there might
      be no .profraw files to merge at all.
    """
    test_type = self._current_processing_test_type
    merged_profdata = self.m.profiles.profile_dir().join(
        '%s-merged.profdata' % test_type)

    # Input profdata in this step was named as {target_name}.profdata. This is
    # used for filtering profdata file of current test type.
    input_profdata_pattern = (
        "%s\.profdata" %
        constants.TEST_TYPE_TO_TARGET_NAME_PATTERN_MAP[test_type])
    self.m.profiles.merge_profdata(
        merged_profdata,
        profdata_filename_pattern=input_profdata_pattern,
        sparse=True)

    if not self.m.path.exists(merged_profdata):
      return None

    # The uploaded profdata file is named "merged.profdata" regardless of test
    # type, since test types are already distinguished in builder part of gs
    # path.
    gs_path = self._compose_gs_path_for_coverage_data('merged.profdata')
    upload_step = self.m.profiles.upload(
        self._gs_bucket, gs_path, merged_profdata, link_name=None)
    upload_step.presentation.links['merged.profdata'] = (
        'https://storage.cloud.google.com/%s/%s' % (self._gs_bucket, gs_path))
    self._merged_profdata_gs_paths.append(gs_path)
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
      binaries (list): A list of absolute paths to binaries.
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

    if self.platform == 'ios':
      args.extend(['--arch', 'x86_64'])

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

    if self.platform == 'ios':
      args.extend(['--arch', 'x86_64'])

    self.m.python(
        'generate html report for %s test coverage in %d tests'
        % (self._current_processing_test_type,
           len(self.m.profiles.profile_subdirs)),
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

  def shard_merge(self,
                  step_name,
                  target_name,
                  additional_merge=None,
                  skip_validation=False,
                  sparse=False):
    """Returns a merge object understood by the swarming module.

    See the docstring for the `merge` parameter of api.chromium_swarming.task.

    |additional_merge| is an additional merge script. This will be invoked from
    the clang coverage merge script.
    """
    args = [
        '--profdata-dir',
        self.m.profiles.profile_dir(step_name),
        '--llvm-profdata',
        self.m.profiles.llvm_profdata_exec,
        '--test-target-name',
        target_name,
    ]
    if skip_validation:
      args += [
          '--skip-validation',
      ]
    if sparse:
      args += [
          '--sparse',
      ]

    if self.use_java_coverage:
      args.extend([
          '--java-coverage-dir',
          self.m.chromium.output_dir.join('coverage'),
          '--jacococli-path',
          self.m.path['checkout'].join('third_party', 'jacoco', 'lib',
                                       'jacococli.jar'),
          '--merged-jacoco-filename',
          self.m.profiles.normalize(step_name),
      ])
    if self.use_javascript_coverage:
      args.extend([
          '--javascript-coverage-dir',
          self.m.chromium.output_dir.join('devtools_code_coverage'),
          '--merged-js-cov-filename',
          self.m.profiles.normalize(step_name),
      ])
    if self._is_per_cl_coverage:
      args.append('--per-cl-coverage')
    if additional_merge:
      args.extend([
          '--additional-merge-script',
          additional_merge.script,
      ])
      if additional_merge.args:
        args.extend([
            '--additional-merge-script-args',
            self.m.json.dumps(additional_merge.args)
        ])

    return chromium_swarming.MergeScript(
        script=self.m.profiles.merge_results_script, args=args)

  def _compose_gs_path_for_coverage_data(self, data_type):
    build = self.m.buildbucket.build
    mimic_builder_name = self._compose_current_mimic_builder_name()
    if build.input.gerrit_changes:
      # Assume that there is only one gerrit patchset which is true for
      # Chromium CQ in practice.
      gerrit_change = build.input.gerrit_changes[0]
      return 'presubmit/%s/%s/%s/%s/%s/%s/%s' % (
          gerrit_change.host,
          gerrit_change.change,  # Change id is unique in a Gerrit host.
          gerrit_change.patchset,
          build.builder.bucket,
          mimic_builder_name,
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
          mimic_builder_name,
          build.id,
          data_type,
      )

  def _generate_dir_metadata(self):
    """Extracts directory metadata, e.g. mapping to monorail component."""
    dir_metadata = self.m.path.mkdtemp().join(constants.DIR_METADATA_FILE_NAME)
    self.m.step('Extract directory metadata', [
        self.m.path['checkout'].join('third_party', 'depot_tools', 'dirmd'),
        'export', '-out', dir_metadata
    ])
    return dir_metadata

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
      args.extend(self._affected_source_files)

      # In order to correctly display the (un)covered line numbers on Gerrit.
      # Per-cl metadata's line numbers need to be rebased because the base
      # revision of the change in this build is different from the one on
      # Gerrit.
      self._generate_line_number_mapping_from_bot_to_gerrit(
          self._affected_source_files, self.metadata_dir)
      args.extend([
          '--diff-mapping-path',
          self.metadata_dir.join(
              constants.BOT_TO_GERRIT_LINE_NUM_MAPPING_FILE_NAME)
      ])
    else:
      pattern = (
          constants.EXCLUDE_SOURCES.get(self._exclude_sources_key)
          if self._exclude_sources_key else [])
      if pattern:
        args.extend(['--exclusion-pattern', pattern])

      if self._include_component_mapping:
        args.extend(['--dir-metadata-path', self._generate_dir_metadata()])

    if self.platform == 'ios':
      args.extend(['--arch', 'x86_64'])

    try:
      self.m.python(
          'generate metadata for %s test coverage in %d tests' %
          (self._current_processing_test_type,
           len(self.m.profiles.profile_subdirs)),
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
          'https://storage.cloud.google.com/%s/%s/index.html' %
          (self._gs_bucket, gs_path))
      self._coverage_metadata_gs_paths.append(gs_path)
      self._mimic_builder_names.append(
          self._compose_current_mimic_builder_name())

  def _generate_line_number_mapping_from_bot_to_gerrit(self, source_files,
                                                       output_dir):
    """Generates the line number mapping from bot to Gerrit.

    Args:
      source_files: List of source files to generate line number mapping for,
                    the paths are relative to the checkout path.
      output_dir: The output directory to store
                  constants.BOT_TO_GERRIT_LINE_NUM_MAPPING_FILE_NAME.
    """
    gerrit_change = self.m.buildbucket.build.input.gerrit_changes[0]
    local_to_gerrit_diff_mapping_file = output_dir.join(
        constants.BOT_TO_GERRIT_LINE_NUM_MAPPING_FILE_NAME)
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
