# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import ast
import os
import re

from buildbot.changes.filter import ChangeFilter
from buildbot.process.properties import WithProperties
from buildbot.schedulers.basic import AnyBranchScheduler
from buildbot.schedulers.basic import SingleBranchScheduler
from buildbot.schedulers.timed import Nightly
from buildbot import util

from config_bootstrap import Master

from common import chromium_utils

from master import gitiles_poller
from master import master_utils
from master import repo_poller
from master import slaves_list
from master.factory import annotator_factory
from master.factory import remote_run_factory


def PopulateBuildmasterConfig(BuildmasterConfig, builders_path,
                              active_master_cls):
  """Read builders_path and populate a build master config dict."""
  builders = chromium_utils.ReadBuildersFile(builders_path)
  _Populate(BuildmasterConfig, builders, active_master_cls)


_revision_getter = master_utils.ConditionalProperty(
    lambda build: build.getProperty('revision'),
    WithProperties('%(revision)s'),
    'master')


def _Populate(BuildmasterConfig, builders, active_master_cls):
  m_annotator = annotator_factory.AnnotatorFactory(active_master_cls)

  c = BuildmasterConfig
  c['logCompressionLimit'] = builders.get('logCompressionLimit', False)
  c['projectName'] = active_master_cls.project_name
  c['projectURL'] = Master.project_url
  c['buildbotURL'] = active_master_cls.buildbot_url

  # This sets c['db_url'] to the database connect string in found in
  # the .dbconfig in the master directory, if it exists.
  chromium_utils.DatabaseSetup(c)

  c['builders'] = _ComputeBuilders(builders, m_annotator, active_master_cls)

  c['schedulers'] = _ComputeSchedulers(builders)

  c['change_source'], tag_comparator = _ComputeChangeSourceAndTagComparator(
      builders)

  # The 'slaves' list defines the set of allowable buildslaves. List all the
  # slaves registered to a builder. Remove dupes.
  c['slaves'] = master_utils.AutoSetupSlaves(
      c['builders'],
      Master.GetBotPassword())

  # This does some sanity checks on the configuration.
  slaves = slaves_list.BaseSlavesList(
      chromium_utils.GetBotsFromBuilders(builders),
      builders['master_classname'])
  master_utils.VerifySetup(c, slaves)

  default_public_html = os.path.join(chromium_utils.BUILD_DIR,
                                     'masters', 'master.chromium',
                                     'public_html')
  public_html = builders.get('public_html', default_public_html)

  mail_notifier = builders.get('mail_notifier')

  order_console_by_time = builders.get('order_console_by_time')

  # Adds common status and tools to this master.
  # TODO: Look at the logic in this routine to see if any of the logic
  # in this routine can be moved there to simplify things.
  master_utils.AutoSetupMaster(c, active_master_cls,
      mail_notifier=mail_notifier,
      public_html=public_html,
      templates=builders['templates'],
      order_console_by_time=order_console_by_time,
      tagComparator=tag_comparator,
      enable_http_status_push=active_master_cls.is_production_host)

  # TODO: AutoSetupMaster's settings for the following are too low to be
  # useful for most projects. We should fix that.
  c['buildHorizon'] = 3000
  c['logHorizon'] = 3000
  # Must be at least 2x the number of slaves.
  c['eventHorizon'] = 200


def _ComputeBuilders(builders, m_annotator, active_master_cls):
  actual_builders = []

  def cmp_fn(a, b):
    a_cat = builders['builders'][a].get('category')
    b_cat = builders['builders'][b].get('category')
    if a_cat != b_cat:
      return 1 if a_cat > b_cat else -1
    if a != b:
      return 1 if a > b else -1
    return 0

  for builder_name in sorted(builders['builders'], cmp=cmp_fn):
    builder_data = builders['builders'][builder_name]
    has_schedulers = bool(
        builder_data.get('scheduler', builder_data.get('schedulers')))

    # We will automatically merge all build requests for any
    # builder that can be scheduled; this is normally the behavior
    # we want for repo-triggered builders and cron-triggered builders.
    # You can override this behavior by setting the mergeRequests field though.
    merge_requests = builder_data.get('mergeRequests', has_schedulers)

    botbuilddir = builder_data.get('botbuilddir',
                                   util.safeTranslate(builder_name))

    props = {}
    props.update(builders.get('default_properties', {}).copy())
    props.update(builder_data.get('properties', {}))

    # Only pass timeout if 'no_output_timeout_s' is specified, to avoid
    # overwriting the default value in BaseFactory.
    kwargs = {}
    if builder_data.get('no_output_timeout_s'):
      kwargs['timeout'] = builder_data['no_output_timeout_s']

    if builder_data.get('use_remote_run'):
      factory = remote_run_factory.RemoteRunFactory(
          active_master=active_master_cls,
          repository=builder_data.get('remote_run_repository'),
          recipe=builder_data['recipe'],
          revision=(
              _revision_getter if builder_data.get('remote_run_sync_revision')
                               else None),
          max_time=builder_data.get('builder_timeout_s'),
          factory_properties=props,
          **kwargs
      )
    else:
      factory = m_annotator.BaseFactory(
          recipe=builder_data['recipe'],
          max_time=builder_data.get('builder_timeout_s'),
          factory_properties=props,
          **kwargs
      )
    actual_builders.append({
        'auto_reboot': builder_data.get('auto_reboot', True),
        'mergeRequests': merge_requests,
        'name': builder_name,
        'factory': factory,
        'slavebuilddir': botbuilddir,
        'slavenames': chromium_utils.GetBotNamesForBuilder(builders,
                                                           builder_name),
        'category': builder_data.get('category'),
        'trybot': builder_data.get('trybot'),
    })

  return actual_builders


