# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This file contains crbuild service clients, such as build service client."""

import json
import logging
import sys

from master.crbuild.common import log, CrbuildError, LOG_PREFIX
from master.deferred_resource import DeferredResource

# Importing DeferredResource adds apiclient, httplib2 and oauth2client to
# sys.path
from oauth2client.client import SignedJwtAssertionCredentials
import httplib2
import apiclient


AUTH_SCOPE = 'https://www.googleapis.com/auth/userinfo.email'
CRBUILD_HOST = 'https://cr-build.appspot.com'
BUILD_SERVICE_DISCOVERY_URL = (
    '%s/_ah/api/discovery/v1/apis/{api}/{apiVersion}/rest' % CRBUILD_HOST
)


def validate_json_key(key):
  """Validates a parsed JSON key. Raises CrbuildError if it is bad.

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
    raise CrbuildError('Unexpected key type: %s' % key['type'])
  if not key['client_email']:
    raise CrbuildError('Client email not specified')
  if not key['private_key']:
    raise CrbuildError('Private key not specified')


def create_authorized_http(json_key_filename):
  """Creates an authenticated httplib2.Http. Blocking.

  See validate_json_key docstring for json_key_filename file format.

  Called by DeferredResource from an internal thread.
  """
  try:
    with open(json_key_filename, 'r') as f:
      key = json.load(f)
      validate_json_key(key)
      creds = SignedJwtAssertionCredentials(key['client_email'],
                                            key['private_key'], AUTH_SCOPE)
  except Exception as ex:
    msg = 'Bad crbuild json key in %s: %s' % (json_key_filename, ex.message)
    log(msg, level=logging.ERROR)
    raise CrbuildError(msg)

  return creds.authorize(httplib2.Http())


def create_build_service(http_factory):
  """Asynchronously creates build API resource.

  Returns:
    A DeferredResource as Deferred.
  """
  return DeferredResource.build(
      'build',
      'v1',
      http_factory=http_factory,
      discoveryServiceUrl=BUILD_SERVICE_DISCOVERY_URL,
      verbose=True,
      log_prefix=LOG_PREFIX,
  )
