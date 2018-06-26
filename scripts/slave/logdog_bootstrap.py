# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Implements LogDog Bootstrapping support.
"""

import argparse
import collections
import json
import logging
import os
import subprocess
import sys

from common import annotator
from common import chromium_utils
from common import env
from slave import cipd
from slave import cipd_bootstrap_v2
from slave import gce
from slave import infra_platform


LOGGER = logging.getLogger('logdog_bootstrap')

# Magic credential "path" to indicate that we're using GCE credentials instead
# of a service account json file.
GCE_CREDENTIALS = ':gce'


class NotBootstrapped(Exception):
  pass


class BootstrapError(Exception):
  pass


# Path to the "cipd.py" library.
_CIPD_PY_PATH = os.path.join(env.Build, 'scripts', 'slave', 'cipd.py')


# CIPD tag for LogDog Butler/Annotee to use.
#
# Verify full package set with:
# $ cipd resolve infra/tools/luci/logdog/butler/ -version ${TAG}
# $ cipd resolve infra/tools/luci/logdog/annotee/ -version ${TAG}
_STABLE_CIPD_TAG = 'git_revision:910b0131071156dce831a84150623d2b9ead62cd'
_CANARY_CIPD_TAG = 'git_revision:57211f43708aa2c91027d1f90f6cdfb639925fb4'

_CIPD_TAG_MAP = {
    '$stable': _STABLE_CIPD_TAG,
    '$canary': _CANARY_CIPD_TAG,
}

# Map between CIPD versions and LogDog API version strings. This can be updated
# if API-based decisions are needed.
#
# If a CIPD tag is explicitly mentioned here, the associated API will be used.
# Otherwise, the "_STABLE_CIPD_TAG" API will be used.
#
# As CIPD tags rotate, old API versions and their respective logic can be
# removed from this code.
_CIPD_TAG_API_MAP = {
    _STABLE_CIPD_TAG: 4,
    _CANARY_CIPD_TAG: 4,
}

# Platform is the set of platform-specific LogDog bootstrapping
# configuration parameters. Platform is loaded by cascading the _PLATFORM_CONFIG
# against the current running platform.
#
# See _get_streamserver_uri for "streamserver" parameter details.
#
# Loaded by '_get_platform'.
Platform = collections.namedtuple('Platform', (
    'host', 'max_buffer_age', 'butler', 'annotee', 'credential_path',
    'streamserver'))


# An infra_platform cascading configuration for the supported architectures.
_PLATFORM_CONFIG = {
  # All systems.
  (): {
    'host': 'logs.chromium.org',
    'max_buffer_age': '30s',
    'butler': 'infra/tools/luci/logdog/butler/${platform}',
    'annotee': 'infra/tools/luci/logdog/annotee/${platform}',
  },

  # Linux
  ('linux',): {
    'credential_path': ('/creds/service_accounts/'
                        'service-account-luci-logdog-publisher.json'),
    'streamserver': 'unix',
  },

  # Mac
  ('mac',): {
    'credential_path': ('/creds/service_accounts/'
                        'service-account-luci-logdog-publisher.json'),
    'streamserver': 'unix',
  },

  # Windows
  ('win',): {
    'credential_path': ('c:\\creds\\service_accounts\\'
                        'service-account-luci-logdog-publisher.json'),
    'streamserver': 'net.pipe',
  },
}


# Params are parameters for this specific master/builder configuration.
#
# Loaded by '_get_params'.
Params = collections.namedtuple('Params', (
    'project', 'cipd_tag', 'api', 'mastername', 'buildername', 'buildnumber',
    'generation',
))


# LogDog bootstrapping configuration.
Config = collections.namedtuple('Config', (
    'params', 'plat', 'host', 'prefix', 'tags',
    'service_account_path',
))


def _check_call(cmd, **kwargs):
  LOGGER.debug('Executing command: %s', cmd)
  subprocess.check_call(cmd, **kwargs)


def _get_platform():
  """Returns (Platform): The constructed Platform object.

  Raises:
    TypeError: if a required configuration key/parameter is not available.
  """
  return Platform(**infra_platform.cascade_config(_PLATFORM_CONFIG))


def all_cipd_packages():
  """Generator which yields all referenced CIPD packages."""
  # All CIPD packages are in top-level platform config.
  pcfg = infra_platform.cascade_config(_PLATFORM_CONFIG, plat=())
  for name in (pcfg['butler'], pcfg['annotee']):
    for version in (_STABLE_CIPD_TAG, _CANARY_CIPD_TAG):
      yield cipd.CipdPackage(name=name, version=version)


def _load_params_dict(mastername):
  """Returns (dict or None): The parameters for the specified master.

  The parameters are loaded by locating the 'logdog-params.pyl' file for the
  currently-executing waterfall. If found, it will be parsed and the waterfall's
  parameters will be loaded from it.

  If no parameter file could be found, or no parameters are defined for the
  specified waterfall, None will be returned.

  Args:
    mastername (str): The name of the master whose parameters will be loaded.

  Raises:
    NotBootstrapped: If the parameters dictionary could not be loaded.
  """
  # Identify the directory where the master is located.
  try:
    master_dir = chromium_utils.MasterPath(mastername)
  except LookupError as e:
    LOGGER.warning('Unable to find directory for master [%s] (%s)',
                   mastername, e)
    raise NotBootstrapped('No master directory')

  # 'master_dir' is:
  #   <build_dir>/masters/<master_name>
  #
  #  We want to look up:
  #   <build_dir>/scripts/slave/logdog-params.pyl
  #
  params_path = os.path.join(master_dir, os.pardir, os.pardir, 'scripts',
                             'slave', 'logdog-params.pyl')
  if not os.path.isfile(params_path):
    LOGGER.warning('No LogDog parameters at: [%s]', params_path)
    raise NotBootstrapped('No parameters file.')

  # Load and parse our parameters.
  LOGGER.debug('Loading LogDog parameters from: [%s]', params_path)
  with open(params_path, 'r') as fd:
    params_data = fd.read()

  try:
    params = eval(params_data)
    assert isinstance(params, dict)
  except SyntaxError as e:
    LOGGER.error('Failed to parse params from [%s]: %s', params_path, e)
    raise NotBootstrapped('Invalid parameters file.')
  except AssertionError:
    LOGGER.error('Params parsed to non-dictionary (%s)', type(params).__name__)
    raise NotBootstrapped('Parameters file does not contain a dictionary.')
  return params


def _get_params(properties):
  """Returns (Params): Parameters for the given properties.

  The parameters are loaded by locating the 'logdog-params.pyl' file for the
  currently-executing waterfall. If found, it will be parsed and the waterfall's
  parameters will be loaded from it.

  If no parameter file could be found, or no parameters are defined for the
  specified waterfall, None will be returned.

  Args:
    properties (dict): Build property dictionary.

  Raises:
    NotBootstrapped: If parameters could not be built, or if this master/builder
        is disabled.
  """
  # Extract our required properties.
  props = tuple(properties.get(f) for f in (
      'mastername', 'buildername', 'buildnumber'))
  if not all(props):
    LOGGER.warning('Missing mastername/buildername/buildnumber properties.')
    raise NotBootstrapped('Insufficient properties.')
  mastername, buildername, buildnumber = props

  # Find our project name and master config.
  project = None
  for project, masters in sorted(_load_params_dict(mastername).items()):
    master_config = masters.get(mastername)
    if master_config is not None:
      break
  else:
    LOGGER.info('No master config found for [%s].', mastername)
    raise NotBootstrapped('No master config.')

  # Get builder config map, allowing overrides if one is defined for either the
  # specific builder or all builders ('*').
  builder_map = {
    'enabled': True,
    'cipd_tag': '$stable',
    'generation': None,
  }
  for bn in (buildername, '*'):
    bn_map = master_config.get(bn)
    if bn_map is not None:
      builder_map.update(bn_map)
      break

  # If our builder is not enabled, we are done.
  if not builder_map['enabled']:
    LOGGER.info('LogDog is disabled for master / builder [%s / %s].',
                mastername, buildername)
    raise NotBootstrapped('LogDog is disabled.')

  # Resolve our CIPD tag.
  cipd_tag = builder_map['cipd_tag']
  cipd_tag = _CIPD_TAG_MAP.get(cipd_tag, cipd_tag)

  # Determine our API version.
  api = _CIPD_TAG_API_MAP.get(cipd_tag, _CIPD_TAG_API_MAP[_STABLE_CIPD_TAG])

  return Params(
      project=project,
      cipd_tag=cipd_tag,
      api=api,
      mastername=mastername,
      buildername=buildername,
      buildnumber=buildnumber,
      generation=builder_map['generation'],
  )


def _get_streamserver_uri(rt, typ):
  """Returns (str): The Butler StreamServer URI.

  Args:
    rt (RobustTempdir): context for temporary directories.
    typ (str): The type of URI to generate. One of: ['unix'].
  Raises:
    BootstrapError: if |typ| is not a known type.
  """
  if typ == 'unix':
    # We have to use a custom temporary directory here. This is due to the path
    # length limitation on UNIX domain sockets, which is generally 104-108
    # characters. We can't make that assumption about our standard recipe
    # temporary directory.
    #
    # Bots run out of "/b/build", so this will form a path starting at
    # "/b/build/.recipe_runtime/tmp-<random>/butler.sock", which is well below
    # the socket name size limit.
    #
    # We don't drop this in "/tmp" because several build scripts assume
    # ownership of that directory and blindly clear it as part of cleanup, and
    # this socket is too important to risk.
    sockdir = rt.tempdir(env.Build)
    uri = 'unix:%s' % (os.path.join(sockdir, 'butler.sock'),)
    if len(uri) > 104:
      raise BootstrapError('Generated URI exceeds UNIX domain socket '
                                 'name size: %s' % (uri,))
    return uri
  elif typ == 'net.pipe':
    return 'net.pipe:LUCILogDogButler'
  else:
    raise BootstrapError('No streamserver URI generator.')


def _get_service_account_json(opts, credential_path):
  """Returns (str/None): If specified, the path to the service account JSON.

  This method probes the local environment and returns a (possibly empty) list
  of arguments to add to the Butler command line for authentication.

  If we're running on a GCE instance, no arguments will be returned, as GCE
  service account is implicitly authenticated. If we're running on Baremetal,
  a path to those credentials will be returned.

  Raises:
    |BootstrapError| if no credentials could be found.
  """
  if opts.logdog_debug_out_file:
    return None

  path = opts.logdog_service_account_json
  if path:
    return path

  if gce.Authenticator.is_gce():
    LOGGER.info('Running on GCE. No credentials necessary.')
    return GCE_CREDENTIALS

  if os.path.isfile(credential_path):
    return credential_path

  raise BootstrapError('Could not find service account credentials. '
                       'Tried: %s' % (credential_path,))


def _build_prefix(params):
  """Constructs a LogDog stream prefix and tags from the supplied properties.

  The returned prefix is of the form:
  bb/<mastername>/<buildername>/<buildnumber>

  Any path-incompatible characters will be flattened to underscores.

  Returns (prefix, tags):
    prefix (str): the LogDog stream prefix.
    tags (dict): A dict of LogDog tags to add.
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

  mastername, buildername, buildnumber = (normalize(p) for p in (
      params.mastername, params.buildername, params.buildnumber))

  parts = ['bb', mastername, buildername]
  if params.generation:
    parts += [params.generation]
  parts += [buildnumber]
  prefix = '/'.join(str(x) for x in parts)

  viewer_url = (
      'https://luci-milo.appspot.com/buildbot/%(mastername)s/%(buildername)s/'
      '%(buildnumber)d' % params._asdict())
  tags = collections.OrderedDict((
      ('buildbot.master', mastername),
      ('buildbot.builder', buildername),
      ('buildbot.buildnumber', str(buildnumber)),
      ('logdog.viewer_url', viewer_url),
  ))
  return prefix, tags


