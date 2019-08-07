#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Scans a list of masters and saves information in a build_db."""

from contextlib import closing, contextmanager
import base64
import httplib2
import json
import logging
import multiprocessing
import optparse
import os
import sys
import time
import urllib
import zlib

from infra_libs.luci_auth import LUCICredentials

import build_scan_db


MAX_ATTEMPTS = 4

BUILDER_WILDCARD = '*'

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_MAP_JSON = os.path.join(THIS_DIR, 'master_map.json')

BUILDBUCKET_ENDPOINT = (
    'https://cr-buildbucket.appspot.com/prpc/buildbucket.v2.Builds/')


@contextmanager
def MultiPool(processes):
  """Manages a multiprocessing.Pool making sure to close the pool when done.

  This will also call pool.terminate() when an exception is raised (and
  re-raised the exception to the calling procedure can handle it).
  """
  try:
    pool = multiprocessing.Pool(processes=processes)
    yield pool
    pool.close()
  except:
    pool.terminate()
    raise
  finally:
    pool.join()


def fetch(method, url, data=None, http=None):
  headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'User-Agent': 'Python-httplib2/2.7 -- build_scan.py',
  }
  if not http:
    http = httplib2.Http()
  http = LUCICredentials().authorize(http)
  logging.info('%s %s with %s' % (method, url, data))

  attempts = 0
  while True:
    resp, content = http.request(url, method, body=data, headers=headers)
    if resp.status == 200:
      return content
    if attempts > MAX_ATTEMPTS or 400 <= resp.status < 500:
      msg = '%s error when fetching %s %s with %s: %s' % (
          resp.status, method, url, data, content)
      logging.error(msg)
      raise ValueError(msg)

    attempts += 1
    time_to_sleep = 2 ** attempts
    logging.info(
        '%s error when fetching %s %s with %s. '
        'Sleeping for %d seconds and retrying...' % (
            resp.status, method, url, data, time_to_sleep))
    time.sleep(time_to_sleep)


def call_buildbucket(method, data, http=None):
  response = fetch(
      'POST', BUILDBUCKET_ENDPOINT + method, json.dumps(data), http)
  return json.loads(response[4:])


def get_builds_for_builder(args):
  project, bucket, builder = args
  request = {
    'pageSize': 100,
    'fields': 'builds.*.endTime,builds.*.number',
    'predicate': {
      'builder': {
        'project': project,
        'bucket': bucket,
        'builder': builder,
      },
    },
  }
  return call_buildbucket('SearchBuilds', request)


def get_builds_for_builders(project, bucket, builders, processes):
  """Fetch new builds for all builders in |builders|.

  Args:
    project: The buildbucket project for the builders.
    bucket: The buildbucket bucket for the builders.
    builders: The list of builders to check.

  Returns:
    For each builder (in the same order they were passed), a list
    [{endTime, number}] of builds with the end time and build number.
  """
  request_tuples = [(project, bucket, builder) for builder in builders]
  # Prevent map from hanging, see http://bugs.python.org/issue12157.
  if request_tuples:
    # The async/get is so that ctrl-c can interrupt the scans.
    # See http://stackoverflow.com/questions/1408356/
    # keyboard-interrupts-with-pythons-multiprocessing-pool
    with MultiPool(processes) as pool:
      builds = filter(
          bool, pool.map_async(get_builds_for_builder, request_tuples).get(
              9999999))
  else:
    builds = []

  return builds


def find_new_builds(master_url, builderlist, root_json, build_db, processes):
  """Given a dict of previously-seen builds, find new builds on each builder.

  Note that we use the 'cachedBuilds' here since it should be faster, and this
  script is meant to be run frequently enough that it shouldn't skip any builds.

  'Frequently enough' means 1 minute in the case of Buildbot or cron, so the
  only way for the scan to be overwhelmed is if > cachedBuilds builds
  complete within 1 minute. As cachedBuilds is scaled per number of slaves per
  builder, the only way for this to really happen is if a build consistently
  takes < 1 minute to complete.
  """
  new_builds = {}
  build_db.masters[master_url] = build_db.masters.get(master_url, {})

  last_finished_build = {}
  for builder, builds in build_db.masters[master_url].iteritems():
    finished = [int(y[0]) for y in builds.iteritems()
                if y[1].finished]
    if finished:
      last_finished_build[builder] = max(finished)

  builders = root_json['builders']
  if BUILDER_WILDCARD not in builderlist:
    builders = builderlist
  if not builders:
    return new_builds

  all_builds = get_builds_for_builders(
      root_json['project'], root_json['bucket'], builders, processes)

  logging.info(
      'buildbucket output for %s (project: %s, bucket: %s):',
      master_url, root_json['project'], root_json['bucket'])
  for buildername, builds in zip(builders, all_builds):
    candidate_builds = [
        build['number'] for build in builds if 'number' in build]
    current_builds = [
        build['number'] for build in builds
        if 'endTime' not in build and 'number' in build]
    logging.info(
        'builder: %s, current builds: %s, candidate builds: %s',
        buildername, current_builds, candidate_builds)

    if buildername in last_finished_build:
      new_builds[buildername] = [
          buildnum for buildnum in candidate_builds
          if buildnum > last_finished_build[buildername]]
    else:
      if buildername in build_db.masters[master_url]:
        # We've seen this builder before, but haven't seen a finished build.
        # Scan finished builds as well as unfinished.
        new_builds[buildername] = candidate_builds
      else:
        # We've never seen this builder before, only scan unfinished builds.

        # We're explicitly only dealing with current builds since we haven't
        # seen this builder before. Thus, the next time a scan is run,
        # only unfinished builds will be in the build_db. This immediately drops
        # us into the section above (builder is in the db, but no finished
        # builds yet.) In this state all the finished builds will be loaded in,
        # firing off an email storm any time the build_db changes or a new
        # builder is added. We set the last finished build here to prevent that.
        finished = set(candidate_builds) - set(current_builds)
        if finished:
          build_db.masters[master_url].setdefault(buildername, {})[
              max(finished)] = build_scan_db.gen_build(finished=True)

        new_builds[buildername] = current_builds

  logging.info('new builds for %s:', master_url)
  for builder in sorted(new_builds.keys()):
    logging.info('builder: %s, new builds: %s', builder, new_builds[builder])

  return new_builds


