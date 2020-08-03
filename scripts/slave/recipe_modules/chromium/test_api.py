# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api


class ChromiumTestApi(recipe_test_api.RecipeTestApi):

  @recipe_test_api.mod_test_data
  @staticmethod
  def change_char_size_limit(size_limit):
    """Returns an integer that limits compile failure format size.

       This controls how many characters the compile failure summary can have.
    """
    return size_limit

  @recipe_test_api.mod_test_data
  @staticmethod
  def change_line_limit(line_limit):
    """Returns an integer that limits compile failure line size

       This controls how many characters each line in
       the compile failure summary can have.
    """
    return line_limit

  def _common_test_data(self,
                        bot_id,
                        mastername,
                        parent_mastername=None,
                        parent_buildername=None):
    props = self.m.properties(bot_id=bot_id)
    if mastername is not None:
      props += self.m.properties(mastername=mastername)
    if parent_buildername is not None:
      parent_mastername = parent_mastername or mastername
      props += self.m.properties(
          parent_mastername=parent_mastername,
          parent_buildername=parent_buildername,
      )
    return props

  def ci_build(self,
               project='chromium',
               bucket='ci',
               mastername='chromium.linux',
               builder='Linux Builder',
               parent_mastername=None,
               parent_buildername=None,
               bot_id='test_bot',
               git_repo='https://chromium.googlesource.com/chromium/src',
               revision='2d72510e447ab60a9728aeea2362d8be2cbd7789',
               build_number=571,
               tags=None,
               **kwargs):
    """Create test data for a chromium CI build.

    Adding this to a test will set properties and inputs in a manner
    that is compatible with the chromium module for builds that would be
    triggered by a scheduler poller with an associated gitiles commit
    (or triggered by another builder that was triggered by a scheduler
    poller).
    """
    props = self._common_test_data(
        bot_id=bot_id,
        mastername=mastername,
        parent_mastername=parent_mastername,
        parent_buildername=parent_buildername)
    return props + self.m.buildbucket.ci_build(
        project=project,
        bucket=bucket,
        builder=builder,
        build_number=build_number,
        revision=revision,
        git_repo=git_repo,
        tags=tags,
        **kwargs)

  def generic_build(self,
                    project='chromium',
                    bucket='ci',
                    mastername='chromium.linux',
                    builder='Linux Builder',
                    parent_mastername=None,
                    parent_buildername=None,
                    bot_id='test_bot',
                    build_number=571,
                    tags=None,
                    **kwargs):
    """Create test data for a generic chromium build.

    Adding this to a test will set properties and inputs in a manner
    that is compatible with the chromium module for builds that have
    neither an associated gitiles commit or gerrit change (e.g. CI
    builder triggered via the scheduler UI or a cron-like schedule).
    """
    props = self._common_test_data(
        bot_id=bot_id,
        mastername=mastername,
        parent_mastername=parent_mastername,
        parent_buildername=parent_buildername)
    return props + self.m.buildbucket.generic_build(
        project=project,
        bucket=bucket,
        builder=builder,
        build_number=build_number,
        tags=tags,
        **kwargs)

  def try_build(self,
                project='chromium',
                bucket='try',
                mastername='tryserver.chromium.linux',
                builder='linux-rel',
                bot_id='test_bot',
                git_repo='https://chromium.googlesource.com/chromium/src',
                build_number=571,
                change_number=456789,
                patch_set=12,
                tags=None,
                **kwargs):
    """Create test data for a chromium try build.

    Adding this to a test will set properties and inputs in a manner
    that is compatible with the chromium module for try builds with an
    associated gerrit change.
    """
    props = self._common_test_data(bot_id=bot_id, mastername=mastername)
    return props + self.m.buildbucket.try_build(
        project=project,
        bucket=bucket,
        builder=builder,
        build_number=build_number,
        git_repo=git_repo,
        change_number=change_number,
        patch_set=patch_set,
        tags=tags,
        **kwargs)

  def override_version(self, major=64, minor=0, build=3282, patch=0):
    assert isinstance(major, int)
    assert isinstance(minor, int)
    assert isinstance(build, int)
    assert isinstance(patch, int)
    version_file_contents = 'MAJOR=%d\nMINOR=%d\nBUILD=%d\nPATCH=%d\n' % (
        major, minor, build, patch)
    return self.override_step_data(
        'get version',
        self.m.file.read_text(version_file_contents))

  def gen_tests_for_builders(
      self, builder_dict,
      project='chromium',
      git_repo='https://chromium.googlesource.com/chromium/src'):
    # TODO: crbug.com/354674. Figure out where to put "simulation"
    # tests. Is this really the right place?

    def _sanitize_nonalpha(text):
      return ''.join(c if c.isalnum() else '_' for c in text)

    for mastername in builder_dict:
      for buildername in builder_dict[mastername]['builders']:
        if 'mac' in buildername or 'Mac' in buildername:
          platform_name = 'mac'
        elif 'win' in buildername or 'Win' in buildername:
          platform_name = 'win'
        else:
          platform_name = 'linux'
        test = self.test(
            'full_%s_%s' % (_sanitize_nonalpha(mastername),
                            _sanitize_nonalpha(buildername)),
            self.m.platform.name(platform_name),
        )
        if mastername.startswith('tryserver'):
          test += self.try_build(
              project=project,
              mastername=mastername,
              builder=buildername,
              git_repo=git_repo,
          )
        else:
          test += self.ci_build(
              project=project,
              mastername=mastername,
              builder=buildername,
              git_repo=git_repo,
          )

        yield test

  # The following data was generated by running 'gyp_chromium
  # --analyzer' with input JSON files corresponding to changes
  # affecting these targets.
  @property
  def analyze_builds_nothing(self):
    return self.m.json.output({
        'status': 'No dependencies',
        'compile_targets': [],
        'test_targets': [],
        })
