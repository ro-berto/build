#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Execute buildsteps on the slave.

This is the buildrunner, a script designed to run builds on the slave. It works
by mocking out the structures of a Buildbot master, then running a slave under
that 'fake' master. There are several benefits to this approach, the main one
being that build code can be changed and reloaded without a master restart.

Usage is detailed with -h.
"""

import copy
import json
import optparse
import os
import re
import sys
import time
import urllib

# pylint: disable=C0323,W0611,F0401,R0201

# slaves are currently set to buildbot 0.7, while masters to 0.8
# these are required to override 0.7 and are necessary until slaves
# have been transitioned to 0.8
pathjack = lambda x: sys.path.insert(
    0, os.path.abspath(os.path.join('..', '..', '..', 'third_party', x)))
pathjack('buildbot_8_4p1')
pathjack('buildbot_slave_8_4')
pathjack('twisted_10_2')
pathjack('sqlalchemy_0_7_1')
pathjack('sqlalchemy_migrate_0_7_1')
pathjack('jinja2')
pathjack('decorator_3_3_1')

# this is required for master.cfg to be loaded properly, since setuptools
# is only required by runbuild.py at the moment.
pathjack('setuptools-0.6c11')

from buildbot.process import base
from buildbot.process import builder as real_builder
from buildbot.process.properties import Properties
from buildbot.status import build as build_module
from buildbot.status import builder
from buildbot.status.results import EXCEPTION
from buildbot.status.results import FAILURE
import buildbot.util
from buildslave.commands import registry
from buildslave.runprocess import shell_quote
from common import chromium_utils
from slave import chromium_commands
from twisted.internet import defer
from twisted.internet import reactor
from twisted.python.reflect import accumulateClassList
from twisted.python.reflect import namedModule
from twisted.spread import pb
from twisted.spread import util


def get_args():
  """Process command-line arguments."""

  prog_desc = 'Executes a Buildbot build locally, without a master.'
  usage = '%prog [options] <master directory> [builder or slave hostname]'
  parser = optparse.OptionParser(usage=(usage + '\n\n' + prog_desc))
  parser.add_option('--list-masters', action='store_true',
                    help='list masters in search path')
  parser.add_option('--master-dir', help='specify a master directory '
                    'instead of a mastername')
  parser.add_option('--list-builders', help='list all available builders for '
                    'this master', action='store_true')
  parser.add_option('-s', '--slavehost', metavar='slavehost',
                    help='specify a slavehost to operate as')
  parser.add_option('-b', '--builder', metavar='builder',
                    help='string specified is a builder name')
  parser.add_option('--list-steps', action='store_true',
                    help='list steps in factory, but don\'t execute them')
  parser.add_option('--stepfilter', help='only run steps that match the '
                    'stepfilter regex')
  parser.add_option('--stepreject', help='reject any steps that match the '
                    'stepfilter regex')
  parser.add_option('--logfile', default='build_runner.log',
                    help='log build runner output to file (use - for stdout). '
                    'default: %default')
  parser.add_option('--hide-header', help='don\'t log environment information'
                    ' to logfile', action='store_true')
  parser.add_option('--svn-rev', help='revision to check out, default: '
                    'LKGR')
  parser.add_option('--master-cfg', default='master.cfg',
                    help='filename of the master config. default: %default')
  parser.add_option('--build-properties', action='callback',
                    callback=chromium_utils.convert_json, type='string',
                    nargs=1, default={},
                    help='build properties in JSON format')
  parser.add_option('--factory-properties', action='callback',
                    callback=chromium_utils.convert_json, type='string',
                    nargs=1, default={},
                    help='factory properties in JSON format')
  parser.add_option('--output-build-properties', action='store_true',
                    help='output JSON-encoded build properties extracted from'
                    ' the build')
  parser.add_option('--output-factory-properties', action='store_true',
                    help='output JSON-encoded build properties extracted from'
                    'the build factory')
  parser.add_option('--annotate', action='store_true',
                    help='format output to work with the Buildbot annotator')

  return parser.parse_args()


def read_config(basedir, config_file, suppress=False):
  canonical_basedir = os.path.abspath(os.path.expanduser(basedir))
  canonical_config = os.path.join(basedir, config_file)
  localDict = {'basedir': canonical_basedir,
               '__file__': canonical_config}
  try:
    f = open(canonical_config, 'r')
  except IOError as err:
    errno, strerror = err
    print >>sys.stderr, 'Error %d opening %s: %s' % (errno,
        canonical_config, strerror)
    return None

  mycwd = os.getcwd()
  os.chdir(canonical_basedir)
  beforepath = list(sys.path)  # make a 'backup' of it
  sys.path.append(canonical_basedir)
  try:
    exec f in localDict
  except Exception as e:
    if not suppress:
      print >>sys.stderr, ('error while parsing %s: ' % canonical_config), e
    return None
  finally:
    sys.path = beforepath
    os.chdir(mycwd)
    f.close()

  return localDict


def pp_internal(items, columns, title, notfound):
  if not items:
    print
    print notfound
    return

  itemdata = {}
  for col in columns:
    itemdata[col] = [s[col] if col in s else 'n/a' for s in items]

  lengths = {}
  for col in columns:
    datalen = max([len(x) for x in itemdata[col]])
    lengths[col] = max(len(col), datalen)

  spacing = 4
  maxwidth = sum([lengths[col] for col in columns]) + (
      spacing * (len(columns) - 1))

  spac = ' ' * spacing

  print
  print title
  print
  print spac.join([col.rjust(lengths[col]) for col in columns])
  print '-' * maxwidth

  for i in range(len(items)):
    print spac.join([itemdata[col][i].rjust(lengths[col]) for col in columns])


def pp_builders(builders, master):
  """Pretty-print a list of builders from a master."""

  columns = ['name', 'slavename', 'category']
  title = 'outputting builders for: %s' % master
  notfound = 'no builders found.'
  pp_internal(builders, columns, title, notfound)


def pp_masters(masterpairs):
  masters = []
  for mastername, path in masterpairs:
    abspath = os.path.abspath(path)
    relpath = os.path.relpath(path)
    shortpath = abspath if len(abspath) < len(relpath) else relpath
    master = {}
    master['mastername'] = mastername
    master['path'] = shortpath
    masters.append(master)

  columns = ['mastername', 'path']
  title = 'listing available masters:'
  notfound = 'no masters found.'
  pp_internal(masters, columns, title, notfound)


def dup_slaves(builders):
  """Expand builders which have multiple slaves into multiple builders with one
  slave each."""

  def arrayify(possible_array):
    """Convert 'string' into ['string']. Leave actual arrays alone."""
    if isinstance(possible_array, basestring):
      return [possible_array]
    return possible_array

  duped_slaves = []
  for b in builders:
    for slave in arrayify(b['slavenames']):
      newbuilder = copy.deepcopy(b)
      newbuilder['slavename'] = slave
      duped_slaves.append(newbuilder)
  return duped_slaves


def search(builders, spec):
  """Return a list of builders which match what is specified in 'spec'."""
  if 'builder' in spec:
    return [b for b in builders if b['name'] ==
            spec['builder']]
  elif 'hostname' in spec:
    return [b for b in builders if b['slavename']
            == spec['hostname']]
  else:
    return [b for b in builders if (b['name'] ==
            spec['either']) or (b['slavename'] == spec['either'])]


def get_masters():
  """Return a pair of (mastername, path) for all masters found."""

  # note: ListMasters uses master.cfg hardcoded as part of its search path
  def parse_master_name(masterpath):
    """Returns a mastername from a pathname to a master."""
    _, tail = os.path.split(masterpath)
    sep = '.'
    hdr = 'master'
    chunks = tail.split(sep)
    if not chunks or chunks[0] != hdr or len(chunks) < 2:
      raise ValueError('unable to parse mastername from path! (%s)' % tail)
    return sep.join(chunks[1:])

  return [(parse_master_name(m), m) for m in chromium_utils.ListMasters()]


def only_get_one(seq, key, source):
  """Confirm a sequence only contains one unique value and return it."""

  def uniquify(seq):
    return list(frozenset(seq))
  res = uniquify([s[key] for s in seq])

  if len(res) > 1:
    print >>sys.stderr, 'error: %s too many %ss:' % (source, key)
    for r in res:
      print '  ', r
    return None
  elif not res:
    print 'error: %s zero %ss' % (source, key)
    return None
  else:
    return res[0]


def get_builder(slaves, keyval):
  """Return unique builder name from a list of builders."""
  errstring = 'string \'%s\' matches' % keyval
  return only_get_one(slaves, 'name', errstring)


def choose(builders, spec):
  """Search through builders matching 'spec' and return it."""

  candidates = search(builders, spec)
  buildername = get_builder(candidates, spec.values()[0])

  if not buildername:
    return None

  blder = [b for b in builders if b['name'] == buildername][0]

  return blder


def get_lkgr():
  """Connect to chromium LKGR server and get LKGR revision."""

  try:
    conn = urllib.urlopen('http://chromium-status.appspot.com/lkgr')
  except IOError:
    return (None, 'Error connecting to LKGR server! Is your internet '
            'connection working properly?')
  try:
    rev = int('\n'.join(conn.readlines()))
  except IOError:
    return (None, 'Error connecting to LKGR server! Is your internet '
            'connection working properly?')
  except ValueError:
    return None, 'LKGR server returned malformed data! Aborting...'
  finally:
    conn.close()

  return rev, 'ok'


def args_ok(inoptions, pos_args):
  """Verify arguments are correct and prepare args dictionary."""

  if inoptions.factory_properties:
    for key in inoptions.factory_properties:
      setattr(inoptions, key, inoptions.factory_properties[key])

  if inoptions.list_masters:
    return True

  if inoptions.build_properties and not inoptions.master_dir:
    if inoptions.build_properties['mastername']:
      inoptions.mastername = inoptions.build_properties['mastername']
    else:
      print >>sys.stderr, 'error: build properties did not specify a ',
      print >>sys.stderr, 'mastername'
      return False
  else:
    if not (inoptions.master_dir or pos_args):
      print >>sys.stderr, 'error: you must provide a mastername or ',
      print >>sys.stderr, 'directory!'
      return False
    else:
      if not inoptions.master_dir:
        inoptions.mastername = pos_args.pop(0)

  if inoptions.stepfilter:
    if inoptions.stepreject:
      print >>sys.stderr, ('Error: can\'t specify both stepfilter and '
                           'stepreject at the same time!')
      return False

    try:
      inoptions.step_regex = re.compile(inoptions.stepfilter)
    except re.error as e:
      print >>sys.stderr, 'Error compiling stepfilter regex \'%s\': %s' % (
          inoptions.stepfilter, e)
      return False
  if inoptions.stepreject:
    if inoptions.stepfilter:
      print >>sys.stderr, ('Error: can\'t specify both stepfilter and '
                           'stepreject at the same time!')
      return False
    try:
      inoptions.stepreject_regex = re.compile(inoptions.stepreject)
    except re.error as e:
      print >>sys.stderr, 'Error compiling stepreject regex \'%s\': %s' % (
          inoptions.stepfilter, e)
      return False

  if inoptions.list_builders:
    return True

  if inoptions.build_properties and not (inoptions.slavehost or
                                         inoptions.builder):
    if inoptions.build_properties['buildername']:
      inoptions.builder = inoptions.build_properties['buildername']
    else:
      print >>sys.stderr, 'error: build properties did not specify a '
      print >>sys.stderr, 'buildername!'
      return False
  else:
    if not (pos_args or inoptions.slavehost or inoptions.builder):
      print >>sys.stderr, 'Error: you must provide a builder or slave hostname!'
      return False

  inoptions.spec = {}
  if inoptions.builder:
    inoptions.spec['builder'] = inoptions.builder
  elif inoptions.slavehost:
    inoptions.spec['hostname'] = inoptions.slavehost
  else:
    inoptions.spec['either'] = pos_args.pop(0)

  if inoptions.list_steps:
    return True

  if inoptions.logfile == '-' or inoptions.annotate:
    inoptions.log = sys.stdout
  else:
    try:
      inoptions.log = open(inoptions.logfile, 'w')
    except IOError as err:
      errno, strerror = err
      print >>sys.stderr, 'Error %d opening logfile %s: %s' % (
          inoptions.logfile, errno, strerror)
      return False

  if hasattr(inoptions, 'build_properties') and not hasattr(
      inoptions, 'svn_rev'):
    if inoptions.build_properties['revision']:
      try:
        setattr(inoptions, 'revision', int(
          inoptions.build_properties['revision']))
      except ValueError:
        setattr(inoptions, 'revision', None)

    if not (hasattr(inoptions, 'revision') and inoptions.revision) and (
        inoptions.build_properties['got_revision']):
      try:
        setattr(inoptions, 'revision', int(
          inoptions.build_properties['got_revision']))
      except ValueError:
        setattr(inoptions, 'revision', None)

      if not inoptions.revision or inoptions.revision < 1:
        print >>sys.stderr, 'Error: revision must be a non-negative integer!'
        return False
    else:
      print >>sys.stderr, 'error: build properties did not specify a revision!'
      return False

    print >>sys.stderr, 'using revision: %d' % inoptions.revision
    inoptions.build_properties['revision'] = '%d' % inoptions.revision
  else:
    if inoptions.svn_rev:
      try:
        inoptions.revision = int(inoptions.svn_rev)
      except ValueError:
        inoptions.revision = None

      if not inoptions.revision or inoptions.revision < 1:
        print >>sys.stderr, 'Error: svn rev must be a non-negative integer!'
        return False

      if not inoptions.annotate:
        print >>sys.stderr, 'using revision: %d' % inoptions.revision
    else:  # nothing specified on command line, let's check LKGR
      inoptions.revision, errmsg = get_lkgr()
      if not inoptions.revision:
        print >>sys.stderr, errmsg
        return False
      if not inoptions.annotate:
        print >>sys.stderr, 'using LKGR: %d' % inoptions.revision

  return True


class FakeChange(object):
  """Represents a mock of a change to the source tree. See
  http://buildbot.net/buildbot/docs/0.8.5/reference/buildbot.changes.changes.
  Change-class.html for what I'm really supposed to be."""

  properties = Properties()
  who = 'me'


