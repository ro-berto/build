#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import collections
import contextlib
import json
import logging
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile


# Install Infra build environment.
BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
                             os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BUILD_ROOT, 'scripts'))

from common import annotator
from common import chromium_utils
from common import env
from common import master_cfg_utils
from slave import gce

# Logging instance.
LOGGER = logging.getLogger('annotated_run')

# Return codes used by Butler/Annotee to indicate their failure (as opposed to
# a forwarded return code from the underlying process).
LOGDOG_ERROR_RETURNCODES = (
    # Butler runtime error.
    250,
    # Annotee runtime error.
    251,
)

# Sentinel value that, if present in master config, matches all builders
# underneath that master.
WHITELIST_ALL = '*'

# Whitelist of {master}=>[{builder}|WHITELIST_ALL] whitelisting specific masters
# and builders for experimental LogDog/Annotee export.
LOGDOG_WHITELIST_MASTER_BUILDERS = {
    'chromium.infra': {
      'luci-gae-trusty64',
      'luci-go-trusty64',
      'infra-continuous-trusty-64',
      'infra-continuous-precise-64',
    },
}

# Configuration for a Pub/Sub topic.
PubSubConfig = collections.namedtuple('PubSubConfig', ('project', 'topic'))

# LogDogPlatform is the set of platform-specific LogDog bootstrapping
# configuration parameters.
#
# See _logdog_get_streamserver_uri for "streamserver" parameter details.
LogDogPlatform = collections.namedtuple('LogDogPlatform', (
    'butler', 'annotee', 'credential_path', 'streamserver'))

# A CIPD binary description, including the package name, version, and relative
# path of the binary within the package.
CipdBinary = collections.namedtuple('CipdBinary',
    ('package', 'version', 'relpath'))

# RecipeRuntime will probe this for values.
# - First, (system, platform)
# - Then, (system,)
# - Finally, (),
PLATFORM_CONFIG = {
  # All systems.
  (): {
    'logdog_pubsub': PubSubConfig(
        project='luci-logdog',
        topic='logs',
    ),
  },

  # Linux
  ('Linux',): {
    'run_cmd': ['/opt/infra-python/run.py'],
    'logdog_platform': LogDogPlatform(
        butler=CipdBinary('infra/tools/luci/logdog/butler/linux-amd64',
                          'latest', 'logdog_butler'),
        annotee=CipdBinary('infra/tools/luci/logdog/annotee/linux-amd64',
                          'latest', 'logdog_annotee'),
        credential_path=('/creds/service_accounts/'
                         'service-account-luci-logdog-publisher.json'),
        streamserver='unix',
    ),
  },

  # Mac OSX
  ('Darwin',): {
    'run_cmd': ['/opt/infra-python/run.py'],
  },

  # Windows
  ('Windows',): {
    'run_cmd': ['C:\\infra-python\\ENV\\Scripts\\python.exe',
                'C:\\infra-python\\run.py'],
  },
}


# Config is the runtime configuration used by `annotated_run.py` to bootstrap
# the recipe engine.
Config = collections.namedtuple('Config', (
    'run_cmd',
    'logdog_pubsub',
    'logdog_platform',
))


class Runtime(object):
  """Runtime is the runtime context of the recipe execution.

  It is a ContextManager that tracks generated files and cleans them up at
  exit.
  """

  def __init__(self, leak=False):
    self._tempdirs = []
    self._leak = leak

  def cleanup(self, path):
    self._tempdirs.append(path)

  def tempdir(self, base=None):
    """Creates a temporary recipe-local working directory and yields it.

    This creates a temporary directory for this annotation run. Directory
    cleanup is appended to the supplied Runtime.

    This creates two levels of directory:
      <base>/.recipe_runtime
      <base>/.recipe_runtime/tmpFOO

    On termination, the entire "<base>/.recipe_runtime" directory is deleted,
    removing the subdirectory created by this instance as well as cleaning up
    any other temporary subdirectories leaked by previous executions.

    Args:
      rt (Runtime): Process-wide runtime.
      base (str/None): The directory under which the tempdir should be created.
          If None, the default temporary directory root will be used.
    """
    base = base or tempfile.gettempdir()
    basedir = ensure_directory(base, '.recipe_runtime')
    self.cleanup(basedir)
    tdir = tempfile.mkdtemp(dir=basedir)
    return tdir

  def __enter__(self):
    return self

  def __exit__(self, _et, _ev, _tb):
    self.close()

  def close(self):
    if self._leak:
      LOGGER.warning('(--leak) Leaking temporary paths: %s', self._tempdirs)
    else:
      for path in reversed(self._tempdirs):
        try:
          if os.path.isdir(path):
            LOGGER.debug('Cleaning up temporary directory [%s].', path)
            chromium_utils.RemoveDirectory(path)
        except BaseException:
          LOGGER.exception('Failed to clean up temporary directory [%s].',
                           path)
    del(self._tempdirs[:])