def _make_butler_output(opts, _cfg):
  """Returns a Butler output string.
  """
  if opts.logdog_debug_out_file:
    return 'file,path="%s"' % (opts.logdog_debug_out_file,)
  return 'logdog'


def _prune_arg(l, key, extra=0):
  """Removes list entry "key" and "extra" additional entries, if present.

  Args:
    l (list): The list to prune.
    key (object): The list entry to identify and remove.
    extra (int): Additional entries after key to prune, if found.
  """
  try:
    idx = l.index(key)
    args = l[idx:idx+extra+1]
    del(l[idx:idx+extra+1])
    return args
  except ValueError:
    return None


def get_config(opts, properties):
  """Returns (Config): the LogDog bootstrap configuration.

  This probes the supplied options and properties and resolves the full
  bootstrap configuration from them.

  Raises:
    NotBootstrapped: If the environment is not configured to be bootstrapped.
  """
  if opts.logdog_disable:
    raise NotBootstrapped('LogDog explicitly disabled (--disable-logdog).')

  # If we have LOGDOG_STREAM_PREFIX defined, we are already bootstrapped. Don't
  # start a new instance.
  #
  # LOGDOG_STREAM_PREFIX is set by the Butler when it bootstraps a process, so
  # it should be set for all child processes of the initial bootstrap.
  if os.environ.get('LOGDOG_STREAM_PREFIX') is not None:
    raise NotBootstrapped(
       'LOGDOG_STREAM_PREFIX in enviornment, refusing to nest bootstraps.')

  # Load our bootstrap parameters based on our master/builder.
  params = _get_params(properties)

  # Get our platform configuration. This will fail if any fields are missing.
  plat = _get_platform()

  # Determine LogDog prefix.
  prefix, tags = _build_prefix(params)

  host = opts.logdog_host or plat.host
  if not host:
    raise BootstrapError('No host is defined')

  # Generate our service account path.
  service_account_path = _get_service_account_json(opts, plat.credential_path)

  return Config(
      params=params,
      plat=plat,
      host=host,
      prefix=prefix,
      tags=tags,
      service_account_path=service_account_path,
  )