class FakeSource(object):
  """A mocked-up SourceStamp, which encapsulates all the parameters of the
  source checkout to build. See http://buildbot.net/buildbot/docs/latest/
  reference/buildbot.sourcestamp.SourceStamp-class.html for reference."""

  def __init__(self, setup):
    self.revision = setup.get('revision')
    self.branch = setup.get('branch')
    self.repository = setup.get('repository')
    self.project = setup.get('project')
    self.patch = setup.get('patch')
    self.changes = [FakeChange()]

    if not self.branch: self.branch = None
    if not self.revision:
      raise ValueError('must specify a revision!')


class FakeRequest(object):
  """A mocked-up BuildRequest, which encapsulates the parameters of the build.
  See http://buildbot.net/buildbot/docs/0.8.6/reference/buildbot.process.
  buildrequest.BuildRequest-class.html for reference."""

  reason = 'Because'
  properties = Properties()

  def __init__(self, buildargs):
    self.source = FakeSource(buildargs)

  def mergeWith(self, others):
    return self.source

  def mergeReasons(self, others):
    return self.reason


class FakeSlave(util.LocalAsRemote):
  """A mocked combination of BuildSlave and SlaveBuilder. Controls the build
  by kicking off steps and receiving messages as those steps run. See
  http://buildbot.net/buildbot/docs/0.7.12/reference/buildbot.slave.bot.
  SlaveBuilder-class.html and http://buildbot.net/buildbot/docs/0.8.3/
  reference/buildbot.buildslave.BuildSlave-class.html for reference."""

  def __init__(self, builddir, slavename):
    self.slave = self
    self.properties = Properties()
    self.slave_basedir = '.'
    self.basedir = '.'  # this must be '.' since I combine slavebuilder
                        # and buildslave
    self.path_module = namedModule('posixpath')
    self.slavebuilddir = builddir
    self.builddir = builddir
    self.slavename = slavename
    self.usePTY = True
    self.updateactions = []
    self.unicode_encoding = 'utf8'
    self.command = None
    self.remoteStep = None

  def addUpdateAction(self, action):
    self.updateactions.append(action)

  def getSlaveCommandVersion(self, command, oldversion=None):
    return command

  def sendUpdate(self, data):
    for action in self.updateactions:
      action(data)
    self.remoteStep.remote_update([[data, 0]])

  def messageReceivedFromSlave(self):
    return None

  def sync_startCommand(self, stepref, stepId, command, cmdargs):
    try:
      cmdfactory = registry.getFactory(command)
    except KeyError:
      raise UnknownCommand("unrecognized SlaveCommand '%s'" % command)

    self.command = cmdfactory(self, stepId, cmdargs)

    self.remoteStep = stepref
    d = self.command.doStart()
    d.addCallback(stepref.remote_complete)
    return d


