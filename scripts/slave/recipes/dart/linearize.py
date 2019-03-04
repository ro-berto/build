# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json


DEPS = [
  'dart',
  'depot_tools/git',
  'depot_tools/gitiles',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
]


COMMITS_JSON = 'commits.json'


def RunSteps(api):
  repo = api.properties['repo']
  assert(repo)
  commit = api.buildbucket.gitiles_commit
  assert(commit)
  commit_hash = commit.id

  url = 'https://%s/%s' % (commit.host, commit.project)
  commit_log = api.gitiles.commit_log(url, commit_hash)
  commit_url = '%s/+/%s' % (url, commit_hash)
  message = commit_log['message']
  message = '%s\n%s\n' % (message, commit_url)
  commit_author = commit_log['author']
  author = '%s <%s>' % (commit_author['name'], commit_author['email'])
  author_date = commit_author['time']

  api.git.checkout(repo, dir_path=api.path['cleanup'], use_git_cache=True)
  with api.context(cwd=api.path['checkout']):
    json_path = api.path['checkout'].join(COMMITS_JSON)
    commits = {}
    if api.path.exists(json_path):
      result = api.json.read('read old commits', json_path,
          step_test_data=lambda: api.json.test_api.output({
            'another_repo': 'deadbeef'
          })).json
      commits = result.output

    commits[commit.project] = commit_hash

    pretty_json = json.dumps(commits, indent=2, separators=(',', ':'),
                            sort_keys=True)
    api.file.write_text('update commits', json_path, pretty_json)
    api.git('add', json_path)
    api.git('commit', '--author=%s' % author, '--date=%s' % author_date,
        '-m', message)
    api.git('push', repo, 'HEAD:refs/heads/master')


def GenTests(api):
  yield (api.test('base') +
      api.properties.generic(
          repo = 'https://dart.googlesource.com/a/linearized_history.git') +
      api.buildbucket.ci_build(
          git_repo = 'https://dart.googlesource.com/a/repo.git',
          revision = 'deadbeef') +
      api.step_data(
          'commit log: %s' % 'deadbeef',
          api.gitiles.make_commit_test_data('deadbeef', 'Subject\n\nMessage\n',
              new_files=['foo/bar', 'baz/qux'])) +
      api.path.exists(
          api.path['checkout'].join(COMMITS_JSON)))