def find_new_builds_per_master(masters, build_db, processes):
  """Given a list of masters, find new builds and collect them under a dict."""
  with open(MASTER_MAP_JSON) as f:
    master_map = json.load(f)

  builds = {}
  master_jsons = {}
  for master, builders in masters.iteritems():
    root_json = master_map[master]
    master_jsons[master] = root_json
    builds[master] = find_new_builds(
        master, builders, root_json, build_db, processes)
  return builds, master_jsons


def get_build_json(request_tuple):
  """Used by get_build_jsons to download the json of a specific build."""
  master_url, builder, buildnum, bucket, project = request_tuple
  request = {
    'builder': {
      'project': project,
      'bucket': bucket,
      'builder': builder,
    },
    'buildNumber': buildnum,
    'fields': 'endTime,steps,input,builder,number,status',
  }
  resp = call_buildbucket('GetBuild', request)
  return (resp, master_url, builder, buildnum)


def get_build_jsons(master_builds, master_jsons, processes):
  """Get all new builds on specified masters.

  This takes a dict in the form of [master][builder][build], formats that URL
  and appends that to url_list. Then, it forks out and queries each build_url
  for build information.
  """
  request_tuples = []
  for master, builder_dict in master_builds.iteritems():
    project = master_jsons[master]['project']
    bucket = master_jsons[master]['bucket']
    for builder, new_builds in builder_dict.iteritems():
      for buildnum in new_builds:
        request_tuples.append((master, builder, buildnum, bucket, project))

  # Prevent map from hanging, see http://bugs.python.org/issue12157.
  if request_tuples:
    # The async/get is so that ctrl-c can interrupt the scans.
    # See http://stackoverflow.com/questions/1408356/
    # keyboard-interrupts-with-pythons-multiprocessing-pool
    with MultiPool(processes) as pool:
      builds = filter(bool, pool.map_async(get_build_json, request_tuples).get(
          9999999))
  else:
    builds = []

  return builds


def propagate_build_json_to_db(build_db, builds):
  """Propagates build status changes from build_json to build_db."""
  for build_json, master, builder, buildnum in builds:
    build = build_db.masters[master].setdefault(builder, {}).get(buildnum)
    if not build:
      build = build_scan_db.gen_build()

    # TODO(ehmaldonado): Rewrite this to make the intent clearer. It is
    # confusing as is, since finished and succeeded are orthogonal things.
    if build_json.get('endTime', None) is not None:
      build = build._replace(finished=True)  # pylint: disable=W0212
    else:
      # Builds can't be marked succeeded unless they are finished.
      build = build._replace(succeeded=False)  # pylint: disable=W0212

    build_db.masters[master][builder][buildnum] = build


def get_options():
  prog_desc = 'Scans for builds and outputs updated builds.'
  usage = '%prog [options] <one or more master urls>'
  parser = optparse.OptionParser(usage=(usage + '\n\n' + prog_desc))
  parser.add_option('--milo-creds',
                    help='Location to service account json credentials for '
                         'accessing Milo.')
  parser.add_option('--build-db', default='build_scan_db.json',
                    help='records the last-seen build for each builder')
  parser.add_option('--clear-build-db', action='store_true',
                    help='reset build_db to be empty')
  parser.add_option('--skip-build-db-update', action='store_true',
                    help='don\' write to the build_db, overridden by clear-db')
  parser.add_option('--parallelism', default=16,
                    help='up to this many builds can be queried simultaneously')
  parser.add_option('-v', '--verbose', action='store_true',
                    help='turn on extra debugging information')

  options, args = parser.parse_args()

  if not args:
    parser.error('you need to specify at least one master URL')

  args = [url.rstrip('/') for url in args]

  return options, args


def get_updated_builds(masters, build_db, parallelism):
  new_builds, master_jsons = find_new_builds_per_master(
      masters, build_db, parallelism)
  build_jsons = get_build_jsons(new_builds, master_jsons, parallelism)
  propagate_build_json_to_db(build_db, build_jsons)
  return master_jsons, build_jsons


def main():
  options, args = get_options()

  logging.basicConfig(level=logging.DEBUG if options.verbose else logging.INFO)

  masters = {}
  for m in set(args):
    masters[m] = BUILDER_WILDCARD

  if options.clear_build_db:
    build_db = {}
    build_scan_db.save_build_db(build_db, {}, options.build_db)
  else:
    build_db = build_scan_db.get_build_db(options.build_db)

  _, build_jsons = get_updated_builds(
      masters, build_db, int(options.parallelism))

  for _, master_url, builder, buildnum in build_jsons:
    print '%s:%s:%s' % (master_url, builder, buildnum)

  if not options.skip_build_db_update:
    build_scan_db.save_build_db(build_db, {}, options.build_db)

  return 0


if __name__ == '__main__':
  sys.exit(main())