def propertiesToJSON(props):
  propdict = props.asDict()
  cleandict = {}
  for k in propdict:
    cleandict[k] = propdict[k][0]

  return json.dumps(cleandict)


class UnknownCommand(pb.Error):
  """Represent an unknown slave command."""
  pass


class ReturnStatus(object):
  """Singleton needed for global return code."""

  def __init__(self):
    self.code = 0


def buildException(status, why):
  """Output error and stop further steps."""
  print >>sys.stderr, 'build error encountered:', why
  print >>sys.stderr, 'aborting build'
  status.code = 1
  reactor.callFromThread(reactor.stop)


def finished():
  """Tear down twisted session."""
  print >>sys.stderr, 'build completed successfully'
  reactor.callFromThread(reactor.stop)


def startNextStep(steps, run_status, prog_args):
  """Run the next step, optionally skipping if there is a stepfilter."""

  def getNextStep():
    if not steps:
      return None
    return steps.pop(0)
  try:
    s = getNextStep()
    if hasattr(prog_args, 'step_regex'):
      while s and not prog_args.step_regex.search(s.name):
        print >>sys.stderr, 'skipping step: ' + s.name
        s = getNextStep()
    if hasattr(prog_args, 'stepreject_regex'):
      while s and prog_args.stepreject_regex.search(s.name):
        print >>sys.stderr, 'skipping step: ' + s.name
        s = getNextStep()
  except StopIteration:
    s = None
  if not s:
    return finished()

  print >>sys.stderr, 'performing step: ' + s.name,
  s.step_status.stepStarted()
  d = defer.maybeDeferred(s.startStep, s.buildslave)
  d.addCallback(lambda x: checkStep(x, steps,
                                    run_status, prog_args))
  d.addErrback(lambda x: buildException(run_status, x))
  return d


