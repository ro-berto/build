# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import functools
import time

from infra_libs import ts_mon

queries = ts_mon.CounterMetric('buildbot/master/db/queries',
    description='Number of database queries made, by success/failure status.')
durations = ts_mon.CumulativeDistributionMetric('buildbot/master/db/durations',
    description='Time taken to make a database request.',
    units=ts_mon.MetricsDataUnits.MILLISECONDS)


def instrumented_thd(name):
  """
  A decorator for the "thd" function passed to the database thread pool.

  Reports metrics about the database operation's performance.
  """
  def decorator(thd):
    @functools.wraps(thd)
    def wrapper(*args, **kwargs):
      start_time = time.time()
      status = 'success'
      try:
        return thd(*args, **kwargs)
      except:
        status = 'failure'
        raise
      finally:
        duration = int((time.time() - start_time) * 1000)
        queries.increment(fields={'op': name, 'status': status})
        durations.add(duration, fields={'op': name})
    return wrapper
  return decorator
