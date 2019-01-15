#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import collections
import contextlib
import copy
import itertools
import json
import logging
import os
import subprocess
import sys
import tempfile
import urllib


# Install Infra build environment.
BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
                             os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BUILD_ROOT, 'scripts'))

# calling common.env.Install() globally causes annotated_run recipes to
# crash because it installs the system python lib path(s) to PYTHONPATH,
# which don't mix well with the bundled python we use. Doing it this way
# will allow us to load what we need, without polluting PYTHONPATH permanently.
import common.env
with common.env.GetInfraPythonPath().Enter():
  import httplib2
  from oauth2client import gce
  from oauth2client.client import GoogleCredentials

from common import annotator
from common import chromium_utils
from slave import cipd
from slave import infra_platform
from slave import logdog_bootstrap
from slave import monitoring_utils
from slave import robust_tempdir
from slave import update_scripts


# BuildBot root directory: /b
BUILDBOT_ROOT = os.path.abspath(os.path.dirname(BUILD_ROOT))


LOGGER = logging.getLogger('remote_run')


# Masters that are running "canary" run.
_CANARY_MASTERS = set((
  'chromium.infra.cron',
  'internal.infra',
  'internal.infra.cron',

  # Volunteered by bpastene@ as a generically representative waterfall that is
  # not a big deal if it breaks.
  'chromium.swarm',
))

# If the build is a CQ dry run, and the blamelist contains one of these
# usernames, the build will automatically opt-in to Kitchen.
_OPT_IN_USERS = set([
      'user:%s@%s' % (ldap, domain) for ldap, domain in itertools.product(
        (
          # Chrome Infrastructure Team Members
          'dnj', 'iannucci', 'hinoka', 'nodir', 'vadimsh', 'estaab', 'smut',
        ),
        ('chromium.org', 'google.com')
      )
])

# The name of the recipe engine CIPD package.
_RECIPES_PY_CIPD_PACKAGE = 'infra/recipes-py'
# The name of the Kitchen CIPD package.
_KITCHEN_CIPD_PACKAGE = 'infra/tools/luci/kitchen/${platform}'

# _CIPD_PINS is a mapping of master name to pinned CIPD package version to use
# for that master.
#
# If "kitchen" pin is empty, use the traditional "recipes.py" invocation path.
# Otherwise, use Kitchen.
# TODO(dnj): Remove this logic when Kitchen is always enabled.
CipdPins = collections.namedtuple('CipdPins', ('recipes', 'kitchen'))

# Stable CIPD pin set.
_STABLE_CIPD_PINS = CipdPins(
      recipes='git_revision:6eaacf24833ebd2565177157d368da33780fced9',
      kitchen='git_revision:c9c1865b81113f02fd618259624170f59e2c832e')

# Canary CIPD pin set.
_CANARY_CIPD_PINS = CipdPins(
      recipes='git_revision:6eaacf24833ebd2565177157d368da33780fced9',
      kitchen='git_revision:c9c1865b81113f02fd618259624170f59e2c832e')


def _ensure_directory(*path):
  path = os.path.join(*path)
  if not os.path.isdir(path):
    os.makedirs(path)
  return path


def _try_cleanup(src, cleanup_dir):
  """Stages the "src" file or directory for removal via "cleanup_dir".

  The "cleanup_dir" is a BuildBot-provided facility that deletes files
  in between builds. Moving files into this directory completes instantly. As
  opposed to deleting in "remote_run" or a lower layer, deletions via
  "cleanup_dir" happen in between builds, meaning that the overhead and
  expense aren't subject to I/O timeout and don't affect actual build times.

  NOTE: We rely on "cleanup_dir" to be on the same filesystem as the source
  directories, which is the case for BuildBot builds.
  """
  if not os.path.isdir(cleanup_dir):
    LOGGER.warning('Cleanup directory does not exist: %r', cleanup_dir)
    return

  base = os.path.basename(src)
  target_dir = tempfile.mkdtemp(prefix=base, dir=cleanup_dir)
  dst = os.path.join(target_dir, base)

  LOGGER.info('Moving file to cleanup directory %r => %r', src, dst)
  try:
    os.rename(src, dst)
  except Exception:
    LOGGER.exception('Failed to cleanup path %r', src)