def bootstrap(rt, opts, basedir, tempdir, properties, cmd):
  """Executes the recipe engine, bootstrapping it through LogDog/Annotee.

  This method executes the recipe engine, bootstrapping it through
  LogDog/Annotee so its output and annotations are streamed to LogDog. The
  bootstrap is configured to tee the annotations through STDOUT/STDERR so they
  will still be sent to BuildBot.

  The overall setup here is:
  [annotated_run.py] => [logdog_butler] => [logdog_annotee] => [recipes.py]

  Args:
    rt (RobustTempdir): context for temporary directories.
    opts (argparse.Namespace): Command-line options.
    basedir (str): The base (non-temporary) recipe directory.
    tempdir (str): The path to the session temporary directory.
    properties (dict): Build properties.
    cmd (list): The recipe runner command list to bootstrap.

  Returns (BootstrapState): The populated bootstrap state.

  Raises:
    NotBootstrapped: if the recipe engine was not executed because the
        LogDog bootstrap requirements are not available.
    BootstrapError: if there was an error bootstrapping the recipe runner
        through LogDog.
  """
  # Load bootstrap configuration (may raise NotBootstrapped).
  cfg = get_config(opts, properties)

  # Determine LogDog prefix.
  LOGGER.debug('Using log stream prefix: [%s]', cfg.prefix)

  # Install our Butler/Annotee packages from CIPD.
  cipd_path = os.path.join(basedir, '.recipe_cipd')

  packages = (
      # Butler
      cipd.CipdPackage(
          name=cfg.plat.butler,
          version=cfg.params.cipd_tag),

      # Annotee
      cipd.CipdPackage(
          name=cfg.plat.annotee,
          version=cfg.params.cipd_tag),
  )
  try:
    cipd_bootstrap_v2.install_cipd_packages(cipd_path, *packages)
  except Exception:
    LOGGER.exception('Failed to install LogDog CIPD packages: %s', packages)
    raise BootstrapError('Failed to install CIPD packages.')

  def cipd_bin(base):
    return os.path.join(cipd_path, base + infra_platform.exe_suffix())

  def var(title, v, dflt):
    v = v or dflt
    if not v:
      raise NotBootstrapped('No value for [%s]' % (title,))
    return v

  butler = var('butler', opts.logdog_butler_path, cipd_bin('logdog_butler'))
  if not os.path.isfile(butler):
    raise NotBootstrapped('Invalid Butler path: %s' % (butler,))

  annotee = var('annotee', opts.logdog_annotee_path, cipd_bin('logdog_annotee'))
  if not os.path.isfile(annotee):
    raise NotBootstrapped('Invalid Annotee path: %s' % (annotee,))

  # Determine LogDog verbosity.
  if opts.logdog_verbose == 0:
    log_level = 'warning'
  elif opts.logdog_verbose == 1:
    log_level = 'info'
  else:
    log_level = 'debug'

  # Generate our Butler stream server URI.
  streamserver_uri = _get_streamserver_uri(rt, cfg.plat.streamserver)

  # If we are using file sentinel-based bootstrap error detection, enable.
  bootstrap_result_path = os.path.join(tempdir, 'bootstrap_result.json')

  # Dump the bootstrapped Annotee command to JSON for Annotee to load.
  #
  # Annotee can run accept bootstrap parameters through either JSON or
  # command-line, but using JSON effectively steps around any sort of command-
  # line length limits such as those experienced on Windows.
  cmd_json = os.path.join(tempdir, 'logdog_annotee_cmd.json')
  with open(cmd_json, 'w') as fd:
    json.dump(cmd, fd)

  # Butler Command, global options.
  butler_args = [
      butler,
      '-log-level', log_level,
      '-project', cfg.params.project,
      '-prefix', cfg.prefix,
      '-coordinator-host', cfg.host,
      '-output', _make_butler_output(opts, cfg),
  ]
  for k, v in cfg.tags.iteritems():
    if v:
      k = '%s=%s' % (k, v)
    butler_args += ['-tag', k]
  if cfg.service_account_path:
    butler_args += ['-service-account-json', cfg.service_account_path]
  if cfg.plat.max_buffer_age:
    butler_args += ['-output-max-buffer-age', cfg.plat.max_buffer_age]
  butler_args += ['-io-keepalive-stderr', '5m']

  # Butler: subcommand run.
  butler_run_args = [
      '-stdout', 'tee=stdout',
      '-stderr', 'tee=stderr',
      '-streamserver-uri', streamserver_uri,
  ]

  # Annotee Command.
  annotee_args = [
      annotee,
      '-log-level', log_level,
      '-name-base', 'recipes',
      '-print-summary',
      '-tee', 'annotations',
      '-json-args-path', cmd_json,
      '-result-path', bootstrap_result_path,
  ]

  # API transformation switch. Please prune as API versions become
  # unused.
  #
  # NOTE: Please update the above comment as new API versions and translation
  # functions are added.
  start_api = cur_api = max(_CIPD_TAG_API_MAP.itervalues())

  # Assert that we've hit the target "params.api".
  assert cur_api == cfg.params.api, 'Failed to transform API %s => %s' % (
      start_api, cfg.params.api)

  cmd = butler_args + ['run'] + butler_run_args + ['--'] + annotee_args
  return BootstrapState(cfg, cmd, bootstrap_result_path)


