# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import ast
import os

from buildbot.schedulers.basic import SingleBranchScheduler
from buildbot.schedulers.timed import Nightly
from buildbot.status.mail import MailNotifier
from buildbot import util

from config_bootstrap import Master

from common import chromium_utils

from master import gitiles_poller
from master import master_utils
from master import slaves_list
from master.factory import annotator_factory


def PopulateBuildmasterConfig(BuildmasterConfig, builders_path,
                              active_master_cls):
  """Read builders_path and populate a build master config dict."""
  builders = chromium_utils.ReadBuildersFile(builders_path)
  _Populate(BuildmasterConfig, builders, active_master_cls)


def _Populate(BuildmasterConfig, builders, active_master_cls):
  m_annotator = annotator_factory.AnnotatorFactory(active_master_cls)

  c = BuildmasterConfig
  c['logCompressionLimit'] = False
  c['projectName'] = active_master_cls.project_name
  c['projectURL'] = Master.project_url
  c['buildbotURL'] = active_master_cls.buildbot_url

  # This sets c['db_url'] to the database connect string in found in
  # the .dbconfig in the master directory, if it exists. If this is
  # a production host, it must exist.
  chromium_utils.DatabaseSetup(
      c,
      require_dbconfig=active_master_cls.is_production_host)

  c['builders'] = _ComputeBuilders(builders, m_annotator)

  c['schedulers'] = _ComputeSchedulers(builders)

  c['change_source'], tag_comparator = _ComputeChangeSourceAndTagComparator(
      builders)

  # The 'slaves' list defines the set of allowable buildslaves. List all the
  # slaves registered to a builder. Remove dupes.
  c['slaves'] = master_utils.AutoSetupSlaves(
      c['builders'],
      Master.GetBotPassword(),
      missing_recipients=['buildbot@chromium-build-health.appspotmail.com'])

  # This does some sanity checks on the configuration.
  slaves = slaves_list.BaseSlavesList(
      chromium_utils.GetSlavesFromBuilders(builders),
      builders['master_classname'])
  master_utils.VerifySetup(c, slaves)

  # Adds common status and tools to this master.
  # TODO: Look at the logic in this routine to see if any of the logic
  # in this routine can be moved there to simplify things.
  master_utils.AutoSetupMaster(c, active_master_cls,
      public_html=os.path.join(chromium_utils.BUILD_DIR,
                               'masters', 'master.chromium', 'public_html'),
      templates=builders['templates'],
      tagComparator=tag_comparator,
      enable_http_status_push=active_master_cls.is_production_host)

  # TODO: AutoSetupMaster's settings for the following are too low to be
  # useful for most projects. We should fix that.
  c['buildHorizon'] = 3000
  c['logHorizon'] = 3000
  # Must be at least 2x the number of slaves.
  c['eventHorizon'] = 200


def _ComputeBuilders(builders, m_annotator):
  actual_builders = []
  for builder_name, builder_data in builders['builders'].items():
    scheduler_name = builder_data['scheduler']

    # We will automatically merge all build requests for any
    # builder that can be scheduled; this is normally the behavior
    # we want for repo-triggered builders and cron-triggered builders.
    merge_requests = bool(scheduler_name)

    slavebuilddir = builder_data.get('slavebuilddir',
                                     util.safeTranslate(builder_name))
    factory = m_annotator.BaseFactory(
        recipe=builder_data['recipe'],
        factory_properties=builder_data.get('properties')
    )
    actual_builders.append({
        'auto_reboot': builder_data.get('auto_reboot', True),
        'mergeRequests': merge_requests,
        'name': builder_name,
        'factory': factory,
        'slavebuilddir': slavebuilddir,
        'slavenames': chromium_utils.GetSlaveNamesForBuilder(builders,
                                                             builder_name),
        'category': builders.get('category'),
    })

  return actual_builders


def _ComputeSchedulers(builders):
  scheduler_to_builders = {}
  for builder_name, builder_data in builders['builders'].items():
    scheduler_name = builder_data['scheduler']
    if scheduler_name:
      scheduler_to_builders.setdefault(scheduler_name, []).append(builder_name)

  schedulers = []
  for scheduler_name, scheduler_values in builders['schedulers'].items():
    scheduler_type = scheduler_values['type']
    builder_names = scheduler_to_builders[scheduler_name]

    if scheduler_type == 'git_poller':
      schedulers.append(SingleBranchScheduler(
          name=scheduler_name,
          branch='master',
          treeStableTimer=60,
          builderNames=builder_names))

    elif scheduler_type == 'cron':
      schedulers.append(Nightly(
          name=scheduler_name,
          branch='master',
          minute=scheduler_values['minute'],
          hour=scheduler_values['hour'],
          builderNames=builder_names))

    else:
      raise ValueError('unsupported scheduler type "%s"' % scheduler_type)

  return schedulers


def _ComputeChangeSourceAndTagComparator(builders):
  change_source = []
  tag_comparator = None

  for url in sorted(set(v['git_repo_url'] for
                        v in builders['schedulers'].values()
                        if v['type'] == 'git_poller')):
    change_source.append(gitiles_poller.GitilesPoller(url))

  # We have to set the tag_comparator to something, but if we have multiple
  # repos, the tag_comparator will not work properly (it's meaningless).
  # It's not clear if there's a good answer to this.
  if change_source:
    tag_comparator = change_source[0].comparator

  return change_source, tag_comparator