def _get_is_canary(mastername):
  return mastername in _CANARY_MASTERS


def find_python():
  if sys.platform == 'win32':
    candidates = ['python.exe', 'python.bat']
  else:
    candidates = ['python']

  path_env = os.environ.get('PATH', '')
  for base in path_env.split(os.pathsep):
    for c in candidates:
      path = os.path.join(base, c)
      if os.path.isfile(path) and os.access(path, os.F_OK|os.X_OK):
        return os.path.abspath(path)

  LOGGER.warning('Could not find Python in PATH: %r', path_env)
  return sys.executable


def get_is_opt_in(properties):
  """Returns True if properties describes an opt-in user.

  Opt-in users are identified by examining the "buildbucket.build.created_by"
  field of the BuildBucket property.

  The BuildBucket property looks like:
  "buildbucket": "{
    \"build\": {
      \"bucket\": \"master.tryserver.chromium.linux\",
      \"created_by\": \"user:iannucci@chromium.org\",
      \"created_ts\": \"1494616236661800\",
      \"id\": \"8979775000984247248\",
      \"lease_key\": \"2065395720\",
      \"tags\": [
        \"builder:linux_chromium_rel_ng\",
        \"buildset:patch/rietveld/codereview.chromium.org/2852733003/1\",
        \"master:tryserver.chromium.linux\",
        \"user_agent:rietveld\"
      ]
    }
  }\"
  """
  buildbucket_json = properties.get('buildbucket')
  if not buildbucket_json:
    return False

  try:
    buildbucket = json.loads(buildbucket_json)
    return buildbucket.get('build', {}).get('created_by') in _OPT_IN_USERS
  except Exception:
    return False


def all_cipd_manifests():
  """Generator which yields all CIPD ensure manifests (canary, staging, prod).

  Each manifest is represented by a list of cipd.CipdPackage instances.
  """
  # All CIPD packages are in top-level platform config.
  for pins in (_STABLE_CIPD_PINS, _CANARY_CIPD_PINS):
    # TODO(dnj): Remove me when everything runs on Kitchen.
    yield [
      cipd.CipdPackage(name=_RECIPES_PY_CIPD_PACKAGE, version=pins.recipes),
      cipd.CipdPackage(name=_KITCHEN_CIPD_PACKAGE, version=pins.kitchen),
    ]


def set_recipe_runtime_properties(stream, args, properties):
  """Looks at mastername/buildername in $properties and contacts
  `luci-migration.appspot.com` to see if LUCI is prod for this builder yet.

  Args:
    * stream - an StructuredAnnotationStream that this function will use to
        present a 'LUCI Migration' step (and display generated migration
        properties).
    * args - the optparse/argparse result object containing the logdog_bootstrap
        arguments.
    * properties (in/out dictionary) - the recipe properties.

  Modifies `properties` to contain `$recipe_engine/runtime`.
  """
  ret = {
    'is_experimental': False,
    'is_luci': False,
  }
  migration = {'status': 'error'}
  try:
    cred_path = logdog_bootstrap.get_config(
      args, properties).service_account_path
    master = properties['mastername']
    builder = properties['buildername']

    # piggyback on logdog's service account; this needs to run everywhere that
    # logdog does, and since it's migration-buildbot-only code, this seems like
    # a reasonable compromise to make this rollout as quick as possible.
    scopes = ['https://www.googleapis.com/auth/userinfo.email']
    if cred_path == logdog_bootstrap.GCE_CREDENTIALS:
      cred = gce.AppAssertionCredentials(scopes)
    else:
      cred = GoogleCredentials.from_stream(cred_path).create_scoped(scopes)

    http = httplib2.Http()
    cred.authorize(http)
    url = ('https://luci-migration.appspot.com/masters/%s/builders/%s/'
           '?format=json')
    resp, body = http.request(
      url % (urllib.quote(master), urllib.quote(builder)))
    if resp.status == 200:
      ret['is_experimental'] = json.loads(body)['luci_is_prod']
      migration['status'] = 'ok'
    else:
      migration['status'] = 'bad_status'
      migration['code'] = resp.status
  except Exception as ex:
    migration['error'] = str(ex)

  properties['$recipe_engine/runtime'] = ret
  properties['luci_migration'] = migration
  with stream.step('LUCI Migration') as st:
    st.set_build_property('$recipe_engine/runtime', json.dumps(ret))
    st.set_build_property('luci_migration', json.dumps(migration))