def get_annotation_url(cfg):
  """Returns (str): LogDog stream URL for the configured annotation stream.

  Args:
    cfg (Config): The bootstrap config.
  """
  return 'logdog://%(host)s/%(project)s/%(prefix)s/+/recipes/annotations' % {
      'host': cfg.host,
      'project': cfg.params.project,
      'prefix': cfg.prefix,
  }


def annotate(cfg, stream):
  """Writes LogDog bootstrap annotations to an annotation stream.

  Args:
    stream (annotator.StructuredAnnotationStream): The annotation stream to
        write to.
  """
  annotation_url = get_annotation_url(cfg)
  with stream.step('LogDog Bootstrap') as st:
    st.set_build_property('logdog_project', json.dumps(cfg.params.project))
    st.set_build_property('logdog_prefix', json.dumps(cfg.prefix))
    st.set_build_property('log_location', json.dumps(annotation_url))


class BootstrapState(object):
  def __init__(self, cfg, cmd, bootstrap_result_path):
    self._cfg = cfg
    self._cmd = cmd
    self._bootstrap_result_path = bootstrap_result_path

  @property
  def cmd(self):
    """Returns (list): The Butler-bootstrapped command."""
    return self._cmd[:]

  def get_result(self):
    """Retrieves and returns the return code of the bootstrapped process.

    Returns (int): The bootstrapped process' return code.

    Raises:
      BootstrapError: If the bootstrapped process didn't even run.
    """
    try:
      with open(self._bootstrap_result_path) as fd:
        result = json.load(fd)
    except (IOError, ValueError) as e:
      raise BootstrapError('Failed to open bootstrap result file [%s]: %s' % (
            self._bootstrap_result_path, e))
    try:
      return result['return_code']
    except KeyError as e:
      raise BootstrapError('Invalid bootstrap result file [%s]: %s' % (
          self._bootstrap_result_path, e))

  def annotate(self, stream):
    """Writes LogDog bootstrap annotations to an annotation stream.

    Args:
      stream (annotator.StructuredAnnotationStream): The annotation stream to
          write to.
    """
    annotate(self._cfg, stream)


