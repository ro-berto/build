#!/usr/bin/python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class used by Dart buildbot masters
"""

import random

from buildbot.changes import gitpoller
from buildbot.process.buildstep import RemoteShellCommand
from buildbot.status.mail import MailNotifier

from master.factory.dart.channels import CHANNELS, CHANNELS_BY_NAME
from master import master_utils

import config

dart_git_server = 'https://dart.googlesource.com'
github_mirror = 'https://chromium.googlesource.com/external/github.com'

# We set these paths relative to the dart root, the scripts need to
# fix these to be absolute if they don't run from there.
linux_env = {}
linux_clang_env = {'CC': 'third_party/clang/linux/bin/clang',
                   'CXX': 'third_party/clang/linux/bin/clang++'}
clang_asan = 'third_party/clang/linux/bin/clang++ -fsanitize=address -fPIC'
linux_asan_env_64 = {'CXX': clang_asan,
                     'ASAN_OPTIONS':
                     'handle_segv=0:detect_stack_use_after_return=1'}
linux_asan_env_32 = {'CXX': clang_asan,
                     'ASAN_OPTIONS':
                     'handle_segv=0:detect_stack_use_after_return=0'}

windows_env = {'LOGONSERVER': '\\\\AD1'}

class DartUtils(object):
  mac_options = ['--compiler=goma', 'dartium_builder']
  linux_options = ['--compiler=goma', 'dartium_builder']
  win_options = ['dartium_builder']


  def __init__(self, active_master):
    self._active_master = active_master

  @staticmethod
  def monkey_patch_remoteshell():
    # Hack to increase timeout for steps, dart2js debug checked mode takes more
    # than 8 hours.
    RemoteShellCommand.__init__.im_func.func_defaults = (None,
                                                         1,
                                                         1,
                                                         1200,
                                                         48*60*60, {},
                                                         'slave-config',
                                                         True)

  @staticmethod
  def get_git_poller(repo, project, name, revlink, branch=None, master=None,
                     interval=None, hostid=None):
    changesource_project = '%s-%s' % (name, branch) if branch else name

    hostid = hostid or 'github'
    branch = branch or 'master'
    master = master or 'main'
    interval = interval or 40
    workdir = '/tmp/git_workdir_%s_%s_%s_%s' % (
        hostid, project, changesource_project, master)
    return gitpoller.GitPoller(repourl=repo,
                               pollinterval=interval,
                               project=changesource_project,
                               branch=branch,
                               workdir=workdir,
                               revlinktmpl=revlink)

  @staticmethod
  def get_github_gclient_repo(project, name, branch=None):
    repo = DartUtils.get_github_repo(project, name)
    if branch:
      repo = '%s@refs/remotes/origin/%s' % (repo, branch)
    return repo

  @staticmethod
  def get_github_repo(project, name):
    return 'https://github.com/%s/%s.git' % (project, name)

  @staticmethod
  def get_github_poller(project, name, branch=None, master=None, interval=None):
    repository = 'https://github.com/%s/%s.git' % (project, name)
    revlink = ('https://github.com/' + project + '/' + name + '/commit/%s')
    return DartUtils.get_git_poller(
        repository, project, name, revlink, branch, master, interval=interval,
        hostid='github')

  @staticmethod
  def get_github_mirror_poller(project, name, branch=None, master=None):
    repository = '%s/%s/%s.git' % (github_mirror, project, name)
    revlink = ('https://github.com/' + project + '/' + name + '/commit/%s')
    return DartUtils.get_git_poller(
        repository, project, name, revlink, branch, master,
        hostid='github_mirror')

  @staticmethod
  def get_dart_poller(name, branch=None, master=None):
    repository = '%s/%s.git' % (dart_git_server, name)
    revlink = ('https://github.com/dart-lang/' + name + '/commit/%s')
    return DartUtils.get_git_poller(
        repository, 'dart-lang', name, revlink, branch, master,
        hostid='dart_git_server')

  @staticmethod
  def prioritize_builders(buildmaster, builders):
    def get_priority(name):
      for channel in CHANNELS:
        if name.endswith(channel.builder_postfix):
          return channel.priority
      # Default to a low priority
      return 10
    # Python's sort is stable, which means that builders with the same priority
    # will be in random order.
    random.shuffle(builders)
    builders.sort(key=lambda b: get_priority(b.name))
    return builders

  def get_web_statuses(self, order_console_by_time=True,
                       extra_templates=None):
    public_html = '../master.chromium/public_html'
    templates = ['../master.client.dart/templates',
                 '../master.chromium/templates']
    if extra_templates:
      templates = extra_templates + templates
    master_port = self._active_master.master_port
    master_port_alt = self._active_master.master_port_alt
    kwargs = {
      'public_html' : public_html,
      'templates' : templates,
      'order_console_by_time' : order_console_by_time,
    }

    statuses = []
    statuses.append(master_utils.CreateWebStatus(master_port,
                                                 allowForce=True,
                                                 **kwargs))
    statuses.append(
        master_utils.CreateWebStatus(master_port_alt, allowForce=False,
                                     **kwargs))
    return statuses

  @staticmethod
  def get_builders_from_variants(variants,
                                 slaves,
                                 slave_locks,
                                 auto_reboot=False):
    builders = []
    for v in variants:
      builder = {
         'name': v['name'],
         'builddir': v.get('builddir', v['name']),
         'factory': v['factory_builder'],
         'slavenames': slaves.GetSlavesName(builder=v['name']),
         'category': v['category'],
         'locks': slave_locks,
         'auto_reboot': v.get('auto_reboot', auto_reboot)}
      if 'merge_requests' in v:
        builder['mergeRequests'] = v['merge_requests']
      builders.append(builder)
    return builders

  @staticmethod
  def get_builder_names(variants):
    return [variant['name'] for variant in variants]

  @staticmethod
  def get_slaves(builders):
    # The 'slaves' list defines the set of allowable buildslaves. List all the
    # slaves registered to a builder. Remove dupes.
    return master_utils.AutoSetupSlaves(builders,
                                        config.Master.GetBotPassword())

  def get_mail_notifier_statuses(self, mail_notifiers):
    statuses = []
    for mail_notifier in mail_notifiers:
      notifying_builders = mail_notifier['builders']
      extra_recipients = mail_notifier['extraRecipients']
      send_to_interested_useres = mail_notifier.get('sendToInterestedUsers',
                                                    False)
      subject = mail_notifier.get('subject')
      if subject:
        statuses.append(
            MailNotifier(fromaddr=self._active_master.from_address,
                         mode='problem',
                         subject=subject,
                         sendToInterestedUsers=send_to_interested_useres,
                         extraRecipients=extra_recipients,
                         lookup=master_utils.UsersAreEmails(),
                         builders=notifying_builders))
      else:
        statuses.append(
            MailNotifier(fromaddr=self._active_master.from_address,
                         mode='problem',
                         sendToInterestedUsers=send_to_interested_useres,
                         extraRecipients=extra_recipients,
                         lookup=master_utils.UsersAreEmails(),
                         builders=notifying_builders))
    return statuses
