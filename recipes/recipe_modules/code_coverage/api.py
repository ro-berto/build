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
    # Absolute path to the file containing line number mappings from bot
    # version of files to gerrit version
    self._bot_to_gerrit_mapping_file = None

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

  @property
  def bot_to_gerrit_mapping_file(self):
    """Generates the line number mapping from bot to Gerrit.

    In order to correctly display the (un)covered line numbers on Gerrit.
    Per-cl metadata's line numbers need to be rebased because the base
    revision of the change in this build is different from the one on Gerrit.

    The mapping get's generated and stored on the first access to the property.
    """
    if not self._bot_to_gerrit_mapping_file:
      output_dir = self.m.path.mkdtemp()
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
          ] + self._affected_source_files,
          stdout=self.m.json.output())
      self._bot_to_gerrit_mapping_file = local_to_gerrit_diff_mapping_file
    return self._bot_to_gerrit_mapping_file

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
    return (self.use_clang_coverage or self.use_java_coverage or
            self.use_javascript_coverage)

  def set_is_per_cl_coverage(self, value):
    self._is_per_cl_coverage = value

  def get_required_build_output_files(self, tests):
    """Get required build output files necessary to run code coverage

    Args:
      tests (list(Test)): List of Test objects

    Returns:
      List of Paths to build output files
    """
    binary_paths = self.get_binaries(tests)
    files = [
        binary_path for binary_path in binary_paths
        if self.m.path.exists(binary_path)
    ]

    if self.platform == 'android':
      step_result = self.m.python(
          'Get jacoco and jar files for java coverage',
          self.resource('get_jacoco_and_jar_files_for_java.py'),
          args=[
              '--sources-json-dir', self.m.chromium.output_dir, '--output-json',
              self.m.json.output()
          ])
      paths = step_result.json.output

      files.extend([self.m.path.abs_to_path(f) for f in paths])

    return files

  def get_binaries(self, tests):
    """Returns paths to the binary for the given test objects.

    By default, use the name of the target as the binary.

    Args:
      tests (list(Test)): List of Test objects

    Returns:
      List of Paths to test binaries
    """
    # TODO(crbug.com/899974): Implement a sturdier approach that also works in
    # separate builder-tester setup.
    binaries = set()

    # Android and Fuchsia platform needs to use unstripped files for llvm-cov.
    # The unstripped artifacts will be generated under lib.unstripped/ or
    # exe.unstripped/.
    if self.platform in ('android', 'fuchsia'):
      step_result = self.m.python(
          'Get all unstripped artifacts paths',
          self.resource('get_unstripped_paths.py'),
          args=[
              '--chromium-output-dir', self.m.chromium.output_dir,
              '--output-json',
              self.m.json.output()
          ])
      unstripped_paths = step_result.json.output

    for t in tests:
      # There are a number of local isolated scripts such as
      # check_static_initializers, checkdeps, checkperms etc. that introduce
      # extra complexitites, meawhile, it's still unclear if there is any value
      # in collecting code coverage data for them. So, for simplicity, skip
      # tests that don't run on swarming for now.
      if not t.runs_on_swarming:
        continue

      target = t.isolate_target

      # Do not get the test binary if it does not correspond to test type.
      if (self.platform in constants.PLATFORM_TO_TARGET_NAME_PATTERN_MAP and
          not re.search(
              constants.PLATFORM_TO_TARGET_NAME_PATTERN_MAP[self.platform][
                  self._current_processing_test_type], target)):
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
          for unstripped_path in unstripped_paths:
            if unstripped_path.endswith(binary) or unstripped_path.endswith(
                so_library_name):
              binaries.add(self.m.path.abs_to_path(unstripped_path))
              break
        elif self.platform == 'fuchsia':
          exec_name = binary + '__exec'
          for unstripped_path in unstripped_paths:
            if unstripped_path.endswith(exec_name):
              binaries.add(self.m.path.abs_to_path(unstripped_path))
              break
        elif self.platform == 'ios':
          if binary == 'ios_web_view_inttests':
            binaries.add(
                self.m.chromium.output_dir.join('ChromeWebView.framework',
                                                'ChromeWebView'))
            break
          # Actual binary file is at {binary}.app/{binary} for iOS.
          binaries.add(self.m.chromium.output_dir.join(binary + '.app', binary))
        elif self.platform == 'win':
          binaries.add(self.m.chromium.output_dir.join(binary + '.exe'))
        else:
          binaries.add(self.m.chromium.output_dir.join(binary))

        break

    return sorted(binaries, key=str)


  def _filter_source_file(self, file_paths, extensions):
    """Filters source files with valid extensions.

    Args:
      file_paths: A list of string file paths relative to the checkout path.
      extensions: A list of extensions to filter source files.

    Returns:
      A sub-list of the input with valid extensions.
    """
    source_files = []
    for file_path in file_paths:
      if any([file_path.endswith(extension) for extension in extensions]):
        source_files.append(file_path)

    return source_files

  def filter_and_set_affected_source_files(self, affected_files):
    """Filter affected_files and assigns them to self._affected_source_files

    Args:
      affected_files: A list of string file paths relative to the checkout path

    Returns: None
    """
    if self.use_clang_coverage:
      self._affected_source_files = self._filter_source_file(
          affected_files, constants.TOOLS_TO_EXTENSIONS_MAP['clang'])
    elif self.use_java_coverage:
      self._affected_source_files = self._filter_source_file(
          affected_files, constants.TOOLS_TO_EXTENSIONS_MAP['jacoco'])
    elif self.use_javascript_coverage:
      self._affected_source_files = self._filter_source_file(
          affected_files, constants.TOOLS_TO_EXTENSIONS_MAP['v8'])

  def _validate_test_types(self):
    """Validates that test type to process in build is supported."""
    for test_type in self._test_types:
      if test_type not in constants.SUPPORTED_TEST_TYPES:
        raise Exception('Unsupported test type %s.' % test_type)

  def _set_builder_output_properties_for_uploads(self):
    """Sets the output property of the builder."""
    result = self.m.step.empty('Set builder output properties')
    result.presentation.properties['coverage_metadata_gs_paths'] = (
        self._coverage_metadata_gs_paths)
    result.presentation.properties['mimic_builder_names'] = (
        self._mimic_builder_names)
    result.presentation.properties['merged_profdata_gs_paths'] = (
        self._merged_profdata_gs_paths)
    result.presentation.properties['coverage_gs_bucket'] = (self._gs_bucket)
    result.presentation.properties['coverage_is_presubmit'] = (
        self._is_per_cl_coverage)

  def instrument(self,
                 affected_files,
                 output_dir=None,
                 is_deps_only_change=False):
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
      self.m.step.empty(
          'skip instrumenting code coverage because >200 files are modified')
    if is_deps_only_change:
      # Skip instrumentation if current change is a DEPS only change.
      # This is because code_coverage recipe module expects affected_files to
      # belong to a chromium checkout, and in case of DEPS only change
      # affected_files belong to third party code.
      affected_files = []
      self.m.step.empty(
          'Skip instrumentating code coverage because DEPS only change')

    if not output_dir:
      output_dir = self.m.chromium.output_dir

    self.set_is_per_cl_coverage(True)

    self.filter_and_set_affected_source_files(affected_files)
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
        self.m.step.empty('skip processing because of an exception '
                          'when validating test types to process: %s' % e)
      else:
        self.m.step.empty(
            'Exception when validating test types to process: %s' % e,
            status=self.m.step.FAILURE)
      return

    if self._is_per_cl_coverage:
      if not self._affected_source_files:
        self.m.step.empty(
            'skip processing coverage data because no source file changed')
        return
      unsupported_projects = self._get_unsupported_projects()
      if unsupported_projects:
        self.m.step.empty(
            'skip processing coverage data, project(s) %s is(are) unsupported' %
            unsupported_projects)
        return

    if self.use_clang_coverage:
      for test_type in self._test_types:
        self._current_processing_test_type = test_type
        self.process_clang_coverage_data(tests)

    if self.use_java_coverage:
      try:
        for test_type in self._test_types:
          self._current_processing_test_type = test_type
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

  def process_clang_coverage_data(self, tests=None, binaries=None):
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

    if not self.m.profiles.profile_subdirs:  # pragma: no cover.
      self.m.step.empty(
          'skip processing coverage data because no profile data collected')
      return

    with self.m.step.nest(
        'process clang code coverage data for %s test coverage' %
        self._current_processing_test_type) as processing_step:
      try:
        merged_profdata = self._merge_and_upload_profdata()
        if not merged_profdata:
          self.m.step.empty('skip processing because no profdata was generated')
          return

        merge_errors = self.m.profiles.find_merge_errors()
        if merge_errors.stdout:
          result = self.m.step.active_result
          result.presentation.text = 'Found invalid profraw files'
          result.presentation.properties['merge errors'] = merge_errors.stdout

        if not binaries:
          binaries = self.get_binaries(tests)
          binaries = self._get_binaries_with_valid_coverage_data_on_trybot(
              binaries, merged_profdata)

          if not binaries:
            self.m.step.empty('skip processing because no data is found')
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

  def _persist_coverage_data_as_json(self, source, data_type, **kwargs):
    """Upload coverage data to GCS bucket.

    Uploads all.json.gz file to google cloud storage based on the
    |data_type| that is supplied.
    Also adds the gs_path and mimic_builder_name corresponding to the
    uploaded file to self._coverage_metadata_gs_paths and
    self._mimic_builder_names, which are later to be exposed as step properties.

    Args:
      source: Absolute location to all.json.gz
      data_type: Type of metadata supplied e.g. javascript_metadata
    """
    mimic_builder_name = self._compose_current_mimic_builder_name()
    gs_path = self._compose_gs_path_for_coverage_data(
        data_type=data_type, mimic_builder_name=mimic_builder_name)
    self.m.gsutil.upload(
        source=source,
        bucket=self._gs_bucket,
        dest='%s/all.json.gz' % gs_path,
        name='Upload JSON metadata',
        link_name='Coverage metadata',
        **kwargs)
    self._coverage_metadata_gs_paths.append(gs_path)
    self._mimic_builder_names.append(mimic_builder_name)

  def process_java_coverage_data(self, **kwargs):
    """Generates metadata and JaCoCo HTML report to upload to storage bucket.

    Generates Java coverage metadata and JaCoCo HTML report by scripts, and
    uploads them to the code-coverage-data storage bucket.

    Args:
      **kwargs: Kwargs for python and gsutil steps.
    """
    with self.m.step.nest('process java coverage (%s)' %
                          self._current_processing_test_type):
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
          args.extend(['--diff-mapping-path', self.bot_to_gerrit_mapping_file])
        else:
          dir_metadata_path = self._generate_dir_metadata()
          args.extend([
              '--dir-metadata-path',
              dir_metadata_path,
          ])
        args.extend([
            '--exec-filename-pattern',
            ("%s\.exec" % constants.PLATFORM_TO_TARGET_NAME_PATTERN_MAP[
                self.platform][self._current_processing_test_type])
        ])
        args.extend(['--exclusion-pattern', constants.EXCLUDED_FILE_REGEX])
        args.append('--third-party-inclusion-subdirs')
        args.extend(constants.INCLUDED_THIRD_PARTY_SUBDIRS)
        self.m.python(
            'Generate Java coverage metadata',
            self.resource('generate_coverage_metadata_for_java.py'),
            args=args,
            **kwargs)

        metadata_path = coverage_dir.join('all.json.gz')
        if not self.m.path.exists(metadata_path):
          self.m.step.empty(
              'skip processing because %s tests metadata was missing' %
              self._current_processing_test_type)
          return
        self._persist_coverage_data_as_json(
            source=metadata_path, data_type='java_metadata', **kwargs)
      except self.m.step.StepFailure:
        self.m.step.active_result.presentation.properties[
            'process_coverage_data_failure'] = True
        if not self._is_per_cl_coverage:
          # Do not raise coverage steps exception for per-cl coverage.
          raise

  def process_javascript_coverage_data(self):
    with self.m.step.nest('process javascript coverage'):
      try:
        coverage_dir = self.m.chromium.output_dir.join('devtools_code_coverage')
        args = [
            '--src-path',
            self.m.path['checkout'],
            '--output-dir',
            coverage_dir,
            '--coverage-dir',
            coverage_dir,
        ]

        if self._is_per_cl_coverage:
          args.append('--source-files')
          args.extend(self._affected_source_files)
          args.extend(['--diff-mapping-path', self.bot_to_gerrit_mapping_file])
        else:
          dir_metadata_path = self._generate_dir_metadata()
          args.extend([
              '--dir-metadata-path',
              dir_metadata_path,
          ])

        self.m.python(
            'Generate JavaScript coverage metadata',
            self.resource('generate_coverage_metadata_for_javascript.py'),
            args=args)

        metadata_path = coverage_dir.join('all.json.gz')
        self._persist_coverage_data_as_json(
            source=metadata_path, data_type='javascript_metadata')
      except self.m.step.StepFailure:
        self.m.step.active_result.presentation.properties[
            'process_coverage_data_failure'] = True
        if not self._is_per_cl_coverage:
          # Do not raise coverage steps exception for per-cl coverage.
          raise

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
    if self.platform in constants.PLATFORM_TO_TARGET_NAME_PATTERN_MAP:
      input_profdata_pattern = ("%s\.profdata" %
                                constants.PLATFORM_TO_TARGET_NAME_PATTERN_MAP[
                                    self.platform][test_type])
    else:
      # do not filter anything
      input_profdata_pattern = ".+\.profdata"

    self.m.profiles.merge_profdata(
        merged_profdata,
        profdata_filename_pattern=input_profdata_pattern,
        sparse=True)

    if not self.m.path.exists(merged_profdata):
      return None

    # The uploaded profdata file is named "merged.profdata" regardless of test
    # type, since test types are already distinguished in builder part of gs
    # path.
    gs_path = self._compose_gs_path_for_coverage_data(
        data_type='merged.profdata',
        mimic_builder_name=self._compose_current_mimic_builder_name())
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
        '--llvm-cov', self.cov_executable, '--compilation-directory',
        self.m.chromium.output_dir, '--binaries'
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

    html_report_gs_path = self._compose_gs_path_for_coverage_data(
        data_type='html_report',
        mimic_builder_name=self._compose_current_mimic_builder_name())
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

  def _compose_gs_path_for_coverage_data(self, data_type, mimic_builder_name):
    build = self.m.buildbucket.build
    build_id = build.id
    if self.m.led.launched_by_led:
      build_id = self.m.swarming.task_id
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
          build_id,
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
          build_id,
          data_type,
      )

  def _generate_dir_metadata(self):
    """Extracts directory metadata, e.g. mapping to monorail component."""
    dir_metadata = self.m.path.mkdtemp().join(constants.DIR_METADATA_FILE_NAME)
    with self.m.context(cwd=self.m.path['checkout']):
      self.m.step('Extract directory metadata', [
          self.m.path['checkout'].join('third_party', 'depot_tools', 'dirmd'),
          'export', '-out', dir_metadata
      ])
    return dir_metadata

  def _generate_and_upload_metadata(self, binaries, profdata_path):
    """Generates the coverage info in metadata format."""
    args = [
        '--build-dir',
        self.m.chromium.output_dir,
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

      args.extend(['--diff-mapping-path', self.bot_to_gerrit_mapping_file])
    else:
      args.extend(['--exclusion-pattern', constants.EXCLUDED_FILE_REGEX])
      args.append('--third-party-inclusion-subdirs')
      args.extend(constants.INCLUDED_THIRD_PARTY_SUBDIRS)
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
      gs_path = self._compose_gs_path_for_coverage_data(
          data_type='metadata',
          mimic_builder_name=self._compose_current_mimic_builder_name())
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
