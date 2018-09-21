# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Traverse the source tree and update a cloud file with component mappings.

In each OWNERS file, a component and a team may be defined. This recipe calls
a script that gathers all the information onto a json file and refreshes a
world-readable cloud location.
"""

import copy
import re


DEPS = [
    'chromium_tests',
    'depot_tools/git',
    'depot_tools/gsutil',
    'recipe_engine/json',
    'recipe_engine/raw_io',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
]

_MAP_FILENAME = 'component_map.json'
_MAP_SUBDIRS_FILENAME = 'component_map_subdirs.json'

_SAMPLE_MAP = {
  "AAA-README": [
    "", "Dummy Readme"
  ],
  "component-to-team": {
    "Blink>DOM": "dom-dev@chromium.org",
    "Blink>Editing": "editing-dev@chromium.org",
    "Blink>Forms": "dom-dev@chromium.org",
    "Blink>HTML": "dom-dev@chromium.org",
    "Blink>HTML>Parser": "loading-dev@chromium.org",
    "Blink>PushAPI": "push-notifications-dev@chromium.org",
    "Blink>Scheduling": "scheduler-dev@chromium.org",
    "Blink>WebMIDI": "midi-dev@chromium.org",
    "Blink>XML": "dom-dev@chromium.org",
    "Internals>Network": "net-dev@chromium.org",
  },
  "dir-to-component": {
    "content/browser/loader": "Internals>Network",
    "content/browser/push_messaging": "Blink>PushAPI",
    "media/midi": "Blink>WebMIDI",
    "third_party/WebKit": "Blink",
    "third_party/WebKit/Source/core/dom": "Blink>DOM",
    "third_party/WebKit/Source/core/editing": "Blink>Editing",
    "third_party/WebKit/Source/core/html": "Blink>HTML",
    "third_party/WebKit/Source/core/html/forms": "Blink>Forms",
    "third_party/WebKit/Source/core/html/parser": "Blink>HTML>Parser",
    "third_party/WebKit/Source/core/xml": "Blink>XML",
    "third_party/WebKit/Source/modules/webmidi": "Blink>WebMIDI",
    "third_party/WebKit/Source/platform/scheduler": "Blink>Scheduling",
    "third_party/WebKit/Source/web/resources": "Blink>Forms",
    "third_party/WebKit/public/platform/modules/webmidi": "Blink>WebMIDI",
    "third_party/WebKit/public/platform/scheduler": "Blink>Scheduling"
  }
}


def RunStepsForFile(api, filename, extra_arguments, step_suffix):
  # Download existing map
  original_map_file = api.path['start_dir'].join('original_map.json')
  api.gsutil.download(
      'chromium-owners', filename, original_map_file,
      name='download original mapping' + step_suffix)

  original_map = api.json.read(
      'Parse original mapping' + step_suffix, original_map_file,
      step_test_data=lambda: api.json.test_api.output(_SAMPLE_MAP)).json.output

  # Run the script that does the actual work.
  try:
    modified_map_file = api.path['start_dir'].join('modified_map.json')
    command_path = api.path['checkout'].join(
        'tools', 'checkteamtags', 'extract_components.py')
    command_parts = [command_path, '-o', modified_map_file] + extra_arguments
    api.step(
        'Run component extraction script to generate mapping' + step_suffix,
        command_parts, stdout=api.raw_io.output_text())
  except api.step.StepFailure as sf:
    api.step.active_result.presentation.logs['extract_components errors'] = (
        sf.result.stdout.splitlines())
    raise

  modified_map = api.json.read(
      'Parse modified mapping' + step_suffix, modified_map_file,
      step_test_data=lambda: api.json.test_api.output(_SAMPLE_MAP)).json.output

  if original_map == modified_map:
    api.step('No changes in mapping' + step_suffix, [])
    return

  summary = []
  for map_key in ['dir-to-component', 'component-to-team']:
    # new keys
    for k in modified_map[map_key].keys():
      if k not in original_map[map_key].keys():
        summary.append('The key %s was added to the %s map' % (k, map_key))
      # changed keys
      elif original_map[map_key][k] != modified_map[map_key][k]:
        summary.append('The value for key %s in the %s map was modified from '
                       '%s to %s' % (k, map_key, original_map[map_key][k],
                                     modified_map[map_key][k]))
    # old keys
    for k in original_map[map_key].keys():
      if k not in modified_map[map_key].keys():
        summary.append('The key %s was removed from the %s map' % (k, map_key))

  if summary:
    api.step('Summary of changes in mapping' + step_suffix, [])
    api.step.active_result.presentation.logs['CHANGES'] = summary

  # Upload to GS
  api.gsutil.upload(modified_map_file, 'chromium-owners', filename,
                    link_name='Updated component map',
                    name='upload updated mapping' + step_suffix)

def RunSteps(api):
  # Replicate the config of a vanilla linux builder.
  bot_config = api.chromium_tests.create_bot_config_object(
      [api.chromium_tests.create_bot_id('chromium.linux', 'Linux Builder')])
  api.chromium_tests.configure_build(bot_config)
  api.chromium_tests.prepare_checkout(bot_config)

  RunStepsForFile(api, _MAP_FILENAME, [], '')
  RunStepsForFile(
      api, _MAP_SUBDIRS_FILENAME, ['--include-subdirs'], ' with subdirs')


def GenTests(api):
  yield (
      api.test('no_change')
      + api.properties.tryserver(
          mastername='chromium.linux',
          buildername='Linux Builder'))

  modified_map = copy.deepcopy(_SAMPLE_MAP)
  modified_map['dir-to-component']['media/mp3'] = 'ChromeWinamp>mp3'
  yield (
      api.test('addition')
      + api.override_step_data(
          'Parse modified mapping',
          api.json.output(modified_map))
      + api.properties.tryserver(
          mastername='chromium.linux',
          buildername='Linux Builder'))

  modified_map = copy.deepcopy(_SAMPLE_MAP)
  modified_map['dir-to-component']['media/mini/mici'] = 'Blink>WebMIDI'
  yield (
      api.test('addition_into_subdirs')
      + api.override_step_data(
          'Parse modified mapping with subdirs',
          api.json.output(modified_map))
      + api.properties.tryserver(
          mastername='chromium.linux',
          buildername='Linux Builder'))

  modified_map = copy.deepcopy(_SAMPLE_MAP)
  del(modified_map['dir-to-component']['media/midi'])
  yield (
      api.test('removal')
      + api.override_step_data(
          'Parse modified mapping',
          api.json.output(modified_map))
      + api.properties.tryserver(
          mastername='chromium.linux',
          buildername='Linux Builder'))

  modified_map = copy.deepcopy(_SAMPLE_MAP)
  modified_map['dir-to-component']['media/midi'] = 'ChromeWinamp>midi'
  yield (
      api.test('conflict')
      + api.override_step_data(
          'Parse modified mapping',
          api.json.output(modified_map))
      + api.properties.tryserver(
          mastername='chromium.linux',
          buildername='Linux Builder'))

  yield (
      api.test('script_error')
      + api.override_step_data(
          'Run component extraction script to generate mapping',
          retcode=1,
          stdout=api.raw_io.output_text('Dummy script error'))
      + api.properties.tryserver(
          mastername='chromium.linux',
          buildername='Linux Builder'))

  modified_map = copy.deepcopy(_SAMPLE_MAP)
  modified_map['dir-to-component']['media/mp3'] = 'ChromeWinamp>mp3'
  yield (
      api.test('failed_upload')
      + api.step_data(
          'gsutil upload updated mapping', retcode=1)
      + api.override_step_data(
          'Parse modified mapping',
          api.json.output(modified_map))
      + api.properties.tryserver(
          mastername='chromium.linux',
          buildername='Linux Builder'))
