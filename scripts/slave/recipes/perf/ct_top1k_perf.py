# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


DEPS = [
  'archive',
  'ct_swarming',
  'file',
  'path',
  'properties',
  'step',
  'time',
]


CT_PAGE_TYPE = '1k'
CT_BINARY = 'run_chromium_perf_swarming'
CT_ISOLATE = 'ct_top1k.isolate'

# Number of slaves to shard CT runs to.
DEFAULT_CT_NUM_SLAVES = 100


def _DownloadAndExtractBinary(api):
  """Downloads the binary from the revision passed to the recipe."""
  api.archive.download_and_unzip_build(
      step_name='Download and Extract Binary',
      target='Release',
      build_url=None,  # This is a required parameter, but has no effect.
      build_archive_url=api.properties['parent_build_archive_url'])


def RunSteps(api):
  # Figure out which benchmark to use.
  buildername = api.properties['buildername']
  if 'Repaint' in buildername:
    benchmark = 'repaint'
  elif 'RR' in buildername:
    benchmark = 'rasterize_and_record_micro'
  else:
    raise Exception('Do not recognise the buildername %s.' % buildername)

  # Checkout chromium and swarming.
  api.ct_swarming.checkout_dependencies()

  # Download the prebuilt chromium binary.
  _DownloadAndExtractBinary(api)

  # Download Cluster Telemetry binary.
  api.ct_swarming.download_CT_binary(CT_BINARY)

  # Record how long the step took in swarming tasks.
  swarming_start_time = api.time.time()

  ct_num_slaves = api.properties.get('ct_num_slaves', DEFAULT_CT_NUM_SLAVES)
  for slave_num in range(1, ct_num_slaves + 1):
    # Download page sets and archives.
    api.ct_swarming.download_page_artifacts(CT_PAGE_TYPE, slave_num)

    # Create this slave's isolated.gen.json file to use for batcharchiving.
    isolate_dir = api.path['checkout'].join('chrome')
    isolate_path = isolate_dir.join(CT_ISOLATE)
    extra_variables = {
        'SLAVE_NUM': str(slave_num),
        'MASTER': api.properties['mastername'],
        'BUILDER': api.properties['buildername'],
        'GIT_HASH': api.properties['git_revision'],
        'BENCHMARK': benchmark,
    }
    api.ct_swarming.create_isolated_gen_json(
        isolate_path, isolate_dir, 'linux', slave_num, extra_variables)

  # Batcharchive everything on the isolate server for efficiency.
  api.ct_swarming.batcharchive(ct_num_slaves)
  swarm_hashes = (
      api.step.active_result.presentation.properties['swarm_hashes']).values()

  # Trigger all swarming tasks.
  tasks = api.ct_swarming.trigger_swarming_tasks(
      swarm_hashes, task_name_prefix='ct-1k-task',
      dimensions={'os': 'Ubuntu', 'gpu': '10de'})

  # Now collect all tasks.
  api.ct_swarming.collect_swarming_tasks(tasks)

  print ('Running isolating, triggering and collecting swarming tasks took a '
         'total of %s seconds') % (api.time.time() - swarming_start_time)


def GenTests(api):
  mastername = 'chromium.perf.fyi'
  slavename = 'test-slave'
  parent_build_archive_url = 'http:/dummy-url.com'
  parent_got_swarming_client_revision = '12345'
  git_revision = 'xy12z43'
  ct_num_slaves = 5

  yield(
    api.test('CT_Top1k_RR') +
    api.properties(
        buildername='Linux CT Top1k RR Perf',
        mastername=mastername,
        slavename=slavename,
        parent_build_archive_url=parent_build_archive_url,
        parent_got_swarming_client_revision=parent_got_swarming_client_revision,
        git_revision=git_revision,
        ct_num_slaves=ct_num_slaves,
    )
  )

  yield(
    api.test('CT_Top1k_Repaint') +
    api.properties(
        buildername='Linux CT Top1k Repaint Perf',
        mastername=mastername,
        slavename=slavename,
        parent_build_archive_url=parent_build_archive_url,
        parent_got_swarming_client_revision=parent_got_swarming_client_revision,
        git_revision=git_revision,
        ct_num_slaves=ct_num_slaves,
    )
  )

  yield(
    api.test('CT_Top1k_Unsupported') +
    api.properties(
        buildername='Linux CT Top1k Unsupported Perf',
        mastername=mastername,
        slavename=slavename,
        parent_build_archive_url=parent_build_archive_url,
        parent_got_swarming_client_revision=parent_got_swarming_client_revision,
        git_revision=git_revision,
        ct_num_slaves=ct_num_slaves,
    ) +
    api.expect_exception('Exception')
  )

  yield(
    api.test('CT_Top1k_slave3_failure') +
    api.step_data('ct-1k-task-3 on Ubuntu', retcode=1) +
    api.properties(
        buildername='Linux CT Top1k RR Perf',
        mastername=mastername,
        slavename=slavename,
        parent_build_archive_url=parent_build_archive_url,
        parent_got_swarming_client_revision=parent_got_swarming_client_revision,
        git_revision=git_revision,
        ct_num_slaves=ct_num_slaves,
    )
  )
