# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Buildbot recipe definition for the various Crashpad continuous builders.
"""

import datetime

DEPS = [
    'chromium',  # to import gclient configs
    'chromium_checkout',
    'depot_tools/gclient',
    'recipe_engine/buildbucket',
    'recipe_engine/cipd',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/futures',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/step',
    'recipe_engine/time',
]

MODEL_CIPD_PACKAGE = 'chromium/rts/model'
RTS_EXEC_PACKAGE = 'chromium/rts/rts-chromium/${platform}'
REJECTION_DATA_WINDOW = datetime.timedelta(weeks=12)
TEST_DURATION_DATA_WINDOW = datetime.timedelta(weeks=1)
# Processing 10% of 1w-worth test durations takes 7h on a 32-core bot.
TEST_DURATION_DATA_PERCENTAGE = 1
RTS_EXECUTABLE_VERSION = 'latest'


def RunSteps(api):
  # Start bot_update in background.
  checkout_dir_fut = api.futures.spawn_immediate(checkout_chromium, api)

  # Install rts-chromium.
  exec_path = api.cipd.ensure_tool(RTS_EXEC_PACKAGE, RTS_EXECUTABLE_VERSION)

  # Fetch the dataset.
  # Ignore today because we might fetch incomplete data.
  yesterday = api.time.utcnow().date() - datetime.timedelta(days=1)
  rejections_dir, durations_dir = _fetch_model_data(
      api,
      exec_path,
      rejection_date_range=(
          yesterday - REJECTION_DATA_WINDOW,
          yesterday,
      ),
      duration_date_range=(
          yesterday - TEST_DURATION_DATA_WINDOW,
          yesterday,
      ),
  )

  # Create the model.
  checkout_dir = checkout_dir_fut.result()
  model_dir = api.path['cleanup'].join('rts-chromium-model')
  api.step(
      'create-model',
      [
        exec_path, 'create-model', \
        '-checkout', str(checkout_dir),
        '-rejections', str(rejections_dir), \
        '-durations', str(durations_dir), \
        '-model-dir', str(model_dir),
      ],
  )

  # TODO(crbug.com/1172372): ensure the new model is not significantly worse
  # than the current one.

  # Add the executable to the model.
  exe_ext = '.exe' if api.platform.is_win else ''
  api.file.copy(
      'add rts-chromium to the model',
      exec_path,
      model_dir.join('rts-chromium' + exe_ext),
  )

  # Upload to CIPD.
  api.cipd.create_from_pkg(
      api.cipd.PackageDefinition(
          package_name=MODEL_CIPD_PACKAGE,
          package_root=model_dir,
      ),
      refs=['latest'],
      tags={
          'build': 'https://ci.chromium.org/b/%d' % api.buildbucket.build.id,
      },
  )


def checkout_chromium(api):
  """Checks out chromium/src and returns its path."""
  api.gclient.set_config('chromium_empty')
  api.chromium_checkout.ensure_checkout()
  return api.chromium_checkout.checkout_dir.join('src')


def _fetch_model_data(api, exec_path, rejection_date_range,
                      duration_date_range):
  """Fetches the data for model creation.

  Returns:
    A tuple (rejections_dir, durations_dir) with path to the directories with
    rejections and durations respectively.
  """
  data_dir = api.path['cleanup'].join('rts-chromium-model-data')
  rejections_dir = data_dir.join('rejections')
  durations_dir = data_dir.join('durations')

  futures = api.futures.wait([
    api.futures.spawn_immediate(
        api.step,
        'fetch rejections',
        [
          str(exec_path), 'fetch-rejections', \
          '-out', str(rejections_dir),
        ] + _date_range_flags(rejection_date_range),
    ),
    api.futures.spawn_immediate(
        api.step,
        'fetch durations',
        [
          str(exec_path), 'fetch-durations', \
          '-frac', '%.3f' % (TEST_DURATION_DATA_PERCENTAGE/100.0), \
          '-out', str(durations_dir),
        ] + _date_range_flags(duration_date_range),
    ),
  ])

  # Check future's exception.
  for f in futures:
    f.result()

  return rejections_dir, durations_dir


def _date_range_flags(date_range):
  from_date, to_date = date_range
  return [
    '-from', from_date.strftime('%Y-%m-%d'), \
    '-to', to_date.strftime('%Y-%m-%d'),
  ]


def GenTests(api):
  yield api.test('basic')