def checkStep(rc, steps, run_status, prog_args):
  """Check if the previous step succeeded before continuing."""

  if (rc == FAILURE) or (rc == EXCEPTION):
    buildException(run_status, 'previous command failed')
  else:
    defer.maybeDeferred(lambda x: startNextStep(x,
                                                run_status, prog_args), steps)


def generate_steplist(my_factory):
  """Print out a list of steps in the builder."""
  steps = []
  stepnames = {}

  for factory, cmdargs in my_factory.steps:
    cmdargs = cmdargs.copy()
    try:
      step = factory(**cmdargs)
    except:
      print >>sys.stderr, ('error while creating step, factory=%s, args=%s'
                           % (factory, cmdargs))
      raise
    name = step.name
    if name in stepnames:
      count = stepnames[name]
      count += 1
      stepnames[name] = count
      name = step.name + ('_%d' % count)
    else:
      stepnames[name] = 0
    step.name = name

    #TODO: is this a bug in FileUpload?
    if not hasattr(step, 'description') or not step.description:
      step.description = [step.name]
    if not hasattr(step, 'descriptionDone') or not step.descriptionDone:
      step.descriptionDone = [step.name]

    step.locks = []
    steps.append(step)

  return steps


class FakeMaster:
  def __init__(self, mastername):
    self.db = None
    self.master_name = mastername
    self.master_incarnation = None


