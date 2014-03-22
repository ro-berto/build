# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'gclient',
  'gsutil',
  'path',
  'step',
  'step_history',
]


def GenSteps(api):
  api.chromium.set_config('chromium')
  yield api.gclient.checkout()

  harness_file = 'telemetry-%s.zip' % (
      api.step_history['gclient sync'].json.output[
          'solutions']['src/']['revision'],)
  harness_path = api.path.mkdtemp('telemetry-harness')

  yield api.step('create harness archive', [
                   api.path['checkout'].join(
                       'tools', 'telemetry', 'build',
                       'generate_telemetry_harness.sh'),
                   harness_path.join(harness_file),
                 ]
  )

  bucket = 'chromium-telemetry'
  cloud_file = 'snapshots/%s' % harness_file
  yield api.gsutil.upload(harness_path.join(harness_file), bucket, cloud_file)
  yield api.path.rmtree('remove harness temp directory', harness_path)


def GenTests(api):
  yield api.test('basic')
