# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib
import json
import os
import posixpath
import re

from recipe_engine import recipe_api
from recipe_engine import util as recipe_util

class FilterApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(FilterApi, self).__init__(**kwargs)
    self._test_targets = []
    self._compile_targets = []
    self._paths = []

  def __is_path_in_regex_list(self, path, regexes):
    """Returns true if |path| matches any of the regular expressions in
    |regexes|."""
    for regex in regexes:
      match = regex.match(path)
      if match and match.end() == len(path):
        return regex.pattern
    return False

  @property
  def test_targets(self):
    """Returns the set of targets passed to does_patch_require_compile() that
    are affected by the set of files that have changed."""
    return self._test_targets

  @property
  def compile_targets(self):
    """Returns the set of targets that need to be compiled based on the set of
    files that have changed."""
    return self._compile_targets

  @property
  def paths(self):
    """Returns the paths that have changed in this patch.

    Paths are *always* posix-style paths, even on windows. This allows analyze
    configs to only include posix-style paths.
    """
    return self._paths

  def _load_analyze_config(self, file_name):
    """Load the given analyze config.

    Analyze config files are expected to be JSONs in the following format:

    ```
      {
        "<analyze-config-name>": {
          "exclusions": ["<regex-exclusion>", ...],
        },
        ...
      }
    ```

    e.g.

    ```
      {
        "base": {
          "exclusions": [
            "base-regex-exclusion-1",
            "base-regex-exclusion-2",
            "base-regex-exclusion-.*",
            ...
          ]
        },
        "chromium": {
          "exclusions": [
            "chromium-regex-exclusion-1",
            "chromium-regex-exclusion-2",
            "chromium-regex-exclusion-.*",
            ...
          ]
        },
        ...
      }
    ```

    Regex patterns are expected to be posix-style paths.

    Files changed by a patch will be matched against all regex patterns in all
    applicable analyze configs.

    An analyze config file is *required* to have an analyze config named
    "base". Some clients may require additional analyze configs (e.g.
    chromium_tests requires "chromium" in addition to "base").
    """
    config_path = self.m.chromium.c.source_side_spec_dir.join(file_name)
    step_result = self.m.json.read(
      'read filter exclusion spec',
      config_path,
      step_test_data=lambda: self.m.json.test_api.output({
          'base': {
            'exclusions': [],
          },
          'chromium': {
            'exclusions': [],
          },
          'ios': {
            'exclusions': [],
          },
        })
      )
    step_result.presentation.step_text = 'path: %r' % config_path
    return step_result.json.output

  def does_patch_require_compile(self,
                                 affected_files,
                                 test_targets=None,
                                 additional_compile_targets=None,
                                 additional_names=None,
                                 config_file_name='trybot_analyze_config.json',
                                 use_mb=False,
                                 builder_id=None,
                                 mb_config_path=None,
                                 build_output_dir=None,
                                 **kwargs):
    """Check to see if the affected files require a compile or tests.

    Args:
      affected_files: list of files affected by the current patch; paths
                      should only use forward slashes ("/") on all platforms
      test_targets: the possible set of executables that are desired to run.
                    When done, test_targets() returns the subsetset of targets
                    that are affected by the files that have changed.
      additional_compile_targets: any targets to compile in addition to
                                  the test_targets.
      additional_names: additional top level keys to look up exclusions in,
                        see |config_file_name|.
      config_file_name: the config file to look up exclusions in.
      builder_id: the ID of the builder with the config to run MB against.
      mb_config_path: the path to the MB config file.

    Within the file we concatenate "base.exclusions" and
    "|additional_names|.exclusions" (if |additional_names| is not none) to
    get the full list of exclusions.

    The exclusions should be a list of Python regular expressions (as strings).

    If any of the files in the current patch match one of the values in
    we assume everything needs to be compiled and tested.

    If an error occurs, an exception is raised. Otherwise, after the
    call completes the results can be obtained from self.compile_targets()
    and self.test_targets().

    To run MB, we get the build ID for the builder currently being run
    and not those of the continuous builder the trybot may be configured
    to match, because the trybot may have a different mb configuration.
    However, recipes used by Findit for culprit finding may override the
    default with `builder_id` to exactly match a given continuous builder.
    """

    names = ['base']
    if additional_names:
      names.extend(additional_names)

    config_contents = self._load_analyze_config(config_file_name)
    exclusions = []
    ignores = []
    valid_names = [name for name in names if name in config_contents]
    for name in valid_names:
      exclusions.extend(config_contents[name].get('exclusions', []))
      ignores.extend(config_contents[name].get('ignores', []))

    test_targets = test_targets or []
    additional_compile_targets = additional_compile_targets or []
    all_targets = sorted(set(test_targets) | set(additional_compile_targets))
    self._test_targets = []
    self._compile_targets = []

    def rewrite_as_posix(path):
      components = []
      while path:
        path, tail = self.m.path.split(path)
        if tail:
          components = [tail] + components
      if components:
        return posixpath.join(components[0], *components[1:])
      return None

    self._paths = [
        p for p in (rewrite_as_posix(f) for f in affected_files) if p
    ]

    analyze_input = {
        'files': self.paths,
        'test_targets': test_targets,
        'additional_compile_targets': additional_compile_targets,
    }

    # Check the path of each file against the exclusion list. If found, we
    # should ignore the dependency check, because it might be wrong.
    exclusion_regexs = [re.compile(exclusion) for exclusion in exclusions]
    ignore_regexs = [re.compile(ignore) for ignore in ignores]
    ignored = True
    matched_exclusion = False

    first_found_path = ''
    first_match = None
    for path in self.paths:
      first_match = self.__is_path_in_regex_list(path, exclusion_regexs)
      if first_match:
        first_found_path = path
        matched_exclusion = True

      if not self.__is_path_in_regex_list(path, ignore_regexs):
        ignored = False

    if ignored:
      analyze_result = 'No compile necessary (all files ignored)'
      self.m.python.succeeding_step('analyze', analyze_result)
      return

    test_output = {
        'status': 'No dependency',
        'compile_targets': [],
        'test_targets': [],
    }

    env = {}

    # Ensure that mb runs in a clean environment.
    if use_mb and self.m.chromium.c.env.FORCE_MAC_TOOLCHAIN:
      env['FORCE_MAC_TOOLCHAIN'] = self.m.chromium.c.env.FORCE_MAC_TOOLCHAIN

    # If building for CrOS, execute through the "chrome_sdk" wrapper. This will
    # override GYP environment variables, so we'll refrain from defining them
    # to avoid confusing output.
    cwd = None
    if not use_mb:
      env.update(self.m.chromium.c.gyp_env.as_jsonish())
    env['GOMA_SERVICE_ACCOUNT_JSON_FILE'] = \
        self.m.goma.service_account_json_path

    with self.m.context(cwd=cwd, env=env):
      if use_mb:
        builder_id = builder_id or self.m.chromium.get_builder_id()
        step_result = self.m.chromium.mb_analyze(
            builder_id,
            analyze_input,
            mb_config_path=mb_config_path,
            build_dir=build_output_dir)
      else:
        step_result = self.m.python(
            'analyze',
            self.m.path['checkout'].join('build', 'gyp_chromium'),
            args=[
                '--analyzer',
                self.m.json.input(analyze_input),
                self.m.json.output()
            ],
            step_test_data=lambda: self.m.json.test_api.output(test_output),
            **kwargs)

    if 'error' in step_result.json.output:
      step_result.presentation.step_text = (
          'Error: ' + step_result.json.output['error'])
      step_result.presentation.status = self.m.step.FAILURE
      raise self.m.step.StepFailure('Error: ' +
                                    step_result.json.output['error'])

    if 'invalid_targets' in step_result.json.output:
      raise self.m.step.StepFailure(
          'Error, following targets were not '
          'found: ' + ', '.join(step_result.json.output['invalid_targets']))

    if matched_exclusion:
      analyze_result = 'Analyze disabled: matched exclusion'
      # TODO(phajdan.jr): consider using plain api.step here, not python.
      step_result = self.m.python.succeeding_step('analyze_matched_exclusion',
                                                  analyze_result)
      step_result.presentation.logs.setdefault('excluded_files', []).append(
          '%s (regex = \'%s\')' % (first_found_path, first_match))
      self._compile_targets = sorted(all_targets)
      self._test_targets = sorted(test_targets)
    elif (step_result.json.output['status'] in ('Found dependency',
                                                'Found dependency (all)')):
      self._compile_targets = step_result.json.output['compile_targets']
      self._test_targets = step_result.json.output['test_targets']

      # TODO(dpranke) crbug.com/557505 - we need to not prune meta
      # targets that are part of 'test_targets', because otherwise
      # we might not actually build all of the binaries needed for
      # a given test, even if they aren't affected by the patch.
      # Until the GYP code is updated, we will merge the returned
      # test_targets into compile_targets to be safe.
      self._compile_targets = sorted(
          set(self._compile_targets + self._test_targets))
    else:
      step_result.presentation.step_text = 'No compile necessary'

  # TODO(phajdan.jr): Merge with does_patch_require_compile.
  def analyze(self,
              affected_files,
              test_targets,
              additional_compile_targets,
              config_file_name,
              builder_id=None,
              mb_config_path=None,
              build_output_dir=None,
              additional_names=None):
    """Runs "analyze" step to determine targets affected by the patch.

    Returns a tuple of:
      - list of targets that are needed to run tests (see filter recipe module)
      - list of targets that need to be compiled (see filter recipe module)"""

    if additional_names is None:
      additional_names = ['chromium']

    use_mb = (self.m.chromium.c.project_generator.tool == 'mb')
    self.does_patch_require_compile(
        affected_files,
        test_targets=test_targets,
        additional_compile_targets=additional_compile_targets,
        additional_names=additional_names,
        config_file_name=config_file_name,
        use_mb=use_mb,
        builder_id=builder_id,
        mb_config_path=mb_config_path,
        build_output_dir=build_output_dir)

    compile_targets = self.compile_targets[:]

    # Emit more detailed output useful for debugging.
    analyze_details = {
        'test_targets': test_targets,
        'additional_compile_targets': additional_compile_targets,
        'self.m.filter.compile_targets': self.compile_targets,
        'self.m.filter.test_targets': self.test_targets,
        'compile_targets': compile_targets,
    }
    with contextlib.closing(recipe_util.StringListIO()) as listio:
      json.dump(analyze_details, listio, indent=2, sort_keys=True)
    step_result = self.m.step.active_result
    step_result.presentation.logs['analyze_details'] = listio.lines

    return self.test_targets, compile_targets