def get_config():
  """Returns (Config): The constructed Config object.

  The Config object is constructed from:
  - Cascading the PLATFORM_CONFIG fields together based on current
        OS/Architecture.

  Raises:
    KeyError: if a required configuration key/parameter is not available.
  """
  # Cascade the platform configuration.
  p = (platform.system(), platform.processor())
  platform_config = {}
  for i in xrange(len(p)+1):
    platform_config.update(PLATFORM_CONFIG.get(p[:i], {}))

  # Construct runtime configuration.
  return Config(
      run_cmd=platform_config.get('run_cmd'),
      logdog_pubsub=platform_config.get('logdog_pubsub'),
      logdog_platform=platform_config.get('logdog_platform'),
      )


def ensure_directory(*path):
  path = os.path.join(*path)
  if not os.path.isdir(path):
    os.makedirs(path)
  return path


def _logdog_get_streamserver_uri(rt, typ):
  """Returns (str): The Butler StreamServer URI.

  Args:
    rt (Runtime): Process-wide runtime.
    typ (str): The type of URI to generate. One of: ['unix'].
  Raises:
    LogDogBootstrapError: if |typ| is not a known type.
  """
  if typ == 'unix':
    # We have to use a custom temporary directory here. This is due to the path
    # length limitation on UNIX domain sockets, which is generally 104-108
    # characters. We can't make that assumption about our standard recipe
    # temporary directory.
    sockdir = rt.tempdir()
    uri = 'unix:%s' % (os.path.join(sockdir, 'butler.sock'),)
    if len(uri) > 104:
      raise LogDogBootstrapError('Generated URI exceeds UNIX domain socket '
                                 'name size: %s' % (uri,))
    return uri
  raise LogDogBootstrapError('No streamserver URI generator.')


def _run_command(cmd, **kwargs):
  if kwargs.pop('dry_run', False):
    LOGGER.info('(Dry Run) Would have executed command: %s', cmd)
    return 0, ''

  LOGGER.debug('Executing command: %s', cmd)
  kwargs.setdefault('stderr', subprocess.STDOUT)
  proc = subprocess.Popen(cmd, **kwargs)
  stdout, _ = proc.communicate()

  LOGGER.debug('Process [%s] returned [%d] with output:\n%s',
               cmd, proc.returncode, stdout)
  return proc.returncode, stdout


def _check_command(cmd, **kwargs):
  rv, stdout = _run_command(cmd, **kwargs)
  if rv != 0:
    raise subprocess.CalledProcessError(rv, cmd, output=stdout)
  return stdout


class LogDogNotBootstrapped(Exception):
  pass


class LogDogBootstrapError(Exception):
  pass


def ensure_directory(*path):
  path = os.path.join(*path)
  if not os.path.isdir(path):
    os.makedirs(path)
  return path


def _get_service_account_json(opts, credential_path):
  """Returns (str/None): If specified, the path to the service account JSON.

  This method probes the local environment and returns a (possibly empty) list
  of arguments to add to the Butler command line for authentication.

  If we're running on a GCE instance, no arguments will be returned, as GCE
  service account is implicitly authenticated. If we're running on Baremetal,
  a path to those credentials will be returned.

  Args:
    rt (RecipeRuntime): The runtime environment.
  Raises:
    |LogDogBootstrapError| if no credentials could be found.
  """
  path = opts.logdog_service_account_json
  if path:
    return path

  if gce.Authenticator.is_gce():
    LOGGER.info('Running on GCE. No credentials necessary.')
    return None

  if os.path.isfile(credential_path):
    return credential_path

  raise LogDogBootstrapError('Could not find service account credentials. '
                             'Tried: %s' % (credential_path,))


