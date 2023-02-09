# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class DepbotAPI(recipe_api.RecipeApi):

  def run(self, src_dir, build_dir, json_out):
    depbot_path = self.m.cipd.ensure_tool(
        'infra_internal/tools/security/depbot/${platform}', 'latest')

    self.m.step(
        'run depbot', [
            depbot_path, '--target', '//base:base', '--chromium-src-dir',
            src_dir, '--log-level', 'debug', '--gn-path',
            self.m.depot_tools.gn_py_path, '--build-dir', build_dir,
            '--json-output', json_out
        ],
        step_test_data=(lambda: self.m.json.test_api.output(
            data={
                'entry_point': '//base:base',
                'artifacts': [],
                'libraries': [],
                'build_metadata': {}
            },
            name='results')))
