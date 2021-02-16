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

MODEL_CIPD_PREFIX = 'chromium/rts/model/'
RTS_EXEC_CIPD_PREFIX = 'chromium/rts/rts-chromium/'
PLATFORMS = [
    'linux-amd64',
    'mac-amd64',
    'windows-amd64',
]
REJECTION_DATA_WINDOW = datetime.timedelta(weeks=12)
TEST_DURATION_DATA_WINDOW = datetime.timedelta(weeks=1)
# Processing 10% of 1w-worth test durations takes 7h on a 32-core bot.
TEST_DURATION_DATA_PERCENTAGE = 1


def RunSteps(api):
  # Start bot_update in background.
  checkout_dir_fut = api.futures.spawn_immediate(checkout_chromium, api)

  # Install rts-chromium executables.
  exec_pkg_paths = install_rts_executables(api)

  assert api.platform.is_linux
  assert api.platform.arch == 'intel'
  assert api.platform.bits == 64
  exec_path = exec_pkg_paths['linux-amd64'].join('rts-chromium')

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

  # Create CIPD packages.
  futures = []
  with api.step.nest('Create CIPD packages'):
    for platform, pkg_dir in exec_pkg_paths.iteritems():
      futures.append(
          api.futures.spawn_immediate(create_cipd_package, api, platform,
                                      pkg_dir, model_dir))
  # Check success.
  for f in futures:
    f.result()


def create_cipd_package(api, platform, exec_pkg_dir, model_dir):
  with api.step.nest('Upload CIPD package - %s' % platform):
    # Copy the model files, such that create_cipd_package can be called for
    # different platforms concurrently.
    # Note that we add a platform-specific executable below.
    pkg_dir = api.path['cleanup'].join('model-pkg-dir', platform)
    api.file.copytree('Copy the model files', model_dir, pkg_dir)

    # Add the executable to the model.
    exe_ext = '.exe' if platform.startswith('windows-') else ''
    exe_base_name = 'rts-executable' + exe_ext
    api.file.copy(
        'Include the executable',
        exec_pkg_dir.join(exe_base_name),
        pkg_dir.join(exe_base_name),
    )

    # Upload to CIPD.
    pkg = api.cipd.PackageDefinition(
        package_name=MODEL_CIPD_PREFIX + platform,
        package_root=pkg_dir,
    )
    pkg.add_dir(pkg_dir)
    api.cipd.create_from_pkg(
        pkg,
        refs=['latest'],
        tags={
            'build': 'https://ci.chromium.org/b/%d' % api.buildbucket.build.id,
        },
    )


def install_rts_executables(api):
  """Installs rts-chromium executables for all platforms.

  Returns:
    Mapping {platform: package_path}, where
    - platform is a CIPD platform, e.g. "linux-amd64".
    - package_path is a api.path.Path object.
  """
  ver = pick_executable_version(api)
  install_dir = api.path['cleanup'].join('rts-chromium')

  ret = {}
  ensure_file = api.cipd.EnsureFile()
  for plat in PLATFORMS:
    ensure_file.add_package(
        name=RTS_EXEC_CIPD_PREFIX + plat,
        version=ver,
        subdir=plat,
    )
    ret[plat] = install_dir.join(plat)

  api.cipd.ensure(install_dir, ensure_file, name='install RTS executables')
  return ret


def pick_executable_version(api):
  """Returns the CIPD version of rts-executable CIPD packages to use."""

  # Find the git_revision of the latest linux-amd64 package.
  # This guarantees that packages for all platforms are built from the same
  # source code.
  descr = api.cipd.describe(
      RTS_EXEC_CIPD_PREFIX + 'linux-amd64',
      'latest',
      test_data_tags=['git_revision:c1ee0e03d15281730ebedf1f7151474f7a523001'],
  )

  # Pick any git_revision.
  # It doesn't matter which one if they produced the same instance hash.
  for t in descr.tags:
    if t.tag.startswith('git_revision:'):
      return t.tag

  raise api.step.StepFailure(
      # pragma: no cover
      'git_revision tag not found in '
      'https://chrome-infra-packages.appspot.com/p/'
      'chromium/rts/rts-chromium/linux-amd64/+/latest')


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
  linux_amd64 = (
      api.platform.name('linux') + \
      api.platform.arch('intel') +
      api.platform.bits(64))

  yield api.test('basic') + linux_amd64
