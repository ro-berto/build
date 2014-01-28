# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Provides templates and base classes for all the public buildbot masters.

Masters inherit from this file in their own master_site_config.py files.
Slaves use this file to get info about the master they are connecting to.
"""

import socket


class classproperty(object):
  """A decorator that allows is_production_host to only to be defined once."""
  def __init__(self, getter):
    self.getter = getter
  def __get__(self, instance, owner):
    return self.getter(owner)


class Master(object):
  """Master base template.

  Contains stubs for variables that all masters must define."""
  # Master address. You should probably copy this file in another svn repo
  # so you can override this value on both the slaves and the master.
  master_host = 'localhost'
  # Only report that we are running on a master if the master_host (even when
  # master_host is overridden by a subclass) is the same as the current host.
  @classproperty
  def is_production_host(cls):
    return socket.getfqdn() == cls.master_host
  # 'from:' field for emails sent from the server.
  from_address = 'nobody@example.com'
  # Additional email addresses to send gatekeeper (automatic tree closage)
  # notifications. Unnecessary for experimental masters and try servers.
  tree_closing_notification_recipients = []
  # For the following values, they are used only if non-0. Do not set them
  # here, set them in the actual master configuration class:
  # Used for the waterfall URL and the waterfall's WebStatus object.
  master_port = 0
  # Which port slaves use to connect to the master.
  slave_port = 0
  # The alternate read-only page. Optional.
  master_port_alt = 0


class PublicBase(Master):
  # Repository URLs used by the SVNPoller and 'gclient config'.
  server_url = 'http://src.chromium.org'
  repo_root = '/svn'
  git_server_url = 'https://chromium.googlesource.com'

  # External repos.
  googlecode_url = 'http://%s.googlecode.com/svn'
  sourceforge_url = 'https://svn.code.sf.net/p/%(repo)s/code'
  googlecode_revlinktmpl = 'https://code.google.com/p/%s/source/browse?r=%s'

  # Directly fetches from anonymous Blink svn server.
  webkit_root_url = 'http://src.chromium.org/blink'
  nacl_trunk_url = 'http://src.chromium.org/native_client/trunk'

  llvm_url = 'http://llvm.org/svn/llvm-project'

  # Perf Dashboard upload URL.
  dashboard_upload_url = 'https://chromeperf.appspot.com'

  # Actually for Chromium OS slaves.
  chromeos_url = git_server_url + '/chromiumos.git'

  # Default domain for emails to come from and
  # domains to which emails can be sent.
  master_domain = 'example.com'
  permitted_domains = ('example.com',)

  # Your smtp server to enable mail notifications.
  smtp = 'smtp'

  trunk_url = server_url + repo_root + '/trunk'

  webkit_trunk_url = webkit_root_url + '/trunk'

  trunk_url_src = trunk_url + '/src'
  trunk_url_tools = trunk_url + '/tools'
  nacl_url = nacl_trunk_url + '/src/native_client'
  nacl_sdk_root_url = 'https://nativeclient-sdk.googlecode.com/svn'
  nacl_ports_trunk_url = 'https://naclports.googlecode.com/svn/trunk'
  nacl_ports_url = nacl_ports_trunk_url + '/src'
  gears_url = 'http://gears.googlecode.com/svn/trunk'
  gyp_trunk_url = 'http://gyp.googlecode.com/svn/trunk'
  branch_url = server_url + repo_root + '/branches'
  merge_branch_url = branch_url + '/chrome_webkit_merge_branch'
  merge_branch_url_src = merge_branch_url + '/src'

  v8_url = 'http://v8.googlecode.com/svn'
  v8_branch_url = (v8_url + '/branches')
  v8_bleeding_edge = v8_branch_url + '/bleeding_edge'
  v8_trunk = v8_url + '/trunk'
  es5conform_root_url =  "https://es5conform.svn.codeplex.com/svn/"
  es5conform_revision = 62998

  dart_url = googlecode_url % 'dart'
  dart_bleeding = dart_url + '/branches/bleeding_edge'
  dart_trunk = dart_url + '/trunk'

  oilpan_url = webkit_root_url + '/branches/oilpan'

  skia_url = 'http://skia.googlecode.com/svn/'

  syzygy_url = 'http://sawbuck.googlecode.com/svn/'

  webrtc_url = 'http://webrtc.googlecode.com/svn'
  libyuv_url = 'http://libyuv.googlecode.com/svn'

  # Default target platform if none was given to the factory.
  default_platform = 'win32'

  # Used by the waterfall display.
  project_url = 'http://www.chromium.org'

  # Base URL for perf test results.
  perf_base_url = 'http://build.chromium.org/f/chromium/perf'

  # Suffix for perf URL.
  perf_report_url_suffix = 'report.html?history=150'

  # Directory in which to save perf-test output data files.
  perf_output_dir = '~/www/perf'

  # URL pointing to builds and test results.
  archive_url = 'http://build.chromium.org/buildbot'

  # The test results server to upload our test results.
  test_results_server = 'test-results.appspot.com'

  # File in which to save a list of graph names.
  perf_graph_list = 'graphs.dat'

  # Magic step return code inidicating "warning(s)" rather than "error".
  retcode_warnings = 88
  # Fake urls to make various factories happy.
  swarm_server_internal_url = 'http://fake.swarm.url.server.com'
  swarm_server_dev_internal_url = 'http://fake.swarm.dev.url.server.com'
  swarm_hashtable_server_internal = 'http://fake.swarm.hashtable.server.com'
  swarm_hashtable_server_dev_internal = 'http://fake.swarm.hashtable.server.com'
  trunk_internal_url = None
  trunk_internal_url_src = None
  slave_internal_url = None
  git_internal_server_url = None
  syzygy_internal_url = None
  webrtc_internal_url = None
  webrtc_limited_url = None
  v8_internal_url = None


class Master1(PublicBase):
  """Chromium master."""
  master_host = 'master1.golo.chromium.org'
  from_address = 'buildbot@chromium.org'
  tree_closing_notification_recipients = [
      'chromium-build-failure@chromium-gatekeeper-sentry.appspotmail.com']
  base_app_url = 'https://chromium-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = base_app_url + '/lkgr'
  last_good_blink_url = 'http://blink-status.appspot.com/lkgr'


class Master2(PublicBase):
  """Chromeos master."""
  master_host = 'master2.golo.chromium.org'
  tree_closing_notification_recipients = [
      'chromeos-build-failures@google.com']
  from_address = 'buildbot@chromium.org'


class Master3(PublicBase):
  """Client master."""
  master_host = 'master3.golo.chromium.org'
  tree_closing_notification_recipients = []
  from_address = 'buildbot@chromium.org'


class Master4(PublicBase):
  """Try server master."""
  master_host = 'master4.golo.chromium.org'
  tree_closing_notification_recipients = []
  from_address = 'tryserver@chromium.org'
  code_review_site = 'https://codereview.chromium.org'


class ChromiumOSBase(Master2):
  """Base class for ChromiumOS masters"""
  base_app_url = 'https://chromiumos-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = base_app_url + '/lkgr'


class NaClBase(Master3):
  """Base class for Native Client masters."""
  tree_closing_notification_recipients = ['bradnelson@chromium.org']
  base_app_url = 'https://nativeclient-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = base_app_url + '/lkgr'
  perf_base_url = 'http://build.chromium.org/f/client/perf'
