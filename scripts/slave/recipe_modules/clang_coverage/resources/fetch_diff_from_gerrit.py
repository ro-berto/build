#!/usr/bin/python
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This script fetches the diff of the patch from Gerrit and redirect to stdout.

For more details on the REST APIs of Gerrit, please refer to:
https://gerrit-review.googlesource.com/Documentation/rest-api.html.
"""

import argparse
import base64
import json
import sys
import urllib2

# A fixed prefix in the http response.
_RESPONSE_PREFIX = ')]}\n'


def fetch_diff(host, project, change, patchset):
  """Fetches diff of the patch from Gerrit.

  Args:
    host (str): The url of the host.
    project (str): The project name.
    change (int): The change number.
    patchset (int): The patchset number.

  Returns:
    A string of the fetched diff.
  """
  project_quoted = urllib2.quote(project, safe='')

  # Uses the Get Change API to get and parse the revision of the patchset.
  # https://gerrit-review.googlesource.com/Documentation/rest-api-changes.html#get-change.
  template_to_get_revisions = 'https://%s/changes/%s~%d?o=ALL_REVISIONS'
  url_to_get_reivisions = template_to_get_revisions % (host, project_quoted,
                                                       change)
  response = urllib2.urlopen(url_to_get_reivisions)
  change_details = json.loads(response.read()[len(_RESPONSE_PREFIX):])
  patchset_revision = None

  for revision, value in change_details['revisions'].iteritems():
    if patchset == value['_number']:
      patchset_revision = revision
      break

  if not patchset_revision:
    raise RuntimeError(
        'Patchset %d is not found in the change descriptions returned by '
        'requesting %s.' % (patchset, url_to_get_reivisions))

  # Uses the Get Patch API to get the diff.
  # https://gerrit-review.googlesource.com/Documentation/rest-api-changes.html#get-patch.
  template_to_get_patch = 'https://%s/changes/%s~%d/revisions/%s/patch'
  url_to_get_patch = template_to_get_patch % (host, project_quoted, change,
                                              patchset_revision)
  response = urllib2.urlopen(url_to_get_patch)
  diff = base64.b64decode(response.read())
  return diff


def _parse_args():
  arg_parser = argparse.ArgumentParser()
  arg_parser.usage = __doc__

  arg_parser.add_argument(
      '--host', required=True, type=str, help='The url of the host.')

  arg_parser.add_argument(
      '--project', required=True, type=str, help='The project name')

  arg_parser.add_argument(
      '--change', required=True, type=int, help='The change number.')

  arg_parser.add_argument(
      '--patchset', required=True, type=int, help='The patchset number.')

  return arg_parser.parse_args()


def main():
  args = _parse_args()
  diff = fetch_diff(args.host, args.project, args.change, args.patchset)
  sys.stdout.write(diff)


if __name__ == '__main__':
  sys.exit(main())
