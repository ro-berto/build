# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import re

from recipe_engine import recipe_api

_BUCKET_NAME = 'code-coverage-data'

# Name of the file to store the component map.
_COMPONENT_MAPPING_FILE_NAME = 'component_mapping_path.json'

# Name of the file to store the line number mapping from bot to Gerrit.
_BOT_TO_GERRIT_LINE_NUM_MAPPING_FILE_NAME = (
    'bot_to_gerrit_line_num_mapping.json')

# Set of valid extensions for source files that use Clang.
_EXTENTIONS_OF_SOURCE_FILES_SUPPORTED_BY_CLANG = set([
    '.mm', '.S', '.c', '.hh', '.cxx', '.hpp', '.cc', '.cpp', '.ipp', '.h', '.m',
    '.hxx'
])


class ClangCoverageApi(recipe_api.RecipeApi):
  """This module contains apis to interact with llvm-cov and llvm-profdata."""

  def __init__(self, *args, **kwargs):
    super(ClangCoverageApi, self).__init__(*args, **kwargs)
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
  def raw_profile_merge_script(self):
    """Returns the location of a script that merges raw profiles from shards.

    This is intended to be passed to the swarming recipe module to be called
    upon completion of the shards.
    """
    return self.resource('merge_profiles.py')

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
    return (self.m.gclient.c and self.m.gclient.c.solutions and
            'checkout_clang_coverage_tools' in self.m.gclient.c.solutions[0]
            .custom_vars)

  def _get_binaries(self, tests):
    """Returns a path to the binary for the given test object."""
    # TODO(crbug.com/899974): Implement a sturdier approach that also works in
    # separate builder-tester setup.

    # This naive approach relies on the test binary sharing a name with the test
    # target. Also, this only works for builder_tester on linux.
    binaries = []
    for t in tests:
      if t.is_gtest and t.runs_on_swarming:
        binaries.append(self.m.chromium.output_dir.join(t.isolate_target))
      # TODO(crbug.com/914213): Remove webkit_layout_tests reference.
      elif 'webkit_layout_tests' in t.isolate_target or (
          'blink_web_tests' in t.isolate_target):
        binaries.append(self.m.chromium.output_dir.join('content_shell'))
      elif t.isolate_target.endswith('_fuzzer'):
        binaries.append(self.m.chromium.output_dir.join(t.isolate_target))
    return list(set(binaries))

  def _filter_source_file(self, file_paths):
    """Fitlers source files with valid extensions.

    Set of valid extensions is defined in:
      _EXTENTIONS_OF_SOURCE_FILES_SUPPORTED_BY_CLANG.

    Args:
      file_paths: A list of file paths relative to the checkout path.

    Returns:
      A sub-list of the input with valid extensions.
    """
    source_files = []
    for file_path in file_paths:
      if any([
          file_path.endswith(extension)
          for extension in _EXTENTIONS_OF_SOURCE_FILES_SUPPORTED_BY_CLANG
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
            self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs),
        ] + self._affected_source_files,
        stdout=self.m.raw_io.output_text(add_output_log=True))

  def process_coverage_data(self, tests):
    """Processes the coverage data for html report or metadata.

    Args:
      tests (list of self.m.chromium_tests.stepsl.Test): A list of test objects
          whose binaries we are to create a coverage report for.
    """
    if not self._profdata_dirs:  # pragma: no cover.
      return

    if self._is_per_cl_coverage and not self._affected_source_files:
      self.m.python.succeeding_step(
          'skip collecting coverage data because no source file is changed', '')
      return

    try:
      merged_profdata = self._merge_profdata()
      self._surface_merging_errors()
      binaries = self._get_binaries(tests)

      self._generate_and_upload_metadata(binaries, merged_profdata)
      self._generate_and_upload_html_report_on_trybot(binaries, merged_profdata)
    except self.m.step.StepFailure:
      self.m.step.active_result.presentation.properties[
          'process_coverage_data_failure'] = True
      raise

  def _merge_profdata(self):
    """Merges the profdata generated by each step to a single profdata."""
    merged_profdata = self.profdata_dir().join('merged.profdata')
    self.m.python(
        'merge profile data for %d targets' % len(self._profdata_dirs),
        self.resource('merge_steps.py'),
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
        _BUCKET_NAME,
        gs_path,
        link_name=None,
        name='upload merged.profdata')
    upload_step.presentation.links['merged.profdata'] = (
        'https://storage.cloud.google.com/%s/%s' % (_BUCKET_NAME, gs_path))
    upload_step.presentation.properties['merged_profdata_gs_path'] = gs_path

    return merged_profdata

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
        'generate html report for %d targets' % len(self._profdata_dirs),
        self.resource('make_report.py'),
        args=args)

    html_report_gs_path = self._compose_gs_path_for_coverage_data('html_report')
    upload_step = self.m.gsutil.upload(
        self.report_dir,
        _BUCKET_NAME,
        html_report_gs_path,
        link_name=None,
        args=['-r'],
        multithreaded=True,
        name='upload html report')
    upload_step.presentation.links['html report'] = (
        'https://storage.cloud.google.com/%s/%s/index.html' %
        (_BUCKET_NAME, html_report_gs_path))

  def shard_merge(self, step_name):
    """Returns a merge object understood by the swarming module.

    See the docstring for the `merge` parameter of api.swarming.task.
    """
    return {
        'script':
            self.raw_profile_merge_script,
        'args': [
            '--profdata-dir',
            self.profdata_dir(step_name),
            '--llvm-profdata',
            self.profdata_executable,
        ],
    }

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
    llvm_cov = self.cov_executable
    if not self._is_per_cl_coverage:
      # Download the version with multi-thread support.
      # Assume that this is running on Linux.
      temp_dir = self.m.path.mkdtemp()
      self.m.gsutil.download(
          _BUCKET_NAME,
          'llvm_cov_multithread',
          temp_dir,
          name='download llvm-cov')
      llvm_cov = temp_dir.join('llvm_cov_multithread')

    args = [
        '--src-path',
        self.m.path['checkout'],
        '--output-dir',
        self.metadata_dir,
        '--profdata-path',
        profdata_path,
        '--llvm-cov',
        llvm_cov,
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
      args.extend(
          ['--component-mapping-path',
           self._generate_component_mapping()])

    try:
      self.m.python(
          'generate metadata for %d targets' % len(self._profdata_dirs),
          self.resource('generate_coverage_metadata.py'),
          args=args,
          venv=True)
    finally:
      gs_path = self._compose_gs_path_for_coverage_data('metadata')
      upload_step = self.m.gsutil.upload(
          self.metadata_dir,
          _BUCKET_NAME,
          gs_path,
          link_name=None,
          args=['-r'],
          multithreaded=True,
          name='upload metadata')
      upload_step.presentation.links['metadata report'] = (
          'https://storage.cloud.google.com/%s/%s/index.html' % (_BUCKET_NAME,
                                                                 gs_path))
      upload_step.presentation.properties['coverage_metadata_gs_path'] = gs_path
      upload_step.presentation.properties['coverage_gs_bucket'] = _BUCKET_NAME

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
            '--output-file',
            self.m.json.output(leak_to=local_to_gerrit_diff_mapping_file)
        ] + source_files)

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
      step_result.presentation.status = self.m.step.FAILURE
      step_result.presentation.properties[
          'bad_coverage_profiles'] = step_result.stdout

  def get_local_isolated_coverage(self, step_name, local_run_isolate_step):
    """Collect coverage data from local isolated run.

    Analogous to the merge script that we pass for the swarming collect step,
    this api finds the output isolate from the stdout of the step that ran the
    isolated test locally, downloads it and merges the raw profile(s) into a
    single profdata."""
    output_isolated = _find_isolated_json(local_run_isolate_step.stdout)
    profraw_dir = self.m.path.mkdtemp()
    if output_isolated:
      with self.m.step.nest('generate coverage profdata for %s' % step_name):
        self.m.python(
            'retrieve raw profiles for %s' % step_name,
            self.m.swarming_client.path.join('isolateserver.py'),
            args=[
                'download',
                '-I%s' % output_isolated['storage'],
                '-s%s' % output_isolated['hash'],
                '--target=%s' % profraw_dir
            ])
        self.m.python(
            'index raw profiles for %s' % step_name,
            self.raw_profile_merge_script,
            args=[
                '--profdata-dir',
                self.profdata_dir(step_name),
                '--task-output-dir',
                profraw_dir,
                '--llvm-profdata',
                self.profdata_executable,
                '--output-json',
                self.profdata_dir(step_name).join('output.json'),
            ])


def _find_isolated_json(stdout):
  isolated_re = re.compile(
      r'\[run_isolated_out_hack\](.*)\[\/run_isolated_out_hack\]')
  match = isolated_re.search(stdout)
  if match:
    return json.loads(match.group(1))
  return None