def _logdog_install_cipd(path, *packages):
  """Returns (list): The paths to the binaries in each of the packages.

  This method bootstraps CIPD in "path", installing the packages specified
  by "packages" and returning the paths to their binaries.

  Args:
    path (str): The CIPD installation root.
    packages (CipdBinary): The set of CIPD binary packages to install.
  """
  verbosity = 0
  level = logging.getLogger().level
  if level <= logging.INFO:
    verbosity += 1
  if level <= logging.DEBUG:
    verbosity += 1

  packages_path = os.path.join(path, 'packages.json')
  pmap = {}
  cmd = [
      sys.executable,
      os.path.join(env.Build, 'scripts', 'slave', 'cipd.py'),
      '--dest-directory', path,
      '--json-output', packages_path,
  ] + (['--verbose'] * verbosity)
  for p in packages:
    cmd += ['-P', '%s@%s' % (p.package, p.version)]
    pmap[p.package] = os.path.join(path, p.relpath)

  try:
    _check_command(cmd)
  except subprocess.CalledProcessError:
    LOGGER.exception('Failed to install LogDog CIPD packages.')
    raise LogDogBootstrapError()

  # Resolve installed packages.
  return tuple(pmap[p.package] for p in packages)


def _build_logdog_prefix(properties):
  """Constructs a LogDog stream prefix from the supplied properties.

  The returned prefix is of the form:
  bb/<mastername>/<buildername>/<buildnumber>

  Any path-incompatible characters will be flattened to underscores.
  """
  def normalize(s):
    parts = []
    for ch in str(s):
      if ch.isalnum() or ch in ':_-.':
        parts.append(ch)
      else:
        parts.append('_')
    if not parts[0].isalnum():
      parts.insert(0, 's_')
    return ''.join(parts)

  components = {}
  for f in ('mastername', 'buildername', 'buildnumber'):
    prop = properties.get(f)
    if not prop:
      raise LogDogBootstrapError('Missing build property [%s].' % (f,))
    components[f] = normalize(properties.get(f))
  return 'bb/%(mastername)s/%(buildername)s/%(buildnumber)s' % components


