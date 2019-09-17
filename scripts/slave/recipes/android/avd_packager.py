# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Packages Android AVDs as CIPD packages."""

from recipe_engine import post_process
from PB.recipes.build.android import avd_packager

DEPS = [
    'chromium_checkout',
    'depot_tools/gclient',
    'recipe_engine/context',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
]


PROPERTIES = avd_packager.InputProperties


def RunSteps(api, properties):
  api.gclient.set_config('chromium')
  api.gclient.apply_config('android')
  api.chromium_checkout.ensure_checkout({})

  chromium_src = api.path['checkout']
  avd_script_path = chromium_src.join(
      'tools', 'android', 'avd', 'avd.py')

  with api.context(cwd=chromium_src):
    for avd_config in properties.avd_configs:
      avd_config_path = chromium_src.join(avd_config)
      create_result = api.python(
          'avd create %s' % avd_config,
          avd_script_path,
          ['create', '-v', '--avd-config', avd_config_path,
           '--cipd-json-output', api.json.output()])
      if create_result.json.output:
        cipd_result = create_result.json.output.get('result', {})
        if 'package' in cipd_result and 'instance_id' in cipd_result:
          # TODO(crbug.com/922145): Switch this to api.cipd.add_instance_link
          # if crrev.com/c/1546431 lands.
          create_result.presentation.links[cipd_result['instance_id']] = (
              'https://chrome-infra-packages.appspot.com' +
              '/p/%(package)s/+/%(instance_id)s' % cipd_result)


def GenTests(api):
  def links_include(check, step_odict, step, link_name):
    check(
        'step result for %s contained link named %s' % (step, link_name),
        link_name in step_odict[step].links)

  yield api.test(
      'basic',
      api.properties(
          avd_configs=[
              'tools/android/avd/proto/generic_android23.textpb',
              'tools/android/avd/proto/generic_android28.textpb',
          ]),
      api.post_process(
          post_process.MustRun,
          'avd create tools/android/avd/proto/generic_android23.textpb'),
      api.override_step_data(
          'avd create tools/android/avd/proto/generic_android23.textpb',
          api.json.output({
              'result': {
                  'instance_id': 'instance-id-generic-android-23',
                  'package': 'sample/avd/package/name',
              }
          })),
      api.post_process(
          links_include,
          'avd create tools/android/avd/proto/generic_android23.textpb',
          'instance-id-generic-android-23'),
      api.post_process(
          post_process.MustRun,
          'avd create tools/android/avd/proto/generic_android28.textpb'),
      api.override_step_data(
          'avd create tools/android/avd/proto/generic_android28.textpb',
          api.json.output({
              'result': {
                  'instance_id': 'instance-id-generic-android-28',
                  'package': 'sample/avd/package/name',
              }
          })),
      api.post_process(
          links_include,
          'avd create tools/android/avd/proto/generic_android28.textpb',
          'instance-id-generic-android-28'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation)
  )
