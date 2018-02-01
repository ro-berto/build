# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Autoroller recipe for Android's AFDO profiles.

These profiles live in gs://, and are generated+vetted+uploaded by our Chrome OS
friends on a ~daily basis. This script tries to keep us on the latest one at all
times."""

import functools
import re

DEPS = [
  'depot_tools/git',
  'depot_tools/gsutil',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/path',
  'recipe_engine/raw_io',
  'recipe_engine/step',
]

_COMMIT_TBRS = ['agrieve@chromium.org', 'gbiv@chromium.org']
_GS_PROFILE_LOCATION = 'gs://chromeos-prebuilt/afdo-job/llvm'


def _PrettifyProfileName(profile_name):
  """Try to remove noise from the profile name."""
  prefix = 'chromeos-chrome-amd64-'
  assert profile_name.startswith(prefix)

  suffix = '.afdo.bz2'
  assert profile_name.endswith(suffix)
  return profile_name[len(prefix):-len(suffix)]


def _GenerateCommitMessage(previous_profile, new_profile):
  # Note for line length: previous_profile and new_profile are generally ~18
  # chars, e.g. "65.0.3322.0_rc-r1".
  lines = [
    '[AFDO] Roll Android\'s profile to %s' % new_profile,
    '',
    'Updating from %s.' % previous_profile,
    '',
    'This CL may cause a small binary size increase, roughly proportional',
    'to how long it\'s been since our last AFDO profile roll. For larger',
    'increases (around or exceeding 100KB), please file a bug against',
    'gbiv@chromium.org. Additional context: https://crbug.com/805539',
    '',
    'Bug: None',
    'Test: CQ',
  ]
  return '\n'.join(lines)


def _PickLatestProfile(api, remote_profile_listing):
  file_names = (api.path.basename(l.strip())
                for l in remote_profile_listing.splitlines())

  # Example name: chromeos-chrome-amd64-63.0.3239.57_rc-r1.afdo.bz2
  versioned_profile = re.compile('''^chromeos-chrome-amd64-      # Prefix
                                    \d+\.\d+\.(\d+)\.(\d+)       # Version
                                    _rc-r(\d+)                   # Revision
                                    \.afdo\.bz2$                 # Suffix''',
                                    re.VERBOSE)

  def _ParseFileName(file_name):
    m = versioned_profile.match(file_name)
    if not m:
      return None
    parsed_version = tuple(int(g) for g in m.groups())
    return parsed_version, file_name

  parsed_files = (_ParseFileName(file) for file in file_names)
  _, newest_profile_name = max(t for t in parsed_files if t)
  return newest_profile_name


def RunSteps(api):
  chromium_dir = api.path['start_dir'].join('chromium')
  api.git.checkout(
    'https://chromium.googlesource.com/chromium/src.git',
    dir_path=chromium_dir,
    recursive=False,
    submodules=False,
    step_suffix='chromium',
  )

  profile_version_loc = chromium_dir.join('chrome', 'android', 'profiles',
                                          'newest.txt')

  current_version = api.file.read_text(
    'Get current profile version',
    profile_version_loc,
  )
  current_version = current_version.strip()

  bucket_files = api.gsutil.list(
    _GS_PROFILE_LOCATION,
    name='list remote profiles',
    stdout=api.raw_io.output_text(),
  )

  latest_version = _PickLatestProfile(api, bucket_files.stdout)
  bucket_files.presentation.properties['latest_version'] = latest_version
  # This logically belongs on the 'Get current profile version' step above, but
  # putting it here is more convenient (both in code, and for inspecting bot
  # output).
  bucket_files.presentation.properties['current_version'] = current_version

  if latest_version == current_version:
    return

  with api.context(cwd=chromium_dir):
    # For local runs/persistent repos, kill any existing branch state with fire.
    branch_name = 'roll_afdo_profile'
    api.git(
      'branch',
      '-D',
      branch_name,
      can_fail_build=False,
      name='git delete old branch',
    )

    api.git.new_branch(branch_name, upstream='origin/master')

    pretty_current = _PrettifyProfileName(current_version)
    pretty_latest = _PrettifyProfileName(latest_version)

    api.file.write_text(
      'Write new profile name',
      profile_version_loc,
      latest_version+'\n',
    )

    git_config_options = {
      'user.email': 'android-afdo-autoroller@chromium.org',
      'user.name': 'Android AFDO Autoroller',
    }

    commit_msg = _GenerateCommitMessage(pretty_current, pretty_latest)
    api.git(
      'commit',
      profile_version_loc,
      '--message', commit_msg,
      name='git commit',
      git_config_options=git_config_options,
    )

    # git_cl.py, which api.git_cl uses, doesn't like config params passed via
    # -c.
    api.git(
      'cl',
      'upload',
      # Hooks might try to use parts of the Chrome tree that we didn't pull.
      # Since there's nothing they can really do for us anyway, disable
      # them.
      '--bypass-hooks',
      '--message=%s' % commit_msg,
      '--tbrs=%s' % ','.join(_COMMIT_TBRS),
      '--force',
      '--use-commit-queue',
      name='git cl upload',
      git_config_options=git_config_options,
    )


def _GenProfileListing(profile_name):
  suffix = '.afdo.bz2'
  assert profile_name.endswith(suffix)

  other_file = profile_name[:-len(suffix)] + '.not-profile.bz2'

  def path(x):
    return _GS_PROFILE_LOCATION + '/' + x

  # Any names that aren't profile_name or other_file are either invalid profile
  # names, or they're older than any existing test data (and so shouldn't show
  # up).
  lines = [
    '',
    path('chromeos-chrome-amd64-57.0.270.0_rc-r1.afdo.bz2'),
    path('chromeos-chrome-amd64-57.0.2970.0_rc-r1.not-profile.bz2'),
    path('chromeos-chrome-amd64-57.0.2970.0_rc-r1.afdo.bz2'),
    path('chromeos-chrome-amd64-57.0.2980.0_rc-r1.afdo.bz2'),
    path('chromeos-chrome-amd64-57.0.299Z.0_rc-r1.afdo.bz2'),
    path(profile_name),
    path(other_file),
    '',
  ]
  return '\n'.join(lines)


def GenTests(api):
  def _GenAPITest(name, current_version, remote_version):
    return (
      api.test(name)
      + api.step_data(
        'Get current profile version',
        api.file.read_text(current_version),
      )
      + api.step_data(
        'gsutil list remote profiles',
        stdout=api.raw_io.output_text(_GenProfileListing(remote_version)),
      )
    )

  profile_name = 'chromeos-chrome-amd64-65.0.3322.0_rc-r1.afdo.bz2'
  rev_newer_profile_name = 'chromeos-chrome-amd64-65.0.3322.0_rc-r2.afdo.bz2'
  newer_profile_name = 'chromeos-chrome-amd64-65.0.3322.1_rc-r1.afdo.bz2'
  much_newer_profile_name = 'chromeos-chrome-amd64-65.0.10000.1_rc-r1.afdo.bz2'

  yield _GenAPITest(
    name='remote_same',
    current_version=profile_name,
    remote_version=profile_name,
  )

  yield _GenAPITest(
    name='remote_newer',
    current_version=profile_name,
    remote_version=newer_profile_name,
  )

  yield _GenAPITest(
    name='remote_newer_rev',
    current_version=profile_name,
    remote_version=rev_newer_profile_name,
  )

  yield _GenAPITest(
    name='remote_much_newer',
    current_version=profile_name,
    remote_version=much_newer_profile_name,
  )

  yield (
    _GenAPITest(
      name='no_old_branch_to_delete',
      current_version=profile_name,
      remote_version=newer_profile_name,
    )
    + api.step_data(
      'git delete old branch',
      retcode=1,
    )
  )