def _logdog_bootstrap(rt, opts, tempdir, config, properties, cmd):
  """Executes the recipe engine, bootstrapping it through LogDog/Annotee.

  This method executes the recipe engine, bootstrapping it through
  LogDog/Annotee so its output and annotations are streamed to LogDog. The
  bootstrap is configured to tee the annotations through STDOUT/STDERR so they
  will still be sent to BuildBot.

  The overall setup here is:
  [annotated_run.py] => [logdog_butler] => [logdog_annotee] => [recipes.py]

  Args:
    rt (Runtime): Process-wide runtime.
    opts (argparse.Namespace): Command-line options.
    tempdir (str): The path to the session temporary directory.
    config (Config): Recipe runtime configuration.
    properties (dict): Build properties.
    cmd (list): The recipe runner command list to bootstrap.

  Returns (int): The return code of the recipe runner process.

  Raises:
    LogDogNotBootstrapped: if the recipe engine was not executed because the
        LogDog bootstrap requirements are not available.
    LogDogBootstrapError: if there was an error bootstrapping the recipe runner
        through LogDog.
  """
  bootstrap_dir = ensure_directory(tempdir, 'logdog_bootstrap')

  plat = config.logdog_platform
  if not plat:
    raise LogDogNotBootstrapped('LogDog platform is not configured.')

  # Determine LogDog prefix.
  prefix = _build_logdog_prefix(properties)

  # TODO(dnj): Consider moving this to a permanent directory on the bot so we
  #            don't CIPD-refresh each time.
  cipd_path = os.path.join(bootstrap_dir, 'cipd')
  butler, annotee = _logdog_install_cipd(cipd_path, plat.butler, plat.annotee)
  if opts.logdog_butler_path:
    butler = opts.logdog_butler_path
  if opts.logdog_annotee_path:
    annotee = opts.logdog_annotee_path

  if not config.logdog_pubsub:
    raise LogDogNotBootstrapped('No Pub/Sub configured.')
  if not config.logdog_pubsub.project:
    raise LogDogNotBootstrapped('No Pub/Sub project configured.')
  if not config.logdog_pubsub.topic:
    raise LogDogNotBootstrapped('No Pub/Sub topic configured.')

  # Determine LogDog verbosity.
  logdog_verbose = []
  if opts.logdog_verbose == 0:
    pass
  elif opts.logdog_verbose == 1:
    logdog_verbose.append('-log_level=info')
  else:
    logdog_verbose.append('-log_level=debug')

  service_account_args = []
  service_account_json = _get_service_account_json(opts, plat.credential_path)
  if service_account_json:
    service_account_args += ['-service-account-json', service_account_json]

  # Generate our Butler stream server URI.
  streamserver_uri = _logdog_get_streamserver_uri(rt, plat.streamserver)

  # Dump the bootstrapped Annotee command to JSON for Annotee to load.
  #
  # Annotee can run accept bootstrap parameters through either JSON or
  # command-line, but using JSON effectively steps around any sort of command-
  # line length limits such as those experienced on Windows.
  cmd_json = os.path.join(bootstrap_dir, 'annotee_cmd.json')
  with open(cmd_json, 'w') as fd:
    json.dump(cmd, fd)

  # Butler Command.
  cmd = [
      butler,
      '-prefix', prefix,
      '-output', 'pubsub,project="%(project)s",topic="%(topic)s"' % (
          config.logdog_pubsub._asdict()),
  ]
  cmd += logdog_verbose
  cmd += service_account_args
  cmd += [
      'run',
      '-stdout', 'tee=stdout',
      '-stderr', 'tee=stderr',
      '-streamserver-uri', streamserver_uri,
      '--',
  ]

  # Annotee Command.
  cmd += [
      annotee,
      '-butler-stream-server', streamserver_uri,
      '-annotate', 'tee',
      '-name-base', 'recipes',
      '-print-summary',
      '-tee',
      '-json-args-path', cmd_json,
  ]
  cmd += logdog_verbose

  rv, _ = _run_command(cmd, dry_run=opts.dry_run)
  if rv in LOGDOG_ERROR_RETURNCODES:
    raise LogDogBootstrapError('LogDog Error (%d)' % (rv,))
  return rv


def _should_run_logdog(properties):
  """Returns (bool): True if LogDog should be used for this run.

  Args:
    properties (dict): The factory properties for this recipe run.
  """
  mastername = properties.get('mastername')
  buildername = properties.get('buildername')
  if not all((mastername, buildername)):
    LOGGER.warning('Required mastername/buildername is not set.')
    return False

  # Key on mastername.
  bdict = LOGDOG_WHITELIST_MASTER_BUILDERS.get(mastername)
  if bdict is not None:
    # Key on buildername.
    if WHITELIST_ALL in bdict or buildername in bdict:
      LOGGER.info('Whitelisted master %s, builder %s.',
                  mastername, buildername)
      return True

  LOGGER.info('Master %s, builder %s is not whitelisted for LogDog.',
              mastername, buildername)
  return False


def get_recipe_properties(workdir, build_properties,
                          use_factory_properties_from_disk):
  """Constructs the recipe's properties from buildbot's properties.

  This retrieves the current factory properties from the master_config
  in the slave's checkout (no factory properties are handed to us from the
  master), and merges in the build properties.

  Using the values from the checkout allows us to do things like change
  the recipe and other factory properties for a builder without needing
  a master restart.

  As the build properties doesn't include the factory properties, we would:
  1. Load factory properties from checkout on the slave.
  2. Override the factory properties with the build properties.
  3. Set the factory-only properties as build properties using annotation so
     that they will show up on the build page.
  """
  if not use_factory_properties_from_disk:
    return build_properties

  stream = annotator.StructuredAnnotationStream()
  with stream.step('setup_properties') as s:
    factory_properties = {}

    mastername = build_properties.get('mastername')
    buildername = build_properties.get('buildername')
    if mastername and buildername:
      # Load factory properties from tip-of-tree checkout on the slave builder.
      factory_properties = get_factory_properties_from_disk(
          workdir, mastername, buildername)

    # Check conflicts between factory properties and build properties.
    conflicting_properties = {}
    for name, value in factory_properties.items():
      if not build_properties.has_key(name) or build_properties[name] == value:
        continue
      conflicting_properties[name] = (value, build_properties[name])

    if conflicting_properties:
      s.step_text(
          '<br/>detected %d conflict[s] between factory and build properties'
          % len(conflicting_properties))

      conflicts = ['  "%s": factory: "%s", build: "%s"' % (
            name,
            '<unset>' if (fv is None) else fv,
            '<unset>' if (bv is None) else bv)
          for name, (fv, bv) in conflicting_properties.items()]
      LOGGER.warning('Conflicting factory and build properties:\n%s',
                     '\n'.join(conflicts))
      LOGGER.warning("Will use the values from build properties.")

    # Figure out the factory-only properties and set them as build properties so
    # that they will show up on the build page.
    for name, value in factory_properties.items():
      if not build_properties.has_key(name):
        s.set_build_property(name, json.dumps(value))

    # Build properties override factory properties.
    properties = factory_properties.copy()
    properties.update(build_properties)

    # Unhack buildbot-hacked blamelist (iannucci).
    if ('blamelist_real' in properties and 'blamelist' in properties):
      properties['blamelist'] = properties['blamelist_real']
      del properties['blamelist_real']

    return properties


