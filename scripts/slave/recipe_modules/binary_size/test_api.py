# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api

from . import constants


class BinarySizeTestApi(recipe_test_api.RecipeTestApi):

  def props(self, commit_message='message', size_footer=False, **kwargs):
    kwargs.setdefault('path_config', 'generic')
    kwargs['revision'] = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    revision_info = {
        '_number': 1,
        'commit': {
            'author': {
                'email': 'foo@bar.com',
            },
            'message': commit_message,
        }
    }
    footer_json = {}
    if size_footer:
      footer_json['Binary-Size'] = ['Totally worth it.']
    return (self.m.properties.tryserver(
        build_config='Release',
        mastername='tryserver.chromium.android',
        buildername=constants.TEST_BUILDER,
        buildnumber=constants.TEST_BUILDNUMBER,
        patch_set=1,
        **kwargs) + self.m.platform('linux', 64) + self.override_step_data(
            'gerrit changes',
            self.m.json.output([{
                'revisions': {
                    kwargs['revision']: revision_info
                }
            }])) + self.override_step_data('parse description',
                                           self.m.json.output(footer_json)) +
            self.m.time.seed(constants.TEST_TIME))