class FakeBotmaster:
  def __init__(self, mastername, properties=Properties()):
    self.master = FakeMaster(mastername)
    self.parent = self
    self.properties = properties


def choose_master(searchname):
  """Given a string, load all masters and pick the master that matches."""
  masters = get_masters()
  masternames = []
  master_lookup = {}
  for mn, path in masters:
    master = {}
    master['mastername'] = mn
    master_lookup[mn] = path
    masternames.append(master)

  candidates = [mn for mn in masternames if mn['mastername'] == searchname]

  errstring = 'string \'%s\' matches' % searchname
  master = only_get_one(candidates, 'mastername', errstring)
  if not master:
    return None

  return master_lookup[master]


def process_steps(steplist, build, buildslave, build_status, basedir):
  """Attach build and buildslaves to each step."""
  for step in steplist:
    step.setBuild(build)
    step.setBuildSlave(buildslave)
    step.setStepStatus(build_status.addStepWithName(step.name))
    step.setDefaultWorkdir(os.path.join(basedir, 'build'))
    step.workdir = os.path.join(basedir, 'build')


def get_commands(steplist):
  """Extract shell commands from step."""
  commands = []
  for step in steplist:
    if hasattr(step, 'command'):
      cmdhash = {}
      renderables = []
      accumulateClassList(step.__class__, 'renderables', renderables)

      for renderable in renderables:
        setattr(step, renderable, step.build.render(getattr(step,
                renderable)))

      cmdhash['name'] = step.name
      cmdhash['command'] = step.command
      cmdhash['workdir'] = step.workdir
      if hasattr(step, 'env'):
        cmdhash['env'] = step.env
      else:
        cmdhash['env'] = {}
      if hasattr(step, 'timeout'):
        print "yay!~"
        cmdhash['timeout'] = step.timeout

      cmdhash['description'] = step.description
      cmdhash['descriptionDone'] = step.descriptionDone
      commands.append(cmdhash)
  return commands


