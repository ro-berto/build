#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This script will change a master from using postgresql to sqlite.

It:
1) Creates .stop_master_lifecycle to stop master manager.
2) Stops the master.
3) Dumps the postgres database and imports it into sqlite.
4) Removes the .dbconfig file indicating buildbot should now use sqlite.
5) Starts the master.
6) Removes .stop_master_lifecycle.

If this script fails in the middle you will have to restore it to a known state
manually.

Run this script in the master's directory.  Some third_party libraries need to
be on the PYTHONPATH, so use runit.py:
  export TOOLS_DIR=~/buildbot/build/scripts/tools
  ${TOOLS_DIR}/runit.py ${TOOLS_DIR}/migrate_psql_to_sqlite.py

Without any arguments this will run in a dry-run mode and create a
'dry-run-psql-conversion.sqlite' file for you to inspect manually.  Use
--no-dry-run to actually stop and restart the master and update the config.
"""

import argparse
import logging
import os
import sqlite3
import subprocess
import sys

from buildbot import cache
from buildbot.db import connector
from twisted.internet import defer, reactor


class FakeBuildMaster(object):
  def __init__(self):
    self.caches = cache.CacheManager()


@defer.inlineCallbacks
def Run(args):
  if args.no_dry_run:
    sqlite_filename = 'state.sqlite'
  else:
    sqlite_filename = 'dry-run-psql-conversion.sqlite'

  # Read the dbconfig.  This will fail if the config doesn't exist and the
  # master doesn't use postgresql.
  dbconfig = {}
  execfile('.dbconfig', dbconfig)

  if args.no_dry_run:
    # Stop master manager from touching this master while we play with it.
    if os.path.exists('.stop_master_lifecycle'):
      raise Exception('A .stop_master_lifecycle file already exists')
    logging.info('Creating .stop_master_lifecycle file')
    with open('.stop_master_lifecycle', 'w') as fh:
      fh.write('migrate_psql_to_sqlite.py')

    # Stop the master.
    logging.info('Stopping master')
    subprocess.check_call(['make', 'stop'])
    subprocess.check_call(['make', 'wait'])

  # Dump the postgres database.
  logging.info('Dumping postgres database %s', dbconfig['dbname'])
  env = os.environ.copy()
  env['PGPASSWORD'] = dbconfig['password']
  sql = subprocess.check_output(['pg_dump',
      '-d', dbconfig['dbname'],
      '-U', dbconfig['username'],
      '-h', 'localhost',
      '--data-only',
      '--inserts'], env=env)

  # Strip out postgres-specific things.
  sql = '\n'.join(
      line for line in sql.splitlines()
      if not line.startswith('SET') and
         not line.startswith('INSERT INTO migrate_version') and
         not 'pg_catalog.setval' in line)

  # Delete any existing sqlite database.
  if os.path.exists(sqlite_filename):
    os.unlink(sqlite_filename)

  # Create the new sqlite database.
  logging.info('Creating empty sqlite database in %s', sqlite_filename)
  db = connector.DBConnector(
      FakeBuildMaster(), 'sqlite:///%s' % sqlite_filename, '.')
  yield db.model.upgrade()

  # Import the data into the sqlite database.
  logging.info('Filling sqlite database %s', sqlite_filename)
  conn = sqlite3.connect(sqlite_filename)
  cursor = conn.cursor()
  cursor.execute('pragma synchronous = off')
  cursor.execute('pragma journal_mode = memory')
  cursor.executescript(sql)
  conn.commit()
  conn.close()

  if args.no_dry_run:
    # Remove the .dbconfig to make it use the sqlite database.
    logging.info('Moving .dbconfig file to dbconfig.bak')
    os.rename('.dbconfig', 'dbconfig.bak')

    # Start the master.
    logging.info('Starting master')
    subprocess.check_call(['make', 'start'])

    # Let master manager take over again.
    logging.info('Removing .stop_master_lifecycle file')
    os.unlink('.stop_master_lifecycle')

    logging.info('Done!')
  else:
    logging.info('Dry-run done!')


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--no-dry-run', action='store_true')
  args = parser.parse_args()

  def HandleError(err):
    err.printTraceback()
    reactor.stop()

  def Start():
    d = Run(args)
    d.addCallback(lambda _: reactor.stop())
    d.addErrback(HandleError)

  logging.basicConfig(level=logging.INFO,
                      format='\033[94m%(asctime)s %(message)s\033[0m')
  reactor.callWhenRunning(Start)
  reactor.run()


if __name__ == '__main__':
  main()
