# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""An interface for holding state and result of revisions in a bisect job.

When implementing support for tests other than perf, one should extend this
class so that the bisect module and recipe can use it.

See perf_revision_state for an example.
"""

class RevisionState(object):
  """Abstracts the state of a single revision on a bisect job."""

  def __init__(self, revision_string, bisector):
    """Create a new instance to track the state of a revision.

    Args:
      revision_string: should be in the following format:
        [(chromium|src)@](<commit_pos>|<commit_hash)(,<repo>@<commit>)*
        E.g.:
          'a0b1c2ffff89009909090' (full or abbrev. commit hash)
          '123456'
          'src@123456'
          'chromium@123456'
          'src@abc01234ffff,v8@00af5ceb888ff'
      bisector: an instance of Bisector, the object performing the bisection.
    """
    super(RevisionState, self).__init__()
    self.bisector = bisector
    self._good = None
    self.build_status_url = None
    self.in_progress = False
    self.aborted = False
    self.next_revision = None
    self.previous_revision = None
    self.revision_string = revision_string
    self.commit_hash, self.commit_pos = self._commit_from_rev_string()
    self.build_job_name = None
    self.test_job_name = None
    self.built = False
    self.build_url = self.bisector.get_platform_gs_prefix() + self._gs_suffix()

  @property
  def good(self):
    return self._good == True

  @property
  def bad(self):
    return self._good == False

  @property
  def tested(self):
    return self._good is not None and not self.aborted

  @good.setter
  def good(self, value):
    self._good = value

  @bad.setter
  def bad(self, value):
    self._good = not value

  @tested.setter
  def _set_tested(self, _):
    raise Exception('The tested property cannot be set. '
                    'Use the .good or .bad properties instead.')

  def start_job(self):
    """Starts a build, or a test job if the build is available."""
    if self._is_build_archived():
      self.built = True
      self.in_progress = True
      self._do_test()
    elif not self.in_progress:
      self._request_build()
      self.in_progress = True

  def abort(self):
    """Aborts the job.

    This method is typically called when the bisect no longer requires it. Such
    as when a later good revision or an earlier bad revision have been found in
    parallel.
    """
    assert self.in_progress
    self.in_progress = False
    self.aborted = True
    # TODO: actually kill buildbot job if it's the test step.

  def deps_change(self):
    """Uses `git show` to see if a given commit contains a DEPS change."""
    api = self.bisector.api
    step_result = api.m.git('show', '--name-only', '--pretty=format:',
               self.commit_hash, stdout=api.m.raw_io.output())
    if self.bisector.dummy_builds:
      return False
    if 'DEPS' in step_result.stdout.splitlines():
      return True
    return False

  def update_status(self):
    """Checks on the pending jobs and updates status accordingly.

    This method will check for the build to complete and then trigger the test,
    or will wait for the test as appropriate.

    To wait for the test we try to get the buildbot job url from GS, and if
    available, we query the status of such job.
    """
    if not self.in_progress:
      return
    if not self.built:
      if self._is_build_archived():
        self.start_job()
      else:
        pass # TODO: Check if build has not timed out.
      return
    if not self.build_status_url:
      self.build_status_url = self._get_build_status_url()
    if self.build_status_url:
      if 'Complete' in self._get_build_status():
        self._read_test_results()
        self.in_progress = False

  def _is_build_archived(self):
    """Checks if the revision is already built and archived."""
    api = self.bisector.api
    result = api.gsutil_file_exists(self.build_url)
    if self.bisector.dummy_builds:
      return self.in_progress
    return result

  def _gs_suffix(self):
    """Provides the expected right half of the build filename.

    This takes into account whether the build has a deps patch.
    """
    # TODO: Implement the logic for deps patch changes.
    return self.commit_hash + '.zip'

  def _commit_from_rev_string(self):
    """Gets the chromium repo commit hash and position for this revision.

    If there are specified dependency revisions in the string, we don't compute
    either the position or hash"""
    pieces = self.revision_string.split(',')
    if len(pieces) > 1:
      return None, None
    if (pieces[0].startswith('chromium@') or
        pieces[0].startswith('src@') or
        not '@' in pieces[0]):
      hash_or_pos = pieces[0].split('@')[-1]
      if self._check_if_hash(hash_or_pos):
        commit_pos = self._get_pos_from_hash(hash_or_pos)
        commit_hash = self._get_hash_from_pos(commit_pos)
      else:
        commit_hash = self._get_hash_from_pos(hash_or_pos)
        commit_pos = self._get_pos_from_hash(commit_hash)
      return commit_hash, commit_pos

  def _check_if_hash(self, s):
    if len(s) <= 8:
      # We expect commit positions to be 8 digits or less
      try:
        int(s)
        # If the cast did not raise an error, assume s is a commit position.
        return False
      except ValueError:
        pass
    # If the following cast raises an error then s does not represent a valid
    # SHA hash, therefore, we let the error bubble up.
    int(s, 16)
    return True

  def _get_pos_from_hash(self, sha):
    api = self.bisector.api
    return api.m.commit_position.chromium_commit_position_from_hash(sha)

  def _get_hash_from_pos(self, pos):
    api = self.bisector.api
    return api.m.commit_position.chromium_hash_from_commit_position(pos)