def _ComputeSchedulers(builders):
  scheduler_to_builders = {}
  for builder_name, builder_data in builders['builders'].items():
    scheduler_names = builder_data.get('schedulers', [])
    if 'scheduler' in builder_data:
      scheduler_names.append(builder_data['scheduler'])
    for scheduler_name in scheduler_names:
      if scheduler_name:
        if scheduler_name not in builders['schedulers']:
          raise ValueError('unknown scheduler "%s"' % scheduler_name)
        scheduler_to_builders.setdefault(
            scheduler_name, []).append(builder_name)

  schedulers = []
  for scheduler_name, scheduler_values in builders['schedulers'].items():
    scheduler_type = scheduler_values['type']
    builder_names = scheduler_to_builders[scheduler_name]

    if scheduler_type == 'git_poller':
      # git_poller polls group changes, so we match on our specific repository
      # to ensure that we only pick up changes from our poller.
      schedulers.append(SingleBranchScheduler(
          name=scheduler_name,
          change_filter=ChangeFilter(
              repository=scheduler_values['git_repo_url'],
              branch=scheduler_values.get('branch', 'master'),
          ),
          treeStableTimer=scheduler_values.get('treeStableTimer', 60),
          builderNames=builder_names))

    elif scheduler_type == 'git_poller_any':
      # When polling multiple branches, we use separate change sources with
      # a category set to the scheduler name.
      schedulers.append(AnyBranchScheduler(
          name=scheduler_name,
          change_filter=ChangeFilter(
              repository=scheduler_values['git_repo_url'],
              category=scheduler_name,
          ),
          treeStableTimer=scheduler_values.get('treeStableTimer', 60),
          builderNames=builder_names))

    elif scheduler_type == 'repo_poller':
      # repo_poller pollers punt changes that use the scheduler name as their
      # category (see _ComputeChangeSourceAndTagComparator). Matching on this
      # ensures that we only match changes from our poller.
      schedulers.append(SingleBranchScheduler(
          name=scheduler_name,
          change_filter=ChangeFilter(
              category=str(scheduler_name),
          ),
          treeStableTimer=scheduler_values.get('treeStableTimer', 60),
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

  git_urls_to_branches = {}
  for scheduler_config in builders['schedulers'].values():
    if scheduler_config['type'] != 'git_poller':
      continue

    url = scheduler_config['git_repo_url']
    branch = scheduler_config.get('branch', 'master')
    git_urls_to_branches.setdefault(url, set()).add(branch)

  for url, branches in git_urls_to_branches.iteritems():
    change_source.append(
        gitiles_poller.GitilesPoller(url, branches=list(branches)))

  # Each AnyBranchScheduler gets a separate poller.
  for scheduler_name, scheduler_config in builders['schedulers'].iteritems():
    if scheduler_config['type'] != 'git_poller_any':
      continue

    branches = scheduler_config.get('branch', 'master')
    if isinstance(branches, list):
      # Treat lists as lists of regular expressions.
      branches = [re.compile(r) for r in branches]
    change_source.append(
        gitiles_poller.GitilesPoller(
            scheduler_config['git_repo_url'],
            branches=list(branches),
            category=scheduler_name))

  for scheduler_name, scheduler_config in builders['schedulers'].iteritems():
    if scheduler_config['type'] != 'repo_poller':
      continue

    rev_link_template = scheduler_config.get('rev_link_template')
    branch = scheduler_config.get('branch')
    branches = [branch] if branch is not None else None
    change_source.append(repo_poller.RepoPoller(
        repo_url=scheduler_config['repo_url'],
        manifest='manifest',
        category=str(scheduler_name),
        repo_branches=branches,
        pollInterval=300,
        revlinktmpl=rev_link_template))

  # We have to set the tag_comparator to something, but if we have multiple
  # repos, the tag_comparator will not work properly (it's meaningless).
  # It's not clear if there's a good answer to this.
  if change_source:
    tag_comparator = change_source[0].comparator

  return change_source, tag_comparator
