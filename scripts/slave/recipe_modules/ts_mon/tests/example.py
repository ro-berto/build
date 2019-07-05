# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'ts_mon',
]


def RunSteps(api):
  api.ts_mon.send_value('/example/metric', 42)
  api.ts_mon.send_value(
      name='/example/metric',
      value=42,
      fields={'foo': 'bar'},
      service_name='example_service',
      job_name='example_job',
      target='example_target',
      step_name='custom upload step name')


def GenTests(api):
  yield api.test('basic')