def _argparse_type_trinary(v):
  v = v.lower()
  if v == '':
    return None
  if v in ('true', 't', 'yes', 'y', '1'):
    return True
  if v in ('false', 'f', 'no', 'n', '0'):
    return False
  raise argparse.ArgumentTypeError('%r is not a valid trinary value' % (v,))


def add_arguments(parser):
  parser.add_argument('--logdog-verbose',
      action='count', default=0,
      help='Increase LogDog verbosity. This can be specified multiple times.')
  parser.add_argument('--logdog-disable', action='store_true',
      help='Disable LogDog bootstrapping, even if otherwise configured.')
  parser.add_argument('--logdog-butler-path',
      help='Path to the LogDog Butler. If empty, one will be probed/downloaded '
           'from CIPD.')
  parser.add_argument('--logdog-annotee-path',
      help='Path to the LogDog Annotee. If empty, one will be '
           'probed/downloaded from CIPD.')
  parser.add_argument('--logdog-service-account-json',
      help='Path to the service account JSON. If one is not provided, the '
           'local system credentials will be used.')
  parser.add_argument('--logdog-host',
      help='Override the LogDog host.')
  parser.add_argument('--logdog-output-service',
      help='If specified, use <service>-dot-<host> for output service '
           'configuration.')
  parser.add_argument('--logdog-debug-out-file',
      help='(Debug) Write logs to this text protobuf file instead of a live '
           'service.')
