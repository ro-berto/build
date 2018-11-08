# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from recipe_engine import recipe_api


_BUCKET_NAME = 'cr-coverage-profile-data'


class ClangCoverageApi(recipe_api.RecipeApi):
  """This module contains apis to interact with llvm-cov and llvm-profdata."""

  def __init__(self, *args, **kwargs):
    super(ClangCoverageApi, self).__init__(*args, **kwargs)
    # A single temporary directory to contain the profile data for all targets
    # in the build.
    self._base_profdata_dir = None
    # Temp dir for report.
    self._report_dir = None
    # Temp dir for json metadata
    self._json_metadata_dir = None
    # Maps step names to subdirectories of the above.
    self._profdata_dirs = {}
    # When set, subset of files to include in the coverage report.
    self._affected_files = None

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
  def json_metadata_dir(self):
    """A temporary directory for the json metadata. Created on first access."""
    if not self._json_metadata_dir:
      self._json_metadata_dir = self.m.path.mkdtemp()
    return self._json_metadata_dir

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
    return (self.m.gclient.c
            and self.m.gclient.c.solutions
            and 'checkout_clang_coverage_tools'
            in self.m.gclient.c.solutions[0].custom_vars)

  def _get_binaries(self, tests):
    """Returns a path to the binary for the given test object."""
    # TODO(crbug.com/899974): Implement a sturdier approach that also works in
    # separate builder-tester setup.

    # This naive approach relies on the test binary sharing a name with the test
    # target. Also, this only works for builder_tester.
    binaries = []
    for t in tests:
      if t.is_gtest and t.runs_on_swarming:
        binaries.append(self.m.chromium.output_dir.join(t.isolate_target))
    return list(set(binaries))

  def instrument(self, affected_files):
    """Saves source paths to generate coverage instrumentation for to a file.

    Args:
      affected_files (list of str): paths to the files we want to instrument,
          relative to the checkout path.
    """
    self._affected_files = affected_files
    return self.m.python(
        'save paths of affected files',
        self.resource('write_paths_to_instrument.py'),
        args=[
            '--write-to',
            self.m.chromium.c.code_coverage.clang_instrumented_paths_file,
            '--src-path',
            self.m.path['checkout'],
            '--build-path',
            self.m.chromium.c.build_dir,
        ] + affected_files)

  def process_coverage_data(self, tests):
    """Processes the coverage data for html report or metadata.

    Args:
      tests (list of self.m.chromium_tests.stepsl.Test): A list of test objects
          whose binaries we are to create a coverage report for.
    """
    if not self._profdata_dirs:  # pragma: no cover.
      return

    out_file = self.profdata_dir().join('merged.profdata')
    self.m.python(
        'merge profile data for %d targets' % len(self._profdata_dirs),
        self.resource('merge_steps.py'),
        args=[
            '--input-dir',
            self.profdata_dir(),
            '--output-file',
            out_file,
            '--llvm-profdata',
            self.profdata_executable,
        ])

    binaries = self._get_binaries(tests)

    self._generate_html_report(binaries, out_file)
    self._generate_metadata(binaries, out_file)


  def _generate_html_report(self, binaries, profdata_path):
    """Generate html coverage report for the given binaries.

    Produce a coverage report for the instrumented test targets and upload to
    the appropriate bucket.
    """
    args = [
        '--report-directory', self.report_dir, '--profdata-path', profdata_path,
        '--llvm-cov', self.cov_executable, '--binaries']
    args.extend(binaries)
    if self._affected_files:
      args.append('--sources')
      args.extend(
          [self.m.path['checkout'].join(s) for s in self._affected_files])

    self.m.python(
        'generate html report for %d targets' % len(self._profdata_dirs),
        self.resource('make_report.py'),
        args=args
    )

    report_gs_path = self._compose_gs_path_for_coverage_data('html')
    upload_step = self.m.gsutil.upload(
        self.report_dir,
        _BUCKET_NAME,
        report_gs_path,
        link_name=None,
        args=['-r'],
        multithreaded=True,
        name='upload html report')
    upload_step.presentation.links['html report'] = (
        'https://storage.googleapis.com/%s/%s/index.html' % (
            _BUCKET_NAME, report_gs_path))
    upload_step.presentation.properties['coverage_html_gs'] = report_gs_path

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
    if build.input.gerrit_changes:  # pragma: no cover. TODO: mock the build.
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

  def _generate_metadata(self, binaries, profdata_path):
    """Generates the coverage info in metadata format."""
    args = [
        '--src-path', self.m.path['checkout'],
        '--output-dir', self.json_metadata_dir,
        '--profdata-path', profdata_path,
        '--llvm-cov', self.cov_executable,
        '--binaries',
    ]
    args.extend(binaries)
    if self._affected_files:
      args.append('--sources')
      args.extend(
          [self.m.path['checkout'].join(s) for s in self._affected_files])

    self.m.python(
        'generate metadata for %d targets' %
            len(self._profdata_dirs),
        self.resource('generate_coverage_metadata.py'),
        args=args)

    gs_path = self._compose_gs_path_for_coverage_data('metadata')
    upload_step = self.m.gsutil.upload(self.json_metadata_dir,
                                       _BUCKET_NAME,
                                       gs_path,
                                       link_name=None,
                                       args=['-r'],
                                       multithreaded=True,
                                       name='upload metadata')
    upload_step.presentation.links['metadata report'] = (
        'https://storage.googleapis.com/%s/%s/' % (_BUCKET_NAME, gs_path))
    upload_step.presentation.properties['coverage_metadata_gs_path'] = gs_path
    upload_step.presentation.properties['coverage_gs_bucket'] = _BUCKET_NAME
