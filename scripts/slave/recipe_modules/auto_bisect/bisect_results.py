# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

class BisectResults(object):
  def __init__(self, bisector):
    """Create a new results object from a finished bisect job."""
    if not bisector.bisect_over:
      raise ValueError('Invalid parameter, the bisect must be over by the time'
                       ' the BisectResults constructor is called')
    self._bisector = bisector
    self._results_dict = {}
    self._prepare_results()

  def to_json(self):
    return json.dumps(self._results_dict)

  def _prepare_results(self):
    """Checks several flags to compose the results output."""
    # TODO: Format this more like the current bisect
    if self._bisector.failed:
      self._results_dict['header'] = 'Failed bisect.'
    elif self._bisector.failed_confidence or self._bisector.failed_direction:
      self._results_dict['header'] = 'Aborted early. See warnings.'
    elif self._bisector.warnings:
      self._results_dict['header'] = 'Succeeded with warnings.'
    else:
      self._results_dict['header'] = 'Succeeded.'

    if self._bisector.warnings:
      self._results_dict['warnings'] = list(self._bisector.warnings)

    self._= '\n'.join(['%s: %s' % (k, v) for k, v in
                       self._bisector.bad_rev.test_info().iteritems()])
    # TODO: Add the culprit CL details if available
    self._compose_revisions_list()

  def _compose_revisions_list(self):
    self._results_dict['revisions'] = [{
        'commit_pos': r.commit_pos or '',
        'revision_string': r.revision_string,
        'mean_value': r.mean_value if r.mean_value is not None else 'N/A',
        'std_err': r.std_err if r.std_err is not None else 'N/A',
        'good_or_bad': 'good' if r.good else 'bad' if r.bad else 'unknown',
        'tested': 'tested' if r.tested else 'aborted' if r.aborted else 'untested',
        'culprit': self._bisector.culprit == r
    } for r in self._bisector.revisions]