def _call(cmd, **kwargs):
  LOGGER.info('Executing command: %s', cmd)
  exit_code = subprocess.call(cmd, **kwargs)
  LOGGER.info('Command %s finished with exit code %d.', cmd, exit_code)
  return exit_code


def _cleanup_old_layouts(buildbot_build_dir, cleanup_dir, cache_dir,
                         properties=None, using_kitchen=None):
  properties = properties or {}

  cleanup_paths = [
      # All remote_run instances no longer use "//build/slave/cache_dir" or
      # "//build/slave/goma_cache", preferring to use cache directories
      # instead (see "infra_paths" recipe module).
      os.path.join(BUILD_ROOT, 'slave', 'cache_dir'),
      os.path.join(BUILD_ROOT, 'slave', 'goma_cache'),

      # "bot_update" uses "build.dead" as a way to automatically purge
      # directories. While this is being handled differently, existing
      # "build.dead" directories currently exist under "[CACHE]/b/build.dead"
      # due to the previous logic.
      os.path.join(cache_dir, 'b', 'build.dead'),
  ]

  # Make switching to remote_run easier: we do not use buildbot workdir,
  # and it takes disk space leading to out of disk errors.
  buildbot_workdir = properties.get('workdir')
  if buildbot_workdir and os.path.isdir(buildbot_workdir):
    try:
      buildbot_workdir = os.path.realpath(buildbot_workdir)
      buildbot_build_dir = os.path.realpath(buildbot_build_dir)
      if buildbot_build_dir.startswith(buildbot_workdir):
        buildbot_workdir = buildbot_build_dir

      # Buildbot workdir is usually used as current working directory,
      # so do not remove it, but delete all of the contents. Deleting
      # current working directory of a running process may cause
      # confusing errors.
      cleanup_paths.extend(os.path.join(buildbot_workdir, x)
                           for x in os.listdir(buildbot_workdir))
    except Exception:
      # It's preferred that we keep going rather than fail the build
      # on optional cleanup.
      LOGGER.exception('Buildbot workdir cleanup failed: %s', buildbot_workdir)

  # "using_kitchen" will be None if we're doing a high-level emergency cleanup.
  # At this point, we don't know if we're using Kitchen, so we can't make any
  # cleanup decisions based on that..
  if using_kitchen is not None:
    if using_kitchen:
      # We want to delete the 'git_cache' cache directory, which was used by the
      # legacy "remote" code path.
      cleanup_paths.append(os.path.join(cache_dir, 'git_cache'))

      # We want to delete "<cache>/b", the legacy build cache directory. We will
      # use "<cache>/builder" from the "generic" infra configuration setup.
      cleanup_paths.append(os.path.join(cache_dir, 'b'))
    else:
      # If we have a 'git' cache directory from a previous Kitchen run, we
      # should delete that in favor of the 'git_cache' cache directory.
      cleanup_paths.append(os.path.join(cache_dir, 'git'))

      # We want to delete "<cache>/builder" from the Kitchen run.
      cleanup_paths.append(os.path.join(cache_dir, 'builder'))

  cleanup_paths = [p for p in cleanup_paths if os.path.exists(p)]
  if cleanup_paths:
    LOGGER.info('Cleaning up %d old layout path(s)...', len(cleanup_paths))

    # We remove files by moving them to the cleanup directory. This causes them
    # to be deleted in between builds.
    for path in cleanup_paths:
      LOGGER.info('Removing path from previous layout: %r', path)
      _try_cleanup(path, cleanup_dir)


