# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib
import json
import re

from recipe_engine import recipe_api


def get_reviewers(commit_infos):
  """Get a set of authors and reviewers from 'recipes.py autoroll' commit infos.
  """
  reviewers = set()
  for project, commits in commit_infos.iteritems():
    for commit in commits:
      reviewers.add(commit['author'])
      for field in ('R', 'TBR'):
        for m in re.findall(
            '^%s=(.*)' % field, commit['message'], re.MULTILINE):
          for s in m.split(','):
            if s:
              # TODO(martiniss): infer domain for email address somehow?
              if '@' in s:
                reviewers.add(s.strip())
  return reviewers


def get_bugs(commit_infos):
  """Return a set of bug IDs from 'recipes.py autoroll' commit infos.
  """
  bugs = set()
  for project, commits in commit_infos.iteritems():
    for commit in commits:
      for m in re.findall('^BUG=(.*)', commit['message'], re.MULTILINE):
        for s in m.split(','):
          if s:
            bugs.add(s.strip())
  return bugs


def get_blame(commit_infos):
  blame = []
  for project, commits in commit_infos.iteritems():
    blame.append('%s:' % project)
    for commit in commits:
      message = commit['message'].splitlines()
      # TODO(phajdan.jr): truncate long messages.
      message = message[0] if message else 'n/a'
      blame.append('  https://crrev.com/%s %s (%s)' % (
          commit['revision'], message, commit['author']))
  return blame


COMMIT_MESSAGE_HEADER = (
"""
This is an automated CL created by the recipe roller. This CL rolls recipe
changes from upstream projects (e.g. depot_tools) into downstream projects
(e.g. tools/build).
""")


NON_TRIVIAL_MESSAGE = (
"""

Please review the expectation changes, and LGTM as normal. The recipe roller
will *NOT* CQ the change itself, so you must commit the change manually.
"""
)

COMMIT_MESSAGE_FOOTER = (
"""

More info is at https://goo.gl/zkKdpD. Use https://goo.gl/noib3a to file a bug
(or complain)

""")


def get_commit_message(roll_result):
  """Construct a roll commit message from 'recipes.py autoroll' result.
  """
  message = 'Roll recipe dependencies (%s).\n' % (
      'trivial' if roll_result['trivial'] else 'nontrivial')
  message += COMMIT_MESSAGE_HEADER
  if not roll_result['trivial']:
    message += NON_TRIVIAL_MESSAGE
  message += COMMIT_MESSAGE_FOOTER

  commit_infos = roll_result['picked_roll_details']['commit_infos']

  message += '%s\n' % '\n'.join(get_blame(commit_infos))
  message += '\n'
  message += 'R=%s\n' % ','.join(get_reviewers(commit_infos))
  message += 'BUG=%s\n' % ','.join(get_bugs(commit_infos))
  return message


