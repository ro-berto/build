# -*- coding: utf-8 -*-
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This recipe is used to keep Chrome's pools of CrOS DUTs up to date.

It does so by launching tasks into the DUT pools which flash the devices.
When ran, this recipe aims to get a portion of a given pool on the latest
CHROMEOS_LKGM version. It will never flash more than a third of the pool at a
single time. This is to ensure the remainder of the pool is online for tests.
Consequently, this recipe will need to be run multiple times to upgrade the
entire pool.

This recipe is intended to run several times during MTV's off-peak hours. Its
builder should be backed by a single thin Ubuntu VM, while the tasks it launches
run the cros_flash recipe and run on DUT swarming bots.
"""

import base64
import re

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

DEPS = [
  'depot_tools/gitiles',
  'depot_tools/gsutil',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'recipe_engine/tempfile',
  'swarming_client',
]

# The gitiles url of the CHROMEOS_LKGM file. This file represents the latest
# version of ChromeOS compatible with Chromium's trunk. The contents of this
# file control what version of CrOS to flash the DUT pools to.
CHROMEOS_LKGM_REPO_URL = 'https://chromium.googlesource.com/chromium/src'
CHROMEOS_LKGM_FILE_PATH = 'chromeos/CHROMEOS_LKGM'

# Should match something that looks like "12345.0.0".
LKGM_RE = re.compile(r'\d+\.\d+\.\d+')

# GS bucket that stores test images for all CrOS boards.
CHROMEOS_IMAGE_BUCKET = 'chromeos-image-archive'

# The name of the builder to which every DUT swarming bot belongs. This builder
# exists solely so the bots can run the cros_flash recipe.
DUT_FLASHING_BUILDER = 'cros-dut-flash'

PROPERTIES = {
  'swarming_server': Property(
      kind=str,
      help='Swarming server of the DUT pool to flash.'),
  'swarming_pool': Property(
      kind=str,
      help='Swarming pool of the DUT pool to flash.'),
  'device_type': Property(
      kind=str,
      help='DUT type (ie: CrOS board) of the DUT pool to flash.'),
  'bb_host': Property(
      kind=str,
      help='Buildbucket host to use when triggering flashing jobs.',
      default=None)
}


def get_bots_in_pool(api, swarming_server, pool, device_type):
  """Returns the list of bots that belong to the given pool.

  This uses swarming.py's bot/list query, and returns the resulting bots.
  """
  # TODO(crbug.com/866062): Pass down a service account if a pool ever needs it.
  cmd = [
    'query',
    '-S', swarming_server,
    'bots/list?dimensions=device_type:%s&dimensions=pool:%s' % (
        device_type, pool)
  ]
  result = api.python('get all bots',
      api.swarming_client.path.join('swarming.py'),
      cmd, stdout=api.json.output())
  if not result.stdout or len(result.stdout.get('items', [])) == 0:
    result.presentation.status = api.step.WARNING
    return [], result
  all_bots = [
      DUTBot(swarming_server, bot_dict) for bot_dict in result.stdout['items']
  ]
  result.presentation.logs['found %d bots' % len(all_bots)] = (
      b.id for b in all_bots)
  return all_bots, result


class DUTBot(object):

  def __init__(self, swarming_url, swarming_dict):
    self.swarming_url = swarming_url
    self.id = swarming_dict['bot_id']
    self.is_unhealthy = swarming_dict['quarantined'] or swarming_dict['is_dead']
    self.os = 'unknown'
    # Swarming returns a bot's dimensions as a list of dicts like:
    # { 'key': 'dimension_name', 'value': ['dimension_value'] } ... 🤷
    for d in swarming_dict['dimensions']:
      if d['key'] == 'device_os':
        self.os = d['value'][0]
        break


def get_closest_available_version(api, board, lkgm_base):
  """Returns the GS path of the latest image for the given board and lkgm.

  This finds the first LATEST-$lkgm file in GS closest to the current lkgm.
  It'll decrement the lkgm until it finds one, up to 100 attempts. This logic
  is taken from:
  https://codesearch.chromium.org/chromium/src/third_party/chromite/cli/cros/cros_chrome_sdk.py?rcl=63924982b3fdaf3c313e0052fe0c07dae5e4628a&l=350

  Once it finds a valid LATEST-$lkgm file, it returns its contents appended
  to the board's directory in the GS image bucket, which contains the images
  built for that board at that version.
  (eg: gs://chromeos-image-archive/kevin-full/R72-11244.0.0-rc2/)
  """
  # Append '-full' to every board, which indicates we want public versions
  # of the board's images.
  # TODO(crbug.com/866062): Support private images (if we ever want them).
  board += '-full'
  gs_path_prefix = 'gs://%s/%s/' % (CHROMEOS_IMAGE_BUCKET, board)
  with api.step.nest('find latest image at %s' % lkgm_base):
    # Occasionally an image won't be available for the board at the current
    # LKGM. So start decrementing the version until we find one that's
    # available.
    lkgm_base = int(lkgm_base)
    for candidate_version in xrange(lkgm_base, lkgm_base-100, -1):
      full_version_file_path = gs_path_prefix + 'LATEST-%d.0.0' % (
          candidate_version)
      try:
        # Only retry the gsutil calls for the first 5 attempts.
        should_retry = candidate_version > lkgm_base - 5
        result = api.gsutil.cat(
            full_version_file_path, name='cat LATEST-%d' % candidate_version,
            use_retry_wrapper=should_retry, stdout=api.raw_io.output(),
            infra_step=False)
        return gs_path_prefix + result.stdout.strip()
      except api.step.StepFailure:
        pass  # Gracefully skip 404s.
  return None


def trigger_flash(api, bot, pool, gs_image_path):
  build_req = {
    'bucket': pool,
    'parameters': {
      'builder_name': DUT_FLASHING_BUILDER,
      'properties': {
        'gs_image_bucket': CHROMEOS_IMAGE_BUCKET,
        # gs_image_path expects everything to the right of the bucket name
        'gs_image_path': gs_image_path.split(CHROMEOS_IMAGE_BUCKET+'/')[1],
      },
      'swarming': {
        'override_builder_cfg': {
          'dimensions': [
            'id:%s' % bot.id,
            # Append the device's current OS to the request. This
            # ensures that if its OS changes unexpectedly, we don't
            # overwrite it.
            'device_os:%s' % bot.os,
          ],
        },
      },
    },
  }
  result = api.buildbucket.put([build_req], name=bot.id)
  build_id = result.stdout['results'][0]['build']['id']
  build_url = result.stdout['results'][0]['build']['url']
  result.presentation.links[build_id] = build_url
  return build_id


def RunSteps(api, swarming_server, swarming_pool, device_type, bb_host):
  api.swarming_client.checkout(revision='master')

  if bb_host:
    api.buildbucket.set_buildbucket_host(bb_host)

  # Curl the current CHROMEOS_LKGM pin. Don't bother with a full chromium
  # checkout since all we need is that one file.
  lkgm = api.gitiles.download_file(
      CHROMEOS_LKGM_REPO_URL, CHROMEOS_LKGM_FILE_PATH,
      step_name='fetch CHROMEOS_LKGM')
  if not LKGM_RE.match(lkgm):
    api.python.failing_step('unknown CHROMEOS_LKGM format',
        'The only supported format for the LKGM file is "12345.0.0". Its '
        'contents currently are "%s".' % lkgm)
  api.step.active_result.presentation.step_text = 'current LKGM: %s ' % lkgm
  lkgm_base = lkgm.split('.')[0]

  # Fetch the full path in GS for the board at the current lkgm.
  latest_version = get_closest_available_version(api, device_type, lkgm_base)
  if not latest_version:
    api.python.failing_step('no available image at %s' % lkgm, '')
  gs_image_path = latest_version + '/chromiumos_test_image.tar.xz'
  # Do a quick GS ls to ensure the image path exists.
  api.gsutil.list(gs_image_path, name='ls ' + gs_image_path)

  # Collect the number of bots in the pool that need to be flashed.
  all_bots, step_result  = get_bots_in_pool(
      api, swarming_server, swarming_pool, device_type)
  if not all_bots:
    api.python.failing_step('no bots online', '')

  unhealthy_bots = []
  up_to_date_bots = []
  out_of_date_bots = []
  for bot in all_bots:
    if bot.is_unhealthy:
      unhealthy_bots.append(bot)
      continue
    if bot.os != lkgm_base:
      out_of_date_bots.append(bot)
    else:
      up_to_date_bots.append(bot)

  # Add logs entries that list all bots that belong to each category.
  if unhealthy_bots:
    step_result.presentation.logs['unhealthy bots'] = (
        b.id for b in unhealthy_bots)
  if up_to_date_bots:
    step_result.presentation.logs['up to date bots'] = (
        b.id for b in up_to_date_bots)
  if out_of_date_bots:
    step_result.presentation.logs['out of date bots'] = (
        b.id for b in out_of_date_bots)
  else:
    step_result.presentation.logs['all bots up to date!'] = [
        'No flashes are necessary since all bots are up to date.']
    return

  # Select a subset (of at least 10 and up to 33%) of the DUTs to flash.
  # This ensures that at least 67% of the pool stays online so tests can
  # continue to run.
  num_available_bots = len(up_to_date_bots) + len(out_of_date_bots)
  max_num_to_flash = max(num_available_bots / 3, 10)
  bots_to_flash = out_of_date_bots[0:max_num_to_flash]
  flashing_requests = set()
  with api.step.nest('flash bots'):
    for bot in bots_to_flash:
      flashing_requests.add(
          trigger_flash(api, bot, swarming_pool, gs_image_path))

  # Wait for all the flashing jobs. Nest it under a single step since there
  # will be several buildbucket.get_build() step calls.
  finished_builds = []
  with api.step.nest('wait for %d flashing jobs' % len(flashing_requests)):
    # Sleep indefinitely if the jobs never finish. Let swarming's task timeout
    # kill us if we won't exit.
    while flashing_requests:
      api.python.inline('sleep for 1 min', 'import time; time.sleep(60)')
      for build in flashing_requests.copy():
        result = api.buildbucket.get_build(build)
        if result.stdout['build']['status'] == 'COMPLETED':
          finished_builds.append(result.stdout['build'])
          flashing_requests.remove(build)

  # TODO(bpastene): Retrigger the recipe if:
  # - all triggered flash jobs were successful
  # - all bots that were flashed are back up and healthy
  # - there are more bots that need flashing


def GenTests(api):
  def bot_json(bot_id, os, quarantined=False):
    return {
      'bot_id': bot_id,
      'quarantined': quarantined,
      'is_dead': False,
      'dimensions': [
        {
          'key': 'device_os',
          'value': [os],
        }
      ]
    }

  def bb_json_get(build_id, finished=True, result='SUCCESS'):
    build = {
      'build': {
        'id': build_id,
        'status': 'COMPLETED' if finished else 'RUNNING',
        'url': 'https://some.build.url',
      }
    }
    if finished:
      build['build']['result'] = result
    return build

  def bb_json_put(build_id):
    return {
      'results': [
        {
          'build': {
            'id': build_id,
            'url': 'https://some.build.url',
          }
        }
      ]
    }

  def test_props(name, include_lkgm_steps=True):
    test = (
      api.test(name) +
      api.platform('linux', 64) +
      api.properties(
        swarming_server='some-swarming-server',
        swarming_pool='some-swarming-pool',
        device_type='some-device-type',
        bb_host='some-buildbucket-server')
    )
    if include_lkgm_steps:
      test += (
        api.override_step_data(
            'fetch CHROMEOS_LKGM',
            api.json.output({ 'value': base64.b64encode('12345.0.0') }))
      )
    return test

  yield (
    test_props('full_run') +
    api.step_data(
        'get all bots',
        stdout=api.json.output({
          'items': [
            bot_json('up_to_date_bot', '12345'),
            bot_json('out_of_date_bot', '11111'),
            bot_json('unhealthy_bot', '12345', quarantined=True),
          ]
        })) +
    api.step_data(
        'flash bots.out_of_date_bot',
        stdout=api.json.output(bb_json_put('1234567890'))) +
    # Build finises after the third buildbucket query.
    api.step_data(
        'wait for 1 flashing jobs.buildbucket.get',
        stdout=api.json.output(bb_json_get('1234567890', finished=False))) +
    api.step_data(
        'wait for 1 flashing jobs.buildbucket.get (2)',
        stdout=api.json.output(bb_json_get('1234567890', finished=False))) +
    api.step_data(
        'wait for 1 flashing jobs.buildbucket.get (3)',
        stdout=api.json.output(bb_json_get('1234567890'))) +
    api.post_process(post_process.StatusSuccess)
  )

  yield (
    test_props('wrong_lkgm_format', include_lkgm_steps=False) +
    api.override_step_data(
        'fetch CHROMEOS_LKGM',
        api.json.output({ 'value': base64.b64encode('this-is-wrong') })) +
    api.post_process(post_process.MustRun, 'unknown CHROMEOS_LKGM format') +
    api.post_process(post_process.StatusFailure) +
    api.post_process(post_process.DropExpectation)
  )

  retry_test = (
    test_props('exhaust_all_gs_retries', include_lkgm_steps=False) +
    api.override_step_data(
        'fetch CHROMEOS_LKGM',
        api.json.output({ 'value': base64.b64encode('99999.0.0') })) +
    api.post_process(post_process.MustRun, 'no available image at 99999.0.0') +
    api.post_process(post_process.StatusFailure) +
    api.post_process(post_process.DropExpectation)
  )
  # gsutil calls return non-zero for all 100 attempts.
  for i in xrange(100):
    next_ver = 99999 - i
    step_name = 'find latest image at 99999.gsutil cat LATEST-%d' % next_ver
    retry_test += api.step_data(step_name, retcode=1)
  yield retry_test

  yield (
    test_props('no_bots') +
    api.step_data(
        'get all bots',
        stdout=api.json.output({'items': []})) +
    api.post_process(post_process.MustRun, 'no bots online') +
    api.post_process(post_process.StatusFailure) +
    api.post_process(post_process.DropExpectation)
  )

  yield (
    test_props('no_flashing_needed') +
    api.step_data(
        'get all bots',
        stdout=api.json.output({
          'items': [
            bot_json('bot2', '12345'),
            bot_json('bot1', '12345'),
          ]
        })) +
    api.post_process(post_process.StatusSuccess) +
    api.post_process(post_process.DropExpectation)
  )