def _remote_run_with_kitchen(args, stream, is_canary, kitchen_version,
                             properties, tempdir, basedir, cache_dir):
  # Write our build properties to a JSON file.
  properties_file = os.path.join(tempdir, 'remote_run_properties.json')
  with open(properties_file, 'w') as f:
    json.dump(properties, f)

  # Create our directory structure.
  recipe_temp_dir = _ensure_directory(tempdir, 't')

  # Use CIPD to download Kitchen to a root within the temporary directory.
  cipd_root = os.path.join(basedir, '.remote_run_cipd')
  kitchen_pkg = cipd.CipdPackage(
      name=_KITCHEN_CIPD_PACKAGE,
      version=kitchen_version)

  from slave import cipd_bootstrap_v2
  cipd_bootstrap_v2.install_cipd_packages(cipd_root, kitchen_pkg)

  kitchen_bin = os.path.join(cipd_root, 'kitchen' + infra_platform.exe_suffix())

  kitchen_cmd = [
      kitchen_bin,
      '-log-level', ('debug' if LOGGER.isEnabledFor(logging.DEBUG) else 'info'),
  ]

  kitchen_result_path = os.path.join(tempdir, 'kitchen_result.json')
  kitchen_cmd += [
      'cook',
      '-mode', 'buildbot',
      '-output-result-json', kitchen_result_path,
      '-properties-file', properties_file,
      '-recipe', args.recipe or properties.get('recipe'),
      '-repository', args.repository,
      '-cache-dir', cache_dir,
      '-temp-dir', recipe_temp_dir,
      '-checkout-dir', os.path.join(tempdir, 'rw'),
      '-workdir', os.path.join(tempdir, 'w'),
  ]

  # Master "remote_run" factory has been changed to pass "refs/heads/master" as
  # a default instead of "origin/master". However, this is a master-side change,
  # and requires a master restart. Rather than restarting all masters, we will
  # just pretend the change took effect here.
  #
  # No "-revision" means "latest", which is the same as "origin/master"'s
  # meaning.
  #
  # See: https://chromium-review.googlesource.com/c/446895/
  # See: crbug.com/696704
  #
  # TODO(dnj,nodir): Delete this once we're confident that all masters have been
  # restarted to take effect.
  if args.revision and (args.revision != 'origin/master'):
    kitchen_cmd += ['-revision', args.revision]

  # Using LogDog?
  try:
    # Load bootstrap configuration (may raise NotBootstrapped).
    cfg = logdog_bootstrap.get_config(args, properties)
    annotation_url = logdog_bootstrap.get_annotation_url(cfg)

    kitchen_cmd += [
      '-logdog-only',
      '-logdog-annotation-url', annotation_url,
    ]
    if cfg.service_account_path:
      # Note: as of 2017-09-01 this system service account is used for
      # logdog and events (via bigquery).
      # This flag is not passed if logdog is not configured (rare case).
      # This will cause a failure to send events, but it is not fatal and
      # won't affect overall build result or kitchen exit code.
      #
      # If we ever add something else to kitchen that may cause a fatal error
      # b/c of the absence of the system account, this code may need to be
      # changed. We hope to get off of buildbot by that time.
      kitchen_cmd += ['-luci-system-account-json', cfg.service_account_path]

    # Add LogDog tags.
    if cfg.tags:
      for k, v in cfg.tags.iteritems():
        param = k
        if v is not None:
          param += '=' + v
        kitchen_cmd += ['-logdog-tag', param]

    # (Debug) Use Kitchen output file if in debug mode.
    if args.logdog_debug_out_file:
      kitchen_cmd += ['-logdog-debug-out-file', args.logdog_debug_out_file]

    logdog_bootstrap.annotate(cfg, stream)
  except logdog_bootstrap.NotBootstrapped as e:
    LOGGER.info('Not configured to use LogDog: %s', e)

  # Remove PYTHNONPATH, since Kitchen will re-establish its own hermetic path.
  kitchen_env = os.environ.copy()
  kitchen_env.pop('PYTHONPATH', None)

  # Invoke Kitchen, capture its return code.
  return_code = _call(kitchen_cmd, env=kitchen_env)

  # Try to open kitchen result file. Any failure will result in an exception
  # and an infra failure.
  with open(kitchen_result_path) as f:
    kitchen_result = json.load(f)
    if isinstance(kitchen_result, dict) and 'recipe_result' in kitchen_result:
      recipe_result = kitchen_result['recipe_result']  # always a dict
    else:
      # Legacy mode: kitchen result is recipe result
      # TODO(nodir): remove this code path

      # On success, it may be JSON "null", so use an empty dict.
      recipe_result = kitchen_result or {}

  # If we failed, but aren't a step failure, we assume it was an
  # exception.
  f = recipe_result.get('failure', {})
  if f.get('timeout') or f.get('step_data'):
    # Return an infra failure for these failure types.
    #
    # The recipe engine used to return -1, which got interpreted as 255 by
    # os.exit in python, since process exit codes are a single byte.
    return_code = 255

  return return_code