class RecipeAutorollerApi(recipe_api.RecipeApi):
  def prepare_checkout(self):
    """Creates a default checkout for the recipe autoroller."""
    self.m.gclient.set_config('recipes_py')
    self.m.gclient.checkout()
    self.m.gclient.runhooks()

  def roll_projects(self, projects):
    """Attempts to roll each project from the provided list.

    If rolling any of the projects leads to failures, other
    projects are not affected.
    """
    project_data = self.m.luci_config.get_projects()
    with recipe_api.defer_results():
      for project in projects:
        with self.m.step.nest(str(project)):
          self._roll_project(project_data[project])

  def _roll_project(self, project_data):
    with self.m.tempfile.temp_dir('roll_%s' % project_data['id']) as workdir:
      self.m.git.checkout(
          project_data['repo_url'], dir_path=workdir, submodules=False)

      # Introduce ourselves to git - also needed for git cl upload to work.
      self.m.git(
          'config', 'user.email', 'recipe-roller@chromium.org', cwd=workdir)
      self.m.git('config', 'user.name', 'recipe-roller', cwd=workdir)

      # git cl upload cannot work with detached HEAD, it requires a branch.
      self.m.git('checkout', '-t', '-b', 'roll', 'origin/master', cwd=workdir)

      recipes_cfg_path = workdir.join('infra', 'config', 'recipes.cfg')

      roll_step = self.m.python('roll',
          self.m.path['checkout'].join('recipes-py', 'recipes.py'),
          ['--package', recipes_cfg_path, 'autoroll',
           '--output-json', self.m.json.output()])
      roll_result = roll_step.json.output

      if roll_result['success']:
        self._process_successful_roll(roll_step, roll_result, workdir)
      else:
        if (not roll_result['roll_details'] and
            not roll_result['rejected_candidates_details']):
          roll_step.presentation.step_text += ' (already at latest revisions)'
        else:
          roll_step.presentation.status = self.m.step.FAILURE

  def _process_successful_roll(self, roll_step, roll_result, workdir):
    roll_step.presentation.logs['blame'] = get_blame(
        roll_result['picked_roll_details']['commit_infos'])

    if roll_result['trivial']:
      roll_step.presentation.step_text += ' (trivial)'
    else:
      roll_step.presentation.status = self.m.step.WARNING

    # We use recipes.cfg hashes to uniquely identify changes (which might be
    # rebased).
    cfg_contents = roll_result['picked_roll_details']['spec']
    # TODO(phajdan.jr): remove prefix once new roller is no longer experimental.
    cfg_digest = hashlib.md5('EXPERIMENTAL-' + cfg_contents).hexdigest()

    # We use diff hashes to uniquely identify patchsets within a change.
    self.m.git('commit', '-a', '-m', 'roll recipes.cfg', cwd=workdir)
    # TODO(phajdan.jr): verify that git-show order is stable and includes
    # all info we need to hash.
    diff_result = self.m.git(
        'show', stdout=self.m.raw_io.output(),
        cwd=workdir,
        step_test_data=lambda: self.m.raw_io.test_api.stream_output(
            '-some line\n+some other line\n'))
    diff = diff_result.stdout
    # TODO(phajdan.jr): remove prefix once new roller is no longer experimental.
    diff_digest = hashlib.md5('EXPERIMENTAL-' + diff).hexdigest()

    # Check if we have uploaded this before.
    need_to_upload = False
    rebase = False
    cat_result = self.m.gsutil.cat(
        'gs://recipe-roller-cl-uploads/%s' % cfg_digest,
        stdout=self.m.raw_io.output(),
        stderr=self.m.raw_io.output(),
        ok_ret=(0,1))

    if cat_result.retcode:
      cat_result.presentation.logs['stderr'] = [
          self.m.step.active_result.stderr]
      assert re.search('No URLs matched', cat_result.stderr), (
          'gsutil failed in an unexpected way; see stderr log')
      # We have never uploaded this change before.
      need_to_upload = True

    if not need_to_upload:
      # We have uploaded before, now let's check the diff hash to see if we
      # have uploaded this patchset before.
      change_data = json.loads(cat_result.stdout)
      if change_data['diff_digest'] != diff_digest:
        self.m.git('cl', 'issue', change_data['issue'], cwd=workdir)
        need_to_upload = True
        rebase = True
      cat_result.presentation.links['Issue %s' % change_data['issue']] = (
          change_data['issue_url'])

    if need_to_upload:
      commit_message = (
          'Rebase' if rebase else get_commit_message(roll_result))
      # TODO(phajdan.jr): Send email for all CLs.
      # TODO(phajdan.jr): TBR trivial rolls.
      upload_args = ['--cq-dry-run']
      upload_args.extend(['--bypass-hooks', '-f', '-m', commit_message])
      upload_args.extend([
          '--auth-refresh-token-json=/creds/refresh_tokens/recipe-roller'])
      self.m.git('cl', 'upload', *upload_args, name='git cl upload', cwd=workdir)
      issue_result = self.m.git(
          'cl', 'issue',
          name='git cl issue', stdout=self.m.raw_io.output(),
          cwd=workdir,
          step_test_data=lambda: self.m.raw_io.test_api.stream_output(
              'Issue number: '
              '123456789 (https://codereview.chromium.org/123456789)'))

      m = re.match('Issue number: (\d+) \((\S*)\)', issue_result.stdout.strip())
      if not m:
        self.m.python.failing_step(
            'git cl upload failed', 'git cl issue output "%s" is not valid' %
                                    issue_result.stdout.strip())

      change_data = {
        'issue': m.group(1),
        'issue_url': m.group(2),
        'diff_digest': diff_digest,
      }
      issue_result.presentation.links['Issue %s' % change_data['issue']] = (
          change_data['issue_url'])
      self.m.gsutil.upload(
          self.m.json.input(change_data),
          'recipe-roller-cl-uploads',
          cfg_digest)
