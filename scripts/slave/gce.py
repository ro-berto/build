# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Utilities for interfacing with Google Compute Engine.
"""

import httplib
import json
import logging
import socket
import time
import urlparse


LOGGER = logging.getLogger('gce')
TRY_LIMIT = 5


class Authenticator(object):
  """Authenticator implementation that uses GCE metadata service for token.
  """

  _INFO_URL = 'http://metadata.google.internal'

  _cache_is_gce = None

  @classmethod
  def is_gce(cls):
    if cls._cache_is_gce is None:
      cls._cache_is_gce = cls._test_is_gce()
    return cls._cache_is_gce

  @classmethod
  def _test_is_gce(cls):
    # Based on https://cloud.google.com/compute/docs/metadata#runninggce
    try:
      resp = cls._get(cls._INFO_URL)
    except socket.error:
      # Could not resolve URL.
      return False
    return resp.getheader('Metadata-Flavor', None) == 'Google'

  @staticmethod
  def _get(url, **kwargs):
    next_delay_sec = 1
    for i in xrange(TRY_LIMIT):
      if i > 0:
        # Retry server error status codes.
        LOGGER.info('Encountered server error; retrying after %d second(s).',
                    next_delay_sec)
        time.sleep(next_delay_sec)
        next_delay_sec *= 2

      p = urlparse.urlparse(url)
      c = GetConnectionClass(protocol=p.scheme)(p.netloc)
      c.request('GET', url, **kwargs)
      resp = c.getresponse()
      LOGGER.debug('GET [%s] #%d/%d (%d)', url, i+1, TRY_LIMIT, resp.status)
      if resp.status < httplib.INTERNAL_SERVER_ERROR:
        return resp


def GetConnectionClass(protocol=None):
  if protocol is None:
    protocol = 'https'
  if protocol == 'https':
    return httplib.HTTPSConnection
  elif protocol == 'http':
    return httplib.HTTPConnection
  else:
    raise RuntimeError(
        "Don't know how to work with protocol '%s'" % protocol)
