# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import ast
import os

from buildbot.schedulers.basic import SingleBranchScheduler
from buildbot.status.mail import MailNotifier

from config_bootstrap import Master

from common import chromium_utils

from master import gitiles_poller
from master import master_utils
from master import slaves_list
from master.factory import annotator_factory


def PopulateBuildmasterConfig(BuildmasterConfig, builders_path,
                              master_cls=None):
  """Read builders.py and populate a build master config dict."""
  master_cls = master_cls or Master
  builders = _ReadBuilders(builders_path)
  _Populate(BuildmasterConfig, builders, master_cls)


def GetSlavesFromBuilders(builders_path):
  """Read builders.py in basedir and return a list of slaves."""
  builders = _ReadBuilders(builders_path)
  return _GetSlaves(builders)


def _ReadBuilders(builders_path):
  with open(builders_path) as fp:
    builders = ast.literal_eval(fp.read())

  # Set some additional derived fields that are derived from the
  # file's location in the filesystem.
  basedir = os.path.dirname(os.path.abspath(builders_path))
  master_dirname = os.path.basename(basedir)
  master_name_comps = master_dirname.split('.')[1:]
  buildbot_path =  '.'.join(master_name_comps)
  master_classname =  ''.join(c[0].upper() + c[1:] for c in master_name_comps)

  # TODO: These probably shouldn't be completely hard-coded like this.
  builders['master_dirname'] = master_dirname
  builders['master_classname'] = master_classname
  builders['buildbot_url'] = 'https://build.chromium.org/p/%s' % buildbot_path

  return builders


def _Populate(BuildmasterConfig, builders, master_cls):
  classname = builders['master_classname']
  base_class = getattr(master_cls, builders['master_base_class'])
  active_master_cls = type(classname, (base_class,), {
      'buildbot_url': builders['buildbot_url'],
      'project_name': builders['master_classname'],
      'master_port': int(builders['master_port']),
      'master_port_alt': int(builders['master_port_alt']),
      'slave_port': int(builders['slave_port']),
      })

  # TODO: Modify this and the factory call, below, so that we can pass the
  # path to the builders.py file through the annotator to the slave so that
  # the slave can get the recipe name and the factory properties dynamically
  # without needing the master to re-read things.
  m_annotator = annotator_factory.AnnotatorFactory()

  c = BuildmasterConfig
  c['logCompressionLimit'] = False
  c['projectName'] = active_master_cls.project_name
  c['projectURL'] = master_cls.project_url
  c['buildbotURL'] = active_master_cls.buildbot_url

  # This sets c['db_url'] to the database connect string in found in
  # the .dbconfig in the master directory, if it exists. If this is
  # a production host, it must exist.
  chromium_utils.DatabaseSetup(
      c,
      require_dbconfig=active_master_cls.is_production_host)

  change_source = gitiles_poller.GitilesPoller(builders['git_repo_url'])
  c['change_source'] = [change_source]

  c['builders'] = []
  for builder_name, builder_data in builders['builders'].items():
    c['builders'].append({
        'name': builder_name,
        'factory': m_annotator.BaseFactory(builder_data['recipe']),
        'slavebuilddir': builder_data['slavebuilddir'],
        'slavenames': _GetSlavesForBuilder(builders, builder_name),
    })

  c['schedulers'] = [
      SingleBranchScheduler(name='source',
                            branch='master',
                            treeStableTimer=60,
                            builderNames=[b['name'] for b in c['builders']])
  ]

  # The 'slaves' list defines the set of allowable buildslaves. List all the
  # slaves registered to a builder. Remove dupes.
  c['slaves'] = master_utils.AutoSetupSlaves(
      c['builders'],
      master_cls.GetBotPassword(),
      missing_recipients=['buildbot@chromium-build-health.appspotmail.com'])

  # This does some sanity checks on the configuration.
  slaves = slaves_list.BaseSlavesList(_GetSlaves(builders),
                                      builders['master_classname'])
  master_utils.VerifySetup(c, slaves)

  # Adds common status and tools to this master.
  # TODO: Look at the logic in this routine to see if any of the logic
  # in this routine can be moved there to simplify things.
  master_utils.AutoSetupMaster(c, active_master_cls,
      public_html='../master.chromium/public_html',
      templates=builders['templates'],
      tagComparator=change_source.comparator,
      enable_http_status_push=active_master_cls.is_production_host)

  # TODO: AutoSetupMaster's settings for the following are too low to be
  # useful for most projets. We should fix that.
  c['buildHorizon'] = 3000
  c['logHorizon'] = 3000
  # Must be at least 2x the number of slaves.
  c['eventHorizon'] = 200


def _GetSlaves(builders):
  builders_in_pool = {}

  # builders.py contains a list of builders -> slave_pools
  # and a list of slave_pools -> slaves.
  # We require that each slave is in a single pool, but each slave
  # may have multiple builders, so we need to build up the list of
  # builders each slave pool supports.
  for builder_name, builder_vals in builders['builders'].items():
    pool_names = builder_vals['slave_pools']
    for pool_name in pool_names:
     if pool_name not in builders_in_pool:
       builders_in_pool[pool_name] = set()
     pool_data = builders['slave_pools'][pool_name]
     for slave in pool_data['slaves']:
       builders_in_pool[pool_name].add(builder_name)

  # Now we can generate the list of slaves using the above lookup table.

  slaves = []
  for pool_name, pool_data in builders['slave_pools'].items():
    slave_data = pool_data['slave_data']
    builder_names = sorted(builders_in_pool[pool_name])
    for slave in pool_data['slaves']:
      slaves.append({
          'hostname': slave,
          'builder_name': builder_names,
          'os': slave_data['os'],
          'version': slave_data['version'],
          'bits': slave_data['bits'],
      })

  return slaves


def _GetSlavesForBuilder(builders, builder_name):
  slaves = []
  pool_names = builders['builders'][builder_name]['slave_pools']
  for pool_name in pool_names:
    slaves.extend(builders['slave_pools'][pool_name]['slaves'])
  return slaves