class LogClass(chromium_utils.RunCommandFilter):
  """Collection of methods to log via annotator or logfile."""

  def __init__(self, outstream):
    self.outstream = outstream
    chromium_utils.RunCommandFilter.__init__(self)

  def log_to_file_internal(self, chunk):
    print >>self.outstream, chunk,

  # for use with Buildbot callback updates
  def log_to_file(self, data):
    if 'stdout' in data:
      self.log_to_file_internal(data['stdout'])
    if 'header' in data:
      self.log_to_file_internal(data['header'] + '\n')

    if 'elapsed' in data:
      print >>sys.stderr, '(took %.2fs)' % float(data['elapsed'])

  # for use with RunCommand's filter_obj
  def FilterLine(self, data):
    self.log_to_file_internal(data)
    return None

  def FilterDone(self, data):
    self.log_to_file_internal(data + '\n')
    return None


def main(args):
  if args.list_masters:
    masterpairs = get_masters()
    pp_masters(masterpairs)
    return 0

  if args.master_dir:
    config = read_config(args.master_dir, args.master_cfg)
  else:
    path = choose_master(args.mastername)
    if not path:
      return 2

    config = read_config(path, args.master_cfg)

  if not config:
    return 2

  mastername = config['BuildmasterConfig']['properties']['mastername']
  builders = dup_slaves(config['BuildmasterConfig']['builders'])

  if args.list_builders:
    pp_builders(builders, mastername)
    return 0

  my_builder = choose(builders, args.spec)

  if args.spec and 'hostname' in args.spec:
    slavename = args.spec['hostname']
  elif (args.spec and 'either' in args.spec) and (
      args.spec['either'] != my_builder['name']):
    slavename = args.spec['either']
  else:
    slavename = my_builder['slavename']

  if not my_builder:
    return 2

  my_factory = my_builder['factory']
  steplist = generate_steplist(my_factory)

  if args.list_steps:
    print
    print 'listing steps in %s/%s:' % (mastername, my_builder['name'])
    print
    for step in steplist:
      if hasattr(args, 'step_regex') and not args.step_regex.search(step.name):
        print '-', step.name, '[skipped]'
      elif hasattr(args, 'stepreject_regex') and (
          args.stepreject_regex.search(step.name)):
        print '-', step.name, '[skipped]'
      else:
        print '*', step.name
    return 0

  if not args.annotate:
    print >>sys.stderr, 'using %s builder \'%s\'' % (mastername,
        my_builder['name'])

  if args.build_properties:
    buildsetup = args.build_properties
  else:
    buildsetup = {}
    buildsetup['revision'] = '%d' % args.revision
    buildsetup['branch'] = 'src'

  build = base.Build([FakeRequest(buildsetup)])
  safename = buildbot.util.safeTranslate(my_builder['name'])
  if hasattr(args, 'builderpath'):
    basepath = args.builderpath
  else:
    basepath = safename
  basedir = os.path.join('..', '..', '..', 'slave', basepath)
  build.basedir = basedir
  builderstatus = builder.BuilderStatus('test')
  builderstatus.nextBuildNumber = 2
  builderstatus.basedir = basedir
  my_builder['builddir'] = safename
  my_builder['slavebuilddir'] = safename
  mybuilder = real_builder.Builder(my_builder, builderstatus)
  build.setBuilder(mybuilder)
  build_status = build_module.BuildStatus(builderstatus, 1)

  build_status.setProperty('blamelist', [], 'Build')
  build_status.setProperty('mastername', mastername, 'Build')
  build_status.setProperty('slavename', slavename, 'Build')
  build_status.setProperty('gtest_filter', [], 'Build')

  # if build_properties are set on the CLI, overwrite the defaults
  # set above when build.setupProperties is called
  buildprops = Properties()
  if args.build_properties:
    buildprops.update(args.build_properties, 'Botmaster')
  mybuilder.setBotmaster(FakeBotmaster(mastername, buildprops))

  mylogger = LogClass(args.log)

  buildslave = FakeSlave(safename, slavename)
  buildslave.addUpdateAction(mylogger.log_to_file)

  build.build_status = build_status

  build.setupSlaveBuilder(buildslave)

  build.setupProperties()

  if args.output_build_properties:
    print
    print 'build properties:'
    print propertiesToJSON(build.getProperties())

  if args.output_factory_properties:
    print
    print 'factory properties:'
    print propertiesToJSON(my_factory.properties)

  if args.output_build_properties or args.output_factory_properties:
    return 0

  process_steps(steplist, build, buildslave, build_status, basedir)

  commands = get_commands(steplist)

  run_status = ReturnStatus()

  start_time = time.clock()
  commands_executed = 0
  for command in commands:
    if hasattr(args, 'step_regex'):
      if not args.step_regex.search(command['name']):
        if not args.annotate:
          print >>sys.stderr, 'skipping step: ' + command['name']
        continue

    if hasattr(args, 'stepreject_regex'):
      if args.stepreject_regex.search(command['name']):
        if not args.annotate:
          print >>sys.stderr, 'skipping step: ' + command['name']
          continue

    if not args.annotate:
      print >>sys.stderr, 'running step: %s' % command['name']
    else:
      print '@@@BUILD_STEP %s@@@' % command['name']

    print >>args.log, '(in %s): %s' % (command['workdir'], shell_quote(
        command['command']))

    mydir = os.getcwd()
    myenv = os.environ
    os.chdir(command['workdir'])

    # python docs says this might cause leaks on FreeBSD/OSX
    for envar in command['env']:
      os.environ[envar] = command['env'][envar]

    ret = chromium_utils.RunCommand(command['command'],
                                    filter_obj=mylogger,
                                    print_cmd=False)
    os.chdir(mydir)
    os.environ = myenv
    commands_executed += 1
    if ret != 0:
      return 2

  end_time = time.clock()
  if not args.annotate:
    print >>sys.stderr, '%d commands completed (%0.2fs).' % (
        commands_executed, end_time - start_time)
  else:
    if commands_executed < 1:
      print '0 commands executed.'
  return run_status.code

if __name__ == '__main__':
  options, positional_args = get_args()
  if args_ok(options, positional_args):
    retcode = main(options)
  else:
    print
    print 'run with --help for usage info'
    retcode = 1
  if retcode == 0:
    if not (options.annotate or options.list_masters or options.list_builders
            or options.list_steps):
      print >>sys.stderr, 'build completed successfully'
  else:
    if options.annotate:
      print >>options.log, '@@@BUILD_FAILRE@@@'
    else:
      print >>sys.stderr, 'build error encountered: aborting build'
  sys.exit(retcode)
