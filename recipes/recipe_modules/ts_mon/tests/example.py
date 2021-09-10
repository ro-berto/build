# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
  'ts_mon',
]


def RunSteps(api):
  api.ts_mon.send_value('/example/metric', 'counter', 42)
  api.ts_mon.send_value(
      name='/example/metric',
      metric_type='float',
      value=42.0,
      fields={'foo': 'bar'},
      service_name='example_service',
      job_name='example_job',
      step_name='custom upload step name')
  api.ts_mon.send_values_batch(
      '/example/metric', 'counter', [(42, {'a': 1}), (43, {'a': 2})])


def GenTests(api):
  yield api.test('basic')
