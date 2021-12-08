# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc


class FinditApi(recipe_api.RecipeApi):

  def get_bot_mirror_for_tester(self, tester_id, builders=None):
    builders = builders or self.m.chromium_tests_builder_config.builder_db

    tester_spec = builders[tester_id]

    if tester_spec.parent_buildername is None:
      return ctbc.TryMirror.create(
          buildername=tester_id.builder, builder_group=tester_id.group)

    return ctbc.TryMirror.create(
        builder_group=tester_spec.parent_builder_group or tester_id.group,
        buildername=tester_spec.parent_buildername,
        tester=tester_id.builder,
        tester_group=tester_id.group)

  def get_builder_config_for_mirror(self, mirror, builders=None):
    return ctbc.BuilderConfig.create(
        builders or self.m.chromium_tests_builder_config.builder_db,
        builder_ids=[mirror.builder_id],
        builder_ids_in_scope_for_testing=([mirror.tester_id]
                                          if mirror.tester_id else []),
        include_all_triggered_testers=False,
        step_api=self.m.step)

  def existing_targets(self, targets, builder_id):
    """Returns a sublist of the given targets that exist in the build graph.

    We test whether a target exists or not by ninja.

    A "target" here is actually a node in ninja's build graph. For example:
      1. An executable target like browser_tests
      2. An object file like obj/path/to/Source.o
      3. An action like build/linux:gio_loader
      4. An generated header file like gen/library_loaders/libgio.h
      5. and so on

    Args:
     targets (list): A list of targets to be tested for existence.
     builder_id (BuilderId): The ID of the builder to run MB for.
    """
    # Run mb to generate or update ninja build files.
    if self.m.chromium.c.project_generator.tool == 'mb':
      self.m.chromium.mb_gen(builder_id, name='generate_build_files')

    # Run ninja to check existences of targets.
    args = ['--target-build-dir', self.m.chromium.output_dir]
    args.extend(['--ninja-path', self.m.depot_tools.ninja_path])
    for target in targets:
      args.extend(['--target', target])
    args.extend(['--json-output', self.m.json.output()])
    step = self.m.python(
        'check_targets', self.resource('check_target_existence.py'), args=args)
    return step.json.output['found']
