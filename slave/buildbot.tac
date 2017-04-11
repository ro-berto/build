# -*- python -*-
# ex: set syntax=python:

# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Chrome Buildbot slave configuration

import argparse
import os
import socket
import sys

from buildslave.bot import BuildSlave
from infra_libs import ts_mon
from twisted.application import service
from twisted.internet import reactor

# Register the commands.
from slave import chromium_commands
# Load default settings.
import config

# config.Master.active_master and config.Master.active_slavename
# are set in run_slave.py
ActiveMaster = config.Master.active_master
slavename = config.Master.active_slavename

# Slave properties:
password = config.Master.GetBotPassword()
host = None
port = None
basedir = None
keepalive = 300
usepty = 0
umask = None


print 'Using slave name %s' % slavename

if password is None:
    print >> sys.stderr, '*** No password configured in %s.' % repr(__file__)
    sys.exit(1)

if host is None:
    host = os.environ.get('TESTING_MASTER_HOST', ActiveMaster.master_host)
print 'Using master host %s' % host

if port is None:
    port = ActiveMaster.slave_port
print 'Using master port %s' % port

if basedir is None:
    basedir = os.path.dirname(os.path.abspath(__file__))


def setup_timeseries_monitoring():
    parser = argparse.ArgumentParser()
    ts_mon.add_argparse_options(parser)
    parser.set_defaults(
        ts_mon_target_type='task',
        ts_mon_task_service_name='buildslave',
        ts_mon_task_job_name='buildslave',
    )
    args = parser.parse_args([])
    ts_mon.process_argparse_options(args)


def stop_timeseries_monitoring():
    ts_mon.close()


reactor.addSystemEventTrigger('during', 'startup', setup_timeseries_monitoring)
reactor.addSystemEventTrigger('during', 'shutdown', stop_timeseries_monitoring)

application = service.Application('buildslave')
s = BuildSlave(host, port, slavename, password, basedir, keepalive, usepty,
               umask=umask, allow_shutdown='file')
s.setServiceParent(application)
