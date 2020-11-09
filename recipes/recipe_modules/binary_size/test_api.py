# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api
from PB.recipe_modules.build.binary_size import properties as properties_pb

from . import constants


class BinarySizeTestApi(recipe_test_api.RecipeTestApi):

  def properties(self, **kwargs):
    for key in kwargs:
      assert hasattr(properties_pb.InputProperties, key)
    return self.m.properties(**{'$build/binary_size': kwargs})

  def build(self, commit_message='message', size_footer=False, **kwargs):
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
    return sum([
        self.m.chromium.try_build(
            builder_group='tryserver.chromium.android',
            builder=constants.TEST_BUILDER,
            build_number=constants.TEST_BUILDNUMBER,
            patch_set=1,
            **kwargs),
        self.m.platform('linux', 64),
        self.override_step_data(
            'gerrit changes',
            self.m.json.output([{
                'revisions': {
                    kwargs['revision']: revision_info
                }
            }])),
        self.override_step_data('parse description',
                                self.m.json.output(footer_json)),
        self.m.time.seed(constants.TEST_TIME),
    ], self.empty_test_data())

  def on_significant_binary_package_restructure(self):
    return self.override_step_data(
        constants.READ_SIZE_CONFIG_JSON_STEP_NAME,
        self.m.json.output({
            'mapping_files': constants.TEST_MAPPING_FILES,
            'resource_sizes_args': {
                'apk_name': constants.TEST_SUPERSIZE_INPUT_FILE,
            },
            'supersize_input_file': constants.TEST_SUPERSIZE_INPUT_FILE,
            'version': constants.TEST_VERSION_NEW,  # Change.
        }))
