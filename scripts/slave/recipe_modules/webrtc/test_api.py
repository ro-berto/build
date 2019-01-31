# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Exposes the builder and recipe configurations to GenTests in recipes.

import base64
import json

from recipe_engine import recipe_test_api
from . import api
from . import builders as webrtc_builders
from . import steps


class WebRTCTestApi(recipe_test_api.RecipeTestApi):
  BUILDERS = webrtc_builders.BUILDERS
  RECIPE_CONFIGS = webrtc_builders.RECIPE_CONFIGS

  def example_binary_sizes(self):
    return self.m.json.output({'some_binary': 123456})

  def example_patch(self):
    return self.m.json.output({
        'value': base64.b64encode('diff --git a/a b/a\nnew file mode 100644\n')
    })

  def generate_builder(self, builders, bucketname, buildername, revision,
                       parent_got_revision=None, failing_test=None,
                       suffix='', fail_android_archive=False,
                       is_chromium=False, is_experimental=False):
    mastername = builders[bucketname]['settings'].get('mastername', bucketname)
    bot_config = builders[bucketname]['builders'][buildername]
    bot_type = bot_config.get('bot_type', 'builder_tester')

    if bot_type in ('builder', 'builder_tester'):
      assert bot_config.get('parent_buildername') is None, (
          'Unexpected parent_buildername for builder %r on bucket %r.' %
              (buildername, bucketname))

    chromium_kwargs = bot_config.get('chromium_config_kwargs', {})
    test = (
      self.test('%s_%s%s' % (_sanitize_builder_name(bucketname),
                             _sanitize_builder_name(buildername), suffix)) +
      self.m.properties(mastername=mastername,
                        buildername=buildername,
                        bot_id='bot_id',
                        path_config='kitchen',
                        BUILD_CONFIG=chromium_kwargs['BUILD_CONFIG']) +
      self.m.platform(bot_config['testing']['platform'],
                      chromium_kwargs.get('TARGET_BITS', 64)) +
      self.m.runtime(is_luci=True, is_experimental=is_experimental)
    )

    if bot_config.get('parent_buildername'):
      test += self.m.properties(
          parent_buildername=bot_config['parent_buildername'])
    if revision:
      test += self.m.properties(revision=revision,
                                got_revision='a' * 40,
                                got_revision_cp='refs/heads/master@{#1337}')
    if bot_type == 'tester':
      parent_rev = parent_got_revision or revision
      test += self.m.properties(parent_got_revision=parent_rev)

    if failing_test:
      test += self.step_data(failing_test, retcode=1)

    if fail_android_archive:
      test += self.step_data('build android archive', retcode=1)

    git_repo = 'https://webrtc.googlesource.com/src'
    if is_chromium:
      git_repo = 'https://chromium.googlesource.com/chromium/src'
    short_bucket = bucketname.split('.')[-1]
    if 'try' in bucketname:
      test += self.m.buildbucket.try_build(
          project='webrtc',
          bucket=short_bucket,
          builder=buildername,
          git_repo=git_repo,
          revision=revision or None)
    else:
      test += self.m.buildbucket.ci_build(
          project='webrtc',
          bucket=short_bucket,
          builder=buildername,
          git_repo=git_repo,
          revision=revision or 'a' * 40)
    test += self.m.properties(buildnumber=1337)

    return test

  def example_chartjson(self):
    return json.dumps({
      "format_version": "1.0",
      "charts": {
        "warm_times": {
          "http://www.google.com/": {
            "type": "list_of_scalar_values",
            "values": [9, 9, 8, 9],
            "units": "sec"
          },
        },
        "html_size": {
          "http://www.google.com/": {
            "type": "scalar",
            "value": 13579,
            "units": "bytes"
          }
        },
        "load_times": {
          "http://www.google.com/": {
            "type": "list_of_scalar_values",
            "value": [4.2],
            "std": 1.25,
            "units": "sec"
          }
        }
      }
    })


def _sanitize_builder_name(name):
  return api.sanitize_file_name(name.lower())
