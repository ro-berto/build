# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import socket

from recipe_engine import recipe_api


# Path to the send_ts_mon_values package in infra-python.
SEND_TS_MON_VALUES = 'infra.tools.send_ts_mon_values'


class TSMonApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(TSMonApi, self).__init__(**kwargs)
    self._infra_python_path = None

  def _ensure_infra_python(self):
    if self._infra_python_path:
      return

    # TODO(tmrts): Create a smaller CIPD package that just contains the package
    # send_ts_mon_values and its dependencies and fetch it here instead.
    self._infra_python_path = self.m.path['cache'].join('infra-python')
    self.m.cipd.ensure(
        self._infra_python_path,
        self.m.cipd.EnsureFile().add_package(
            'infra/infra_python/${platform}', 'latest'))

  def send_value(self, name, value, fields=None, service_name='luci',
                 job_name='recipe', target=None,
                 step_name='upload ts_mon metrics'):
    """Sends a value to the ts_mon monitoring service.

    Based on the ts_mon monitoring pipeline and script for sending data to it:
    https://cs.chromium.org/chromium/infra/infra/tools/send_ts_mon_values/.
    Internal users can read more about ts_mon at go/brown-bag-timeseries-basics.

    Note that the candinality of all possible combinations of different values
    passed to fields should be less than 5000, i.e. do not use unique
    identifiers or timestamps and instead use values from a known small set.

    Additionally, the reported values for each unique combination of field
    values get downsampled by ts_mon according to the following rules:
     - no downsampling for 12 hrs
     - keep at most 1 data point for each min for the next 1 week
     - keep at most 1 data point for 5 mins interval for the next 12 weeks
     - Keep at most 1 data point for 30 mins interval for the next 52 weeks

    Therefore, please keep in mind that for metrics reported with high frequency
    (which can also be caused by having them reported at low frequency, but from
    large number of bots), the graphs may change as a result of downsampling and
    thus users may see different values in the past than what was reported
    originally and what was used to generate alerts.

    Arguments:
      name: Name of the metric, which is automatically prefixed with
          /chrome/infra, i.e. /foo/bar will become /chrome/infra/foo/bar.
      value: The value to be reported.
      fields: Dictionary with fields to be associated with the value.
      service_name: Name of the ts_mon service.
      job_name: Name of the ts_mon job.
      target: Target reporting the value, defaults to the current hostname.
      step_name: Name of the step sending information to ts_mon.
    """
    self._ensure_infra_python()

    counter_config = {'name': name, 'value': value}
    counter_config.update(fields or {})

    if target is None:
      if self._test_data.enabled:
        target = 'fake-hostname'
      else:  # pragma: no cover
        target = socket.gethostname()

    result = self.m.python(step_name, self._infra_python_path.join('run.py'), [
      SEND_TS_MON_VALUES,
      '--ts-mon-target-type', target,
      '--ts-mon-task-service-name', service_name,
      '--ts-mon-task-job-name', job_name,
      '--counter-file', self.m.json.input(counter_config),
    ])
    result.presentation.logs['counter_config'] = self.m.json.dumps(
        counter_config, indent=2, separators=(',', ': ')).splitlines()
