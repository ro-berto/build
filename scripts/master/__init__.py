#!/usr/bin/python2.4
# Copyright (c) 2006-2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Reload all python files in the directory."""

# These don't depend on anything except the standard python libraries.
# bot_data.py is manually loaded by irc_contact.py and not meant to be
# imported.
from master import build_sheriffs
from master import copytree
reload(build_sheriffs)
reload(copytree)


# These depend only on buildbot.
from master import builders_pools
from master import chromium_step
from master import json_file
from master import optional_arguments
from master import try_job_stamp
from master import try_job_status_update
from master import try_mail_notifier
reload(builders_pools)
reload(chromium_step)
reload(json_file)
reload(optional_arguments)
reload(try_job_stamp)
reload(try_job_status_update)
reload(try_mail_notifier)


# These only depend on chromium_config.
from master import irc_contact
from master import chromium_status
reload(irc_contact)
reload(chromium_status)


import log_parser
reload(log_parser)

import factory
reload(factory)

# These depend on the others py files in this directory.
from master import goodrevisions
from master import gatekeeper
from master import try_job_base
from master import try_job_http
from master import try_job_svn
reload(goodrevisions)
reload(gatekeeper)
reload(try_job_base)
reload(try_job_http)
reload(try_job_svn)
