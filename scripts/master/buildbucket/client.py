# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This file contains buildbucket service client."""

import json
import logging
import sys

from master.buildbucket import common
from master.deferred_resource import DeferredResource

from oauth2client.client import SignedJwtAssertionCredentials
import httplib2
import apiclient


AUTH_SCOPE = 'https://www.googleapis.com/auth/userinfo.email'
BUILDBUCKET_HOSTNAME = 'cr-buildbucket.appspot.com'


def buildbucket_api_discovery_url(hostname=None):
  return (
      'https://%s/_ah/api/discovery/v1/apis/{api}/{apiVersion}/rest' % hostname)


def validate_json_key(key):
  """Validates a parsed JSON key. Raises buildbucket.Error if it is bad.

  Example of a well-formatted key, taken from GAE console:
    {
      "private_key_id": "4168d274cdc7a1eaef1c59f5b34bdf255",
      "private_key": ("-----BEGIN PRIVATE KEY-----\nMIIhkiG9w0BAQEFAASCAmEwsd" +
                      "sdfsfFd\ngfxFChctlOdTNm2Wrr919Nx9q+sPV5ibyaQt5Dgn89fKV" +
                      "jftrO3AMDS3sMjaE4Ib\nZwJgy90wwBbMT7/YOzCgf5PZfivUe8KkB" +
                      -----END PRIVATE KEY-----\n",
      "client_email": "234243-rjstu8hi95iglc8at3@developer.gserviceaccount.com",
      "client_id": "234243-rjstu8hi95iglc8at3.apps.googleusercontent.com",
      "type": "service_account"
    }
  """
  if key['type'] != 'service_account':
    raise common.Error('Unexpected key type: %s' % key['type'])
  if not key['client_email']:
    raise common.Error('Client email not specified')
  if not key['private_key']:
    raise common.Error('Private key not specified')


def create_authorized_http(json_key_filename):
  """Creates an httplib2.Http authenticated with SignedJwtAssertionCredentials.

  This call is blocking.
  See validate_json_key docstring for json_key_filename file format.
  Normally called by DeferredResource from an internal thread.

  Returns:
    Authenticated httplib2.Http.
  """
  try:
    with open(json_key_filename, 'r') as f:
      key = json.load(f)
      validate_json_key(key)
      creds = SignedJwtAssertionCredentials(key['client_email'],
                                            key['private_key'], AUTH_SCOPE)
  except Exception as ex:
    msg = ('Invalid buildbucket json key in %s: %s' %
           (json_key_filename, ex.message))
    common.log(msg, level=logging.ERROR)
    raise common.Error(msg)

  return creds.authorize(httplib2.Http())


def create_buildbucket_service(http_factory, hostname=None):
  """Asynchronously creates buildbucket API resource.

  Returns:
    A DeferredResource as Deferred.
  """
  return DeferredResource.build(
      'buildbucket',
      'v1',
      http_factory=http_factory,
      discoveryServiceUrl=buildbucket_api_discovery_url(hostname),
      verbose=True,
      log_prefix=common.LOG_PREFIX,
  )