def _exec_recipe(args, rt, stream, basedir, buildbot_build_dir, cleanup_dir,
                 cache_dir):
  tempdir = rt.tempdir(basedir)
  LOGGER.info('Using temporary directory: %r.', tempdir)

  build_data_dir = rt.tempdir(basedir)
  LOGGER.info('Using build data directory: %r.', build_data_dir)

  # Construct our properties.
  properties = copy.copy(args.factory_properties)
  properties.update(args.build_properties)

  # Determine if this build is an opt-in build.
  is_opt_in = get_is_opt_in(properties)

  # Determine our CIPD pins.
  #
  # If a property includes "remote_run_canary", we will explicitly use canary
  # pins. This can be done by manually submitting a build to the waterfall.
  mastername = properties.get('mastername')
  buildername = properties.get('buildername')
  is_canary = (_get_is_canary(mastername) or is_opt_in or
               'remote_run_canary' in properties or args.canary)
  pins = _STABLE_CIPD_PINS if not is_canary else _CANARY_CIPD_PINS

  # Determine if we're running Kitchen.
  #
  # If a property includes "remote_run_kitchen", we will explicitly use canary
  # pins. This can be done by manually submitting a build to the waterfall.
  is_kitchen = (is_opt_in or 'remote_run_kitchen' in properties)

  # Augment our input properties...
  def set_property(key, value):
    properties[key] = value
    print '@@@SET_BUILD_PROPERTY@%s@%s@@@' % (key, json.dumps(value))

  set_property('build_data_dir', build_data_dir)
  set_property('builder_id', 'master.%s:%s' % (mastername, buildername))
  if 'buildnumber' in properties:
    set_property(
        'build_id',
        'buildbot/{mastername}/{buildername}/{buildnumber}'.format(
            **properties))

  if not is_kitchen:
    # path_config property defines what paths a build uses for checkout, git
    # cache, goma cache, etc.
    #
    # TODO(dnj or phajdan): Rename "kitchen" path config to "remote_run_legacy".
    # "kitchen" was never correct, and incorrectly implies that Kitchen is
    # somehow involved int his path config.
    properties['path_config'] = 'kitchen'
    properties['bot_id'] = properties['slavename']

    # Set our cleanup directory to be "build.dead" so that BuildBot manages it.
    properties['$recipe_engine/path'] = {
        'cleanup_dir': cleanup_dir,
    }
  else:
    # If we're using Kitchen, our "path_config" must be empty or "kitchen".
    path_config = properties.pop('path_config', None)
    if path_config and path_config != 'kitchen':
      raise ValueError("Users of 'remote_run.py' MUST specify either 'kitchen' "
                       "or no 'path_config', not %r." % (path_config,))

  set_recipe_runtime_properties(stream, args, properties)

  monitoring_utils.write_build_monitoring_event(build_data_dir, properties)

  # Ensure that the CIPD client and base tooling is installed and available on
  # PATH.
  from slave import cipd_bootstrap_v2
  track = cipd_bootstrap_v2.STAGING if is_opt_in else cipd_bootstrap_v2.PROD
  prefix_paths = cipd_bootstrap_v2.high_level_ensure_cipd_client(
      basedir, mastername, track=track)

  if not is_kitchen:
    # kitchen sets this property itself, so only set this for non-kitchen runs.
    properties['$recipe_engine/step'] = {'prefix_path': prefix_paths}
  LOGGER.info('Using properties: %r', properties)

  # Cleanup data from old builds.
  _cleanup_old_layouts(
      buildbot_build_dir, cleanup_dir, cache_dir,
      properties=properties, using_kitchen=is_kitchen)

  # (Canary) Use Kitchen if configured.
  # TODO(dnj): Make this the only path once we move to Kitchen.
  if is_kitchen:
    # We don't want to pay the cost of purging Kitchen's temporary directory as
    # part of "remote_run" execution.
    kitchen_tempdir = _ensure_directory(tempdir, 'k')
    try:
      return _remote_run_with_kitchen(
          args, stream, is_canary, pins.kitchen, properties, tempdir, basedir,
          cache_dir)
    finally:
      _try_cleanup(kitchen_tempdir, cleanup_dir)

  ##
  # Classic Remote Run
  #
  # TODO(dnj): Delete this in favor of Kitchen.
  ##

  properties_file = os.path.join(tempdir, 'remote_run_properties.json')
  with open(properties_file, 'w') as f:
    json.dump(properties, f)

  cipd_path = os.path.join(basedir, '.remote_run_cipd')

  cipd_bootstrap_v2.install_cipd_packages(cipd_path,
      cipd.CipdPackage(_RECIPES_PY_CIPD_PACKAGE, pins.recipes))

  engine_args = []

  recipe_result_path = os.path.join(tempdir, 'recipe_result.json')
  recipe_cmd = [
      find_python(),
      os.path.join(cipd_path, 'recipes.py'),] + engine_args + [
      '--verbose',
      'remote',
      '--repository', args.repository,
      '--workdir', os.path.join(tempdir, 'rw'),
  ]
  if args.revision:
    recipe_cmd.extend(['--revision', args.revision])
  recipe_cmd.extend([
      '--',] + (
      engine_args) + [
      '--verbose',
      'run',
      '--properties-file', properties_file,
      '--workdir', os.path.join(tempdir, 'w'),
      '--output-result-json', recipe_result_path,
      properties.get('recipe') or args.recipe,
  ])
  # If we bootstrap through logdog, the recipe command line gets written
  # to a temporary file and does not appear in the log.
  LOGGER.info('Recipe command line: %r', recipe_cmd)

  environ = os.environ.copy()
  environ['VPYTHON_CLEAR_PYTHONPATH'] = '1'

  # Default to return code != 0 is for the benefit of buildbot, which uses
  # return code to decide if a step failed or not.
  recipe_return_code = 1
  try:
    bs = logdog_bootstrap.bootstrap(rt, args, basedir, tempdir, properties,
                                    recipe_cmd)

    LOGGER.info('Bootstrapping through LogDog: %s', bs.cmd)
    bs.annotate(stream)
    _ = _call(bs.cmd, env=environ)
    recipe_return_code = bs.get_result()
  except logdog_bootstrap.NotBootstrapped:
    LOGGER.info('Not using LogDog. Invoking `recipes.py` directly.')
    recipe_return_code = _call(recipe_cmd, env=environ)

  # Try to open recipe result JSON. Any failure will result in an exception
  # and an infra failure.
  with open(recipe_result_path) as f:
    return_value = json.load(f)

  f = return_value.get('failure')
  if f is not None and not f.get('step_failure'):
    # The recipe engine used to return -1, which got interpreted as 255
    # by os.exit in python, since process exit codes are a single byte.
    recipe_return_code = 255

  return recipe_return_code


