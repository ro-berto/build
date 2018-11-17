# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os
import urllib

from recipe_engine import recipe_api


_BASE_URL = 'https://chromeperf.appspot.com'
_PINPOINT_BASE_URL = 'https://pinpoint-dot-chromeperf.appspot.com'


class PerfDashboardApi(recipe_api.RecipeApi):
  """Provides steps to take a list of perf points and post them to the
  Chromium Perf Dashboard.  Can also use the test url for testing purposes."""

  def get_skeleton_point(self, test, revision, value, bot=None):
    # TODO: masterid is really mastername
    assert (test != '')
    assert (revision != '')
    assert (value != '')
    return {
        'master': self.m.properties['mastername'],
        'bot': bot or self.m.buildbucket.builder_name,
        'test': test,
        'revision': revision,
        'value': value,
        'masterid': self.m.properties['mastername'],
        'buildername': self.m.buildbucket.builder_name,
        'buildnumber': self.m.buildbucket.build.number,
    }

  def add_dashboard_link(self, presentation, test, revision, bot=None):
    """Adds a results-dashboard link to the step presentation.

    Must be called from a follow-up function of the step, to which the link
    should be added. For a working link, the parameters test, revision and bot
    must match to the parameters used to upload points to the dashboard.

    Args:
      presentation: A step presentation object. Can be obtained by
                    step_result.presentation from a followup_fn of a step.
      test: Slash-separated test path.
      revision: The build revision, e.g. got_revision from the update step.
      bot: The bot name used for the data on the perf dashboard.
    """
    assert presentation
    assert test
    assert revision
    params = urllib.urlencode({
        'masters': self.m.properties['mastername'],
        'bots': bot or self.m.buildbucket.builder_name,
        'tests': test,
        'rev': revision,
    })
    presentation.links['Results Dashboard'] = (
        '%s/report?%s' % (_BASE_URL, params))

  def set_default_config(self):
    # TODO: Remove.
    pass

  def add_point(self, data, halt_on_failure=False, name=None, **kwargs):
    return self.post(name or 'perf dashboard post', '%s/add_point' % _BASE_URL,
                     {'data': json.dumps(data)}, halt_on_failure, **kwargs)

  def post_bisect_results(self, data, halt_on_failure=False, **kwargs):
    """Posts bisect results to Perf Dashboard."""
    return self.post('Post bisect results',
                     '%s/post_bisect_results' % _BASE_URL,
                     {'data': json.dumps(data)}, halt_on_failure, **kwargs)

  def upload_isolate(self, builder_name, change, isolate_server,
                     isolate_map, halt_on_failure=False, **kwargs):
    data = {
        'builder_name': builder_name,
        'change': json.dumps(change),
        'isolate_server': isolate_server,
        'isolate_map': json.dumps(isolate_map),
    }
    return self.post('pinpoint isolate upload',
                     '%s/api/isolate' % _PINPOINT_BASE_URL,
                     data, halt_on_failure, **kwargs)


  def get_change_info(self, commits):
    change = {
        'commits': commits,
    }

    deps_revision_overrides = self.m.properties.get(
        'deps_revision_overrides')
    if deps_revision_overrides:
      change['commits'] += list(
          {'repository': repository, 'git_hash': git_hash}
          for repository, git_hash in deps_revision_overrides.iteritems())

    if self.m.tryserver.is_tryserver:
      change['patch'] = {
          'server': 'https://' + self.m.tryserver.gerrit_change.host,
          'change': self.m.tryserver.gerrit_change.change,
          'revision': self.m.tryserver.gerrit_change.patchset,
      }

    return change

  def post(self, name, url, data, halt_on_failure, debug_info=None, **kwargs):
    """Send a POST request to a URL with a payload.

    Args:
      name: The name of the step.
      url: The URL to post to.
      data: A dict of parameters to send in the body of the request.
      halt_on_failure: If True, the step turns purple on failure. Otherwise, it
          turns orange.
      debug_info (list[str]|None): An optional list of log lines to add to the
          post step as debugging information.
    """
    post_json_args = [
        url, '-i', self.m.json.input(data), '-o', self.m.json.output()]
    if self.m.runtime.is_luci:
      token = self.m.service_account.default().get_access_token()
      post_json_args += ['-t', self.m.raw_io.input_text(token)]
    step_result = self.m.python(
        name=name, script=self.resource('post_json.py'), args=post_json_args,
        **kwargs)

    if debug_info:
      step_result.presentation.logs['Debug Info'] = debug_info

    response = step_result.json.output
    if not response or response['status_code'] != 200:  # pragma: no cover
      error = response['status_code'] if response else 'None'
      reason = ('Failed to post to Perf Dashboard. '
                'Error response: %s' % error)
      if halt_on_failure:
        self.halt(step_result, reason)
      else:
        self.warning(step_result, reason)

    return step_result

  def halt(self, step_result, reason):  # pragma: no cover
    step_result.presentation.step_text = reason
    step_result.presentation.status = self.m.step.FAILURE
    raise self.m.step.StepFailure(reason)

  def warning(self, step_result, reason):  # pragma: no cover
    step_result.presentation.step_text = reason
    step_result.presentation.status = self.m.step.WARNING