def get_factory_properties_from_disk(workdir, mastername, buildername):
  master_list = master_cfg_utils.GetMasters()
  master_path = None
  for name, path in master_list:
    if name == mastername:
      master_path = path

  if not master_path:
    raise LookupError('master "%s" not found.' % mastername)

  script_path = os.path.join(env.Build, 'scripts', 'tools',
                             'dump_master_cfg.py')

  master_json = os.path.join(workdir, 'dump_master_cfg.json')
  dump_cmd = [sys.executable,
              script_path,
              master_path, master_json]
  proc = subprocess.Popen(dump_cmd, cwd=env.Build,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  out, err = proc.communicate()
  if proc.returncode:
    raise LookupError('Failed to get the master config; dump_master_cfg %s'
                      'returned %d):\n%s\n%s\n'% (
                      mastername, proc.returncode, out, err))

  with open(master_json, 'rU') as f:
    config = json.load(f)

  # Now extract just the factory properties for the requested builder
  # from the master config.
  props = {}
  found = False
  for builder_dict in config['builders']:
    if builder_dict['name'] == buildername:
      found = True
      factory_properties = builder_dict['factory']['properties']
      for name, (value, _) in factory_properties.items():
        props[name] = value

  if not found:
    raise LookupError('builder "%s" not found on in master "%s"' %
                      (buildername, mastername))

  if 'recipe' not in props:
    raise LookupError('Cannot find recipe for %s on %s' %
                      (buildername, mastername))

  return props


def get_args(argv):
  """Process command-line arguments."""
  parser = argparse.ArgumentParser(
      description='Entry point for annotated builds.')
  parser.add_argument('-v', '--verbose',
      action='count', default=0,
      help='Increase verbosity. This can be specified multiple times.')
  parser.add_argument('-d', '--dry-run', action='store_true',
      help='Perform the setup, but refrain from executing the recipe.')
  parser.add_argument('-l', '--leak', action='store_true',
      help="Refrain from cleaning up generated artifacts.")
  parser.add_argument('--build-properties',
      type=json.loads, default={},
      help='build properties in JSON format')
  parser.add_argument('--factory-properties',
      type=json.loads, default={},
      help='factory properties in JSON format')
  parser.add_argument('--build-properties-gz', dest='build_properties',
      type=chromium_utils.convert_gz_json_type, default={},
      help='build properties in b64 gz JSON format')
  parser.add_argument('--factory-properties-gz', dest='factory_properties',
      type=chromium_utils.convert_gz_json_type, default={},
      help='factory properties in b64 gz JSON format')
  parser.add_argument('--keep-stdin', action='store_true', default=False,
      help='don\'t close stdin when running recipe steps')
  parser.add_argument('--master-overrides-slave', action='store_true',
      help='use the property values given on the command line from the master, '
           'not the ones looked up on the slave')
  parser.add_argument('--use-factory-properties-from-disk',
      action='store_true', default=False,
      help='use factory properties loaded from disk on the slave')

  group = parser.add_argument_group('LogDog Bootstrap')
  group.add_argument('--logdog-verbose',
      action='count', default=0,
      help='Increase LogDog verbosity. This can be specified multiple times.')
  group.add_argument('--logdog-force', action='store_true',
      help='Force LogDog bootstrapping, even if the system is not configured.')
  group.add_argument('--logdog-butler-path',
      help='Path to the LogDog Butler. If empty, one will be probed/downloaded '
           'from CIPD.')
  group.add_argument('--logdog-annotee-path',
      help='Path to the LogDog Annotee. If empty, one will be '
           'probed/downloaded from CIPD.')
  group.add_argument('--logdog-service-account-json',
      help='Path to the service account JSON. If one is not provided, the '
           'local system credentials will be used.')

  return parser.parse_args(argv)


def update_scripts():
  if os.environ.get('RUN_SLAVE_UPDATED_SCRIPTS'):
    os.environ.pop('RUN_SLAVE_UPDATED_SCRIPTS')
    return False

  stream = annotator.StructuredAnnotationStream()

  with stream.step('update_scripts') as s:
    gclient_name = 'gclient'
    if sys.platform.startswith('win'):
      gclient_name += '.bat'
    gclient_path = os.path.join(env.Build, os.pardir, 'depot_tools',
                                gclient_name)
    gclient_cmd = [gclient_path, 'sync', '--force', '--verbose', '--jobs=2']
    try:
      fd, output_json = tempfile.mkstemp()
      os.close(fd)
      gclient_cmd += ['--output-json', output_json]
    except Exception:
      # Super paranoia try block.
      output_json = None
    cmd_dict = {
        'name': 'update_scripts',
        'cmd': gclient_cmd,
        'cwd': env.Build,
    }
    annotator.print_step(cmd_dict, os.environ, stream)
    rv, _ = _run_command(gclient_cmd, cwd=env.Build)
    if rv != 0:
      s.step_text('gclient sync failed!')
      s.step_warnings()
    elif output_json:
      try:
        with open(output_json, 'r') as f:
          gclient_json = json.load(f)
        for line in json.dumps(
            gclient_json, sort_keys=True,
            indent=4, separators=(',', ': ')).splitlines():
          s.step_log_line('gclient_json', line)
        s.step_log_end('gclient_json')

        build_checkout = gclient_json['solutions'].get('build/')
        if build_checkout:
          s.step_text('%(scm)s - %(revision)s' % build_checkout)
          s.set_build_property('build_scm', json.dumps(build_checkout['scm']))
          s.set_build_property('build_revision',
                               json.dumps(build_checkout['revision']))
      except Exception as e:
        s.step_text('Unable to process gclient JSON %s' % repr(e))
        s.step_warnings()
      finally:
        try:
          os.remove(output_json)
        except Exception as e:
          LOGGER.warning("LEAKED: %s", output_json, exc_info=True)
    else:
      s.step_text('Unable to get SCM data')
      s.step_warnings()

    os.environ['RUN_SLAVE_UPDATED_SCRIPTS'] = '1'

    # After running update scripts, set PYTHONIOENCODING=UTF-8 for the real
    # annotated_run.
    os.environ['PYTHONIOENCODING'] = 'UTF-8'

    return True


def clean_old_recipe_engine():
  """Clean stale pycs from the old location of recipe_engine.

  This function should only be needed for a little while after the recipe
  packages rollout (2015-09-16).
  """
  for (dirpath, _, filenames) in os.walk(
      os.path.join(env.Build, 'third_party', 'recipe_engine')):
    for filename in filenames:
      if filename.endswith('.pyc'):
        os.remove(os.path.join(dirpath, filename))


def write_monitoring_event(config, datadir, build_properties):
  # Ensure that all command components of "run_cmd" are available.
  if not config.run_cmd:
    LOGGER.warning('No run.py is defined for this platform.')
    return
  run_cmd_missing = [p for p in config.run_cmd if not os.path.exists(p)]
  if run_cmd_missing:
    LOGGER.warning('Unable to find run.py. Some components are missing: %s',
                   run_cmd_missing)
    return

  hostname = socket.getfqdn()
  if hostname:  # just in case getfqdn() returns None.
    hostname = hostname.split('.')[0]
  else:
    hostname = None

  try:
    cmd = config.run_cmd + ['infra.tools.send_monitoring_event',
       '--event-mon-output-file', os.path.join(datadir, 'log_request_proto'),
       '--event-mon-run-type', 'file',
       '--event-mon-service-name',
           'buildbot/master/master.%s'
           % build_properties.get('mastername', 'UNKNOWN'),
       '--build-event-build-name',
           build_properties.get('buildername', 'UNKNOWN'),
       '--build-event-build-number',
           str(build_properties.get('buildnumber', 0)),
       '--build-event-build-scheduling-time',
           str(1000*int(build_properties.get('requestedAt', 0))),
       '--build-event-type', 'BUILD',
       '--event-mon-timestamp-kind', 'POINT',
       # And use only defaults for credentials.
     ]
    # Add this conditionally so that we get an error in
    # send_monitoring_event log files in case it isn't present.
    if hostname:
      cmd += ['--build-event-hostname', hostname]
    _check_command(cmd)
  except Exception:
    LOGGER.warning("Failed to send monitoring event.", exc_info=True)


def _exec_recipe(rt, opts, tdir, config, properties):
  # Find out if the recipe we intend to run is in build_internal's recipes. If
  # so, use recipes.py from there, otherwise use the one from build.
  recipe_file = properties['recipe'].replace('/', os.path.sep) + '.py'

  # Use the standard recipe runner unless the recipes are explicitly in the
  # "build_limited" repository.
  recipe_runner = os.path.join(env.Build,
                               'scripts', 'slave', 'recipes.py')
  if env.BuildInternal:
    build_limited = os.path.join(env.BuildInternal, 'scripts', 'slave')
    if os.path.exists(os.path.join(build_limited, 'recipes', recipe_file)):
      recipe_runner = os.path.join(build_limited, 'recipes.py')

  # Dump properties to JSON and build recipe command.
  props_file = os.path.join(tdir, 'recipe_properties.json')
  with open(props_file, 'w') as fh:
    json.dump(properties, fh)

  cmd = [
      sys.executable, '-u', recipe_runner,
      'run',
      '--workdir=%s' % os.getcwd(),
      '--properties-file=%s' % props_file,
      properties['recipe'],
  ]

  status = None
  try:
    if opts.logdog_force or _should_run_logdog(properties):
      status = _logdog_bootstrap(rt, opts, tdir, config, properties, cmd)
  except LogDogNotBootstrapped as e:
    LOGGER.info('Not bootstrapped: %s', e.message)
  except LogDogBootstrapError as e:
    LOGGER.warning('Could not bootstrap LogDog: %s', e.message)
  except Exception as e:
    LOGGER.exception('Exception while bootstrapping LogDog.')
  finally:
    if status is None:
      LOGGER.info('Not using LogDog. Invoking `recipes.py` directly.')
      status, _ = _run_command(cmd, dry_run=opts.dry_run)

  return status


def main(argv):
  opts = get_args(argv)

  if opts.verbose == 0:
    level = logging.INFO
  else:
    level = logging.DEBUG
  logging.getLogger().setLevel(level)

  clean_old_recipe_engine()

  # Enter our runtime environment.
  with Runtime(leak=opts.leak) as rt:
    tdir = rt.tempdir(os.getcwd())
    LOGGER.debug('Using temporary directory: [%s].', tdir)

    # Load factory properties and configuration.
    # TODO(crbug.com/551165): remove flag "factory_properties".
    use_factory_properties_from_disk = (opts.use_factory_properties_from_disk or
                                        bool(opts.factory_properties))
    properties = get_recipe_properties(
        tdir, opts.build_properties, use_factory_properties_from_disk)
    LOGGER.debug('Loaded properties: %s', properties)

    config = get_config()
    LOGGER.debug('Loaded runtime configuration: %s', config)

    # Setup monitoring directory and send a monitoring event.
    build_data_dir = ensure_directory(tdir, 'build_data')
    properties['build_data_dir'] = build_data_dir

    # Write our annotated_run.py monitoring event.
    write_monitoring_event(config, build_data_dir, properties)

    # Execute our recipe.
    return _exec_recipe(rt, opts, tdir, config, properties)


def shell_main(argv):
  if update_scripts():
    # Re-execute with the updated annotated_run.py.
    rv, _ = _run_command([sys.executable] + argv)
    return rv
  else:
    return main(argv[1:])


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  sys.exit(shell_main(sys.argv))