def _main_impl(argv, stream):
  parser = argparse.ArgumentParser()
  parser.add_argument('--repository', required=True,
      help='URL of a git repository to fetch.')
  parser.add_argument('--revision',
      help='Git commit hash to check out.')
  parser.add_argument('--recipe', required=True,
      help='Name of the recipe to run')
  parser.add_argument('--build-properties-gz', dest='build_properties',
      type=chromium_utils.convert_gz_json_type, default={},
      help='Build properties in b64 gz JSON format')
  parser.add_argument('--factory-properties-gz', dest='factory_properties',
      type=chromium_utils.convert_gz_json_type, default={},
      help='factory properties in b64 gz JSON format')
  parser.add_argument('--leak', action='store_true',
      help='Refrain from cleaning up generated artifacts.')
  parser.add_argument('--canary', action='store_true',
      help='Force use of canary configuration.')
  parser.add_argument('--verbose', action='store_true')

  group = parser.add_argument_group('LogDog Bootstrap')
  logdog_bootstrap.add_arguments(group)

  args = parser.parse_args(argv[1:])

  buildbot_build_dir = os.path.abspath(os.getcwd())
  try:
    basedir = chromium_utils.FindUpward(buildbot_build_dir, 'b')
  except chromium_utils.PathNotFound as e:
    LOGGER.warn(e)
    # Use base directory inside system temporary directory - if we use slave
    # one (cwd), the paths get too long. Recipes which need different paths
    # or persistent directories should do so explicitly.
    basedir = tempfile.gettempdir()

  # "/b/c" as a cache directory.
  cache_dir = os.path.join(BUILDBOT_ROOT, 'c')

  # BuildBot automatically purges "build.dead", and recipe engine uses this as
  # its cleanup directory (see "infra_paths" recipe module). Make sure that it
  # exists, and retain it so that we can use it to perform "annotated_run" to
  # "remote_run" path cleanup.
  cleanup_dir = os.path.join(
      os.path.dirname(buildbot_build_dir), 'build.dead')

  # Cleanup system and temporary directories.
  from slave import cleanup_temp
  try:
    # Note that this will delete "cleanup_dir", so we will need to
    # recreate it afterwards.
    cleanup_temp.Cleanup(b_dir=basedir)
  except cleanup_temp.FullDriveException:
    LOGGER.error('Buildslave disk is full! Please contact the trooper.')

    # Our cleanup failed because the disk is full! Do a best-effort cleanup in
    # hopes that the next run, we can get farther than this.
    _ensure_directory(cleanup_dir)
    _cleanup_old_layouts(buildbot_build_dir, cleanup_dir, cache_dir)
    raise

  # Ensure that "cleanup_dir" exists; our recipes expect this to be the case.
  _ensure_directory(cleanup_dir)

  # Choose a tempdir prefix. If we have no active subdir, we will use a prefix
  # of "rr". If we have an active subdir, we will use "rs/<subdir>". This way,
  # there will be no tempdir collisions between combinations of the two
  # sitautions.
  active_subdir = chromium_utils.GetActiveSubdir()
  if active_subdir:
    prefix = os.path.join('rs', str(active_subdir))
  else:
    prefix = 'rr'

  with robust_tempdir.RobustTempdir(prefix, leak=args.leak) as rt:
    # Explicitly clean up possibly leaked temporary directories
    # from previous runs.
    rt.cleanup(basedir)
    return _exec_recipe(args, rt, stream, basedir, buildbot_build_dir,
                        cleanup_dir, cache_dir)


def main(argv, stream, passthrough=False):
  # We always want everything to be unbuffered so that we can see the logs on
  # buildbot/logdog as soon as they're available.
  os.environ['PYTHONUNBUFFERED'] = '1'

  exc_info = None
  try:
    return _main_impl(argv, stream)
  except Exception:
    exc_info = sys.exc_info()

  # Report on the "remote_run" execution. If an exception (infra failure)
  # occurred, raise it so that the build and the step turn purple.
  with stream.step('remote_run_result') as s:
    if passthrough:
      s.step_text('(passthrough)')
    if exc_info is not None:
      raise exc_info[0], exc_info[1], exc_info[2]


def shell_main(argv):
  logging.basicConfig(
      level=(logging.DEBUG if '--verbose' in argv else logging.INFO))

  if update_scripts.update_scripts():
    # Re-execute with the updated remote_run.py.
    return _call([sys.executable] + argv)

  stream = annotator.StructuredAnnotationStream()
  return main(argv, stream)


if __name__ == '__main__':
  sys.exit(shell_main(sys.argv))
