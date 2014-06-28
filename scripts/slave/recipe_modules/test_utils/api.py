# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class TestUtilsApi(recipe_api.RecipeApi):
  @staticmethod
  def format_step_text(data):
    """
    Returns string suitable for use in a followup function's step result's
    presentation step text.

    Args:
      data - iterable of sections, where each section is one of:
        a) tuple/list with one element for a single-line section
           (always displayed)
        b) tuple/list with two elements where first one is the header,
           and the second one is an iterable of content lines; if there are
           no contents, the whole section is not displayed
    """
    step_text = []
    for section in data:
      if len(section) == 1:
        # Make it possible to display single-line sections.
        step_text.append('<br/>%s<br/>' % section[0])
      elif len(section) == 2:
        # Only displaying the section (even the header) when it's non-empty
        # simplifies caller code.
        if section[1]:
          step_text.append('<br/>%s<br/>' % section[0])
          step_text.extend(('%s<br/>' % line for line in section[1]))
      else:  # pragma: no cover
        raise ValueError(
            'Expected a one or two-element list, got %r instead.' % section)
    return ''.join(step_text)

  def determine_new_failures(self, caller_api, tests, deapply_patch_fn):
    """
    Utility function for running steps with a patch applied, and retrying
    failing steps without the patch. Failures from the run without the patch are
    ignored.

    Args:
      caller_api - caller's recipe API; this is needed because self.m here
                   is different than in the caller (different recipe modules
                   get injected depending on caller's DEPS vs. this module's
                   DEPS)
      tests - iterable of objects implementing the Test interface above
      deapply_patch_fn - function that takes a list of failing tests
                         and undoes any effect of the previously applied patch
    """
    # Convert iterable to list, since it is enumerated multiple times.
    tests = list(tests)

    if self.m.step_history.failed:
      yield self.m.python.inline(
        'Aborting due to failed build state',
        "import sys; sys.exit(1)",
        always_run=True, abort_on_failure=True)
      return  # won't actually hit this, but be explicit

    def run(prefix, tests):
      yield (t.pre_run(caller_api, prefix) for t in tests)
      yield (t.run(caller_api, prefix) for t in tests)
      yield (t.post_run(caller_api, prefix) for t in tests)

    yield run('with patch', tests)

    failing_tests = []
    for t in tests:
      if not t.has_valid_results(caller_api, 'with patch'):
        yield self.m.python.inline(
          t.name,
          r"""
          import sys
          print 'TEST RESULTS WERE INVALID'
          sys.exit(1)
          """,
          always_run=True)
      elif t.failures(caller_api, 'with patch'):
        failing_tests.append(t)
    if not failing_tests:
      return

    yield deapply_patch_fn(failing_tests)

    yield run('without patch', failing_tests)
    yield (self._summarize_retried_test(caller_api, t) for t in failing_tests)

  def _summarize_retried_test(self, caller_api, test):
    if not test.has_valid_results(caller_api, 'without patch'):
      return self.m.python.inline(
        test.name,
        r"""
        import sys
        print 'TEST RESULTS WERE INVALID'
        sys.exit(1)
        """,
        always_run=True)

    ignored_failures = set(test.failures(caller_api, 'without patch'))
    new_failures = set(test.failures(caller_api, 'with patch')) - ignored_failures

    def followup_fn(step_result):
      p = step_result.presentation

      p.step_text += self.format_step_text([
          ['failures:', new_failures],
          ['ignored:', ignored_failures]
      ])

      if new_failures:
        p.status = 'FAILURE'
      elif ignored_failures:
        p.status = 'WARNING'

    return self.m.python.inline(
      test.name,
      r"""
      import sys, json
      failures = json.load(open(sys.argv[1], 'rb'))

      success = True

      if failures['new']:
        success = False
        print 'New failures:'
        for f in failures['new']:
          print f

      if failures['ignored']:
        print 'Ignored failures:'
        for f in failures['ignored']:
          print f

      sys.exit(0 if success else 1)
      """,
      args=[
        self.m.json.input({
          'new': list(new_failures),
          'ignored': list(ignored_failures),
        })
      ],
      followup_fn=followup_fn,
      always_run=True,
    )
