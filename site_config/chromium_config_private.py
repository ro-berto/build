#!/usr/bin/python
# Copyright (c) 2006-2008 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Seeds a number of variables defined in chromium_config.py.

The recommended way is to fork this file and use a custom DEPS forked from
config/XXX/DEPS with the right configuration data."""


class Master(object):
  # Repository URLs used by the SVNPoller and 'gclient config'.
  server_url = 'http://src.chromium.org'
  git_server_url =  'http://src.chromium.org/git'
  repo_root = '/svn'

  # Directly fetches from anonymous webkit svn server.
  webkit_root_url = 'http://svn.webkit.org/repository/webkit'

  # Other non-redistributable repositories.
  repo_root_internal = None
  trunk_internal_url = None
  trunk_internal_url_src = None
  gears_url_internal = None
  o3d_url_internal = None
  nacl_trunk_url_internal = None
  nacl_url_internal = None

  # Actually for Chromium OS slaves.
  chromeos_url = git_server_url + '/chromiumos.git'
  chromeos_internal_url = None

  # Please change this accordingly.
  master_domain = 'example.com'
  permitted_domains = ('example.com',)

  # Your smtp server to enable mail notifications.
  smtp = 'smtp'

  class _Base(object):
    # If set to True, the master will do nasty stuff like closing the tree,
    # sending emails or other similar behaviors. Don't change this value unless
    # you modified the other settings extensively.
    is_production_host = False
    # Master address. You should probably copy this file in another svn repo
    # so you can override this value on both the slaves and the master.
    master_host = 'localhost'
    # Additional email addresses to send gatekeeper (automatic tree closage)
    # notifications. Unnecessary for experimental masters and try servers.
    tree_closing_notification_recipients = []
    # 'from:' field for emails sent from the server.
    from_address = 'nobody@example.com'
    # Code review site to upload results. You should setup your own Rietveld
    # instance with the code at
    # http://code.google.com/p/rietveld/source/browse/#svn/branches/chromium
    # and put a url looking like this:
    # 'http://codereview.chromium.org/%d/upload_build_result/%d'
    # You can host your own private rietveld instance on Django, see
    # http://code.google.com/p/google-app-engine-django and
    # http://code.google.com/appengine/articles/pure_django.html
    code_review_site = None

    # For the following values, they are used only if non-0. Do not set them
    # here, set them in the actual master configuration class.

    # Used for the waterfall URL and the waterfall's WebStatus object.
    master_port = 0
    # Which port slaves use to connect to the master.
    slave_port = 0
    # The alternate read-only page. Optional.
    master_port_alt = 0
    # HTTP port for try jobs.
    try_job_port = 0

  ## Chrome related

  class _ChromiumBase(_Base):
    # Tree status urls. You should fork the code from tools/chromium-status/ and
    # setup your own AppEngine instance (or use directly Djando to create a
    # local instance).
    # Defaulting urls that are used to POST data to 'localhost' so a local dev
    # server can be used for testing and to make sure nobody updates the tree
    # status by error!
    #
    # This url is used for HttpStatusPush:
    base_app_url = 'http://localhost:8080'
    # HTTP url that should return 0 or 1, depending if the tree is open or
    # closed. It is also used as POST to update the tree status.
    tree_status_url = base_app_url + '/status'
    # Used by LKGR to POST data.
    store_revisions_url = base_app_url + '/revisions'
    # Used by the try server to sync to the last known good revision:
    last_good_url = 'http://chromium-status.appspot.com/lkgr'

  class Chromium(_ChromiumBase):
    # Used by the waterfall display.
    project_name = 'Chromium'
    master_port = 9010
    slave_port = 9012
    master_port_alt = 9014

  class ChromiumFYI(_ChromiumBase):
    project_name = 'Chromium FYI'
    master_port = 9016
    slave_port = 9017
    master_port_alt = 9019

  class ChromiumMemory(_ChromiumBase):
    project_name = 'Chromium Meomry'
    master_port = 9014
    slave_port = 9019
    master_port_alt = 9047

  class TryServer(_ChromiumBase):
    project_name = 'Chromium Try Server'
    master_port = 9011
    slave_port = 9013
    master_port_alt = 9015
    try_job_port = 9018
    # The svn repository to poll to grab try patches. For chrome, we use a
    # separate repo to put all the diff files to be tried.
    svn_url = None

  class MyChromeFork(_Base):
    # Place your continuous build fork settings here.
    project_name = 'My Forked Chrome'
    master_port = 9010
    slave_port = 9011
    from_address = 'nobody@example.com'

  ## ChromeOS related

  class ChromeOS(_Base):
    project_name = 'ChromeOS'
    master_port = 9030
    slave_port = 9027
    master_port_alt = 9043
    base_app_url = 'http://localhost:8080'
    tree_status_url = base_app_url + '/status'
    store_revisions_url = base_app_url + '/revisions'
    last_good_url = 'http://chromiumos-status.appspot.com/lkgr'

  ## V8

  class V8(_Base):
    project_name = 'V8'
    master_host = 'localhost'
    master_port = 9030
    slave_port = 9031
    master_port_alt = 9043
    server_url = 'http://v8.googlecode.com'
    project_url = 'http://v8.googlecode.com'

  ## Native Client related

  class _NaClBase(_Base):
    base_app_url = 'http://localhost:8080'
    tree_status_url = base_app_url + '/status'
    store_revisions_url = base_app_url + '/revisions'
    last_good_url = 'http://nativeclient-status.appspot.com/lkgr'

  class NativeClient(_NaClBase):
    project_name = 'NativeClient'
    master_port = 9025
    slave_port = 9026
    master_port_alt = 9041

  class NativeClientToolchain(_NaClBase):
    project_name = 'NativeClientToolchain'
    master_port = 9025
    slave_port = 9026
    master_port_alt = 9041

  class NativeClientChrome(_NaClBase):
    project_name = 'NativeClientChrome'
    master_port = 9025
    slave_port = 9026
    master_port_alt = 9041

  class NativeClientSDK(_NaClBase):
    project_name = 'NativeClientSDK'
    master_port = 9022
    slave_port = 9048
    master_port_alt = 9049

  class NativeClientPorts(_NaClBase):
    project_name = 'NativeClientPorts'
    master_port = 9022
    slave_port = 9048
    master_port_alt = 9049

  class NativeClientTryServer(_Base):
    project_name = 'NativeClient-Try'
    master_port = 9020
    slave_port = 9021
    master_port_alt = 9022
    try_job_port = 9023
    svn_url = None

  ## Others

  class O3D(_Base):
    project_name = 'O3D'
    master_port = 9028
    slave_port = 9029
    master_port_alt = 9042
    base_app_url = 'http://localhost:8080'
    tree_status_url = base_app_url + '/status'
    store_revisions_url = base_app_url + '/revisions'
    last_good_url = 'http://o3d-status.appspot.com/lkgr'

  # Used for testing on a local machine
  class Experimental(Chromium):
    project_name = 'Chromium Experimental'
    master_host = 'localhost'
    master_port = 9010
    slave_port = 9011
    master_port_alt = 9012


class Installer(object):
  # A file containing information about the last release.
  last_release_info = "."


class Archive(object):
  archive_host = 'localhost'
  # Skip any filenames (exes, symbols, etc.) starting with these strings
  # entirely, typically because they're not built for this distribution.
  exes_to_skip_entirely = []
  # Web server base path.
  www_dir_base = "\\\\" + archive_host + "\\www\\"


class IRC(object):
  bot_admins = ['root']
  nickname = 'change_me_buildbot'

class Distributed(object):
  """Not much to describe."""
