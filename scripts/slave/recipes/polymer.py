# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


DEPS = [
  'gclient',
  'git',
  'path',
  'platform',
  'properties',
  'python',
  'step',
]


REPOS = (
  'CustomElements',
  'HTMLImports',
  'PointerEvents',
  'PointerGestures',
  'ShadowDOM',
  'mdv',
  'platform',
  'polymer',
)


def _CheckoutSteps(api):
  repo_url = api.properties['repository']
  url_base = 'https://github.com/Polymer/'
  assert repo_url.startswith(url_base)
  repo = repo_url[len(url_base):]

  api.path.set_checkout(api.path.slave_build(repo))

  cfg = api.gclient.make_config()
  for name in REPOS:
    soln = cfg.solutions.add()
    soln.name = name
    soln.url = url_base + name + '.git'
    soln.deps_file = ''

  submodule_command = api.python(
      'submodule update', api.path.depot_tools('gclient.py'),
      ['recurse', 'git', 'submodule', 'update', '--init', '--recursive'])

  return (
      api.gclient.checkout(cfg),
      submodule_command
  )


def GenSteps(api):
  yield _CheckoutSteps(api)

  if not api.platform.is_win:
    tmp_path = api.path.slave_build('.tmp')
    yield api.step('mktmp', ['mkdir', '-p', tmp_path])
    npm_path = ['--tmp', tmp_path]
  else:
    npm_path = []

  yield api.step('update-install', ['npm', 'install'] + npm_path,
                 cwd=api.path.checkout())

  test_prefix = ['xvfb-run'] if api.platform.is_linux else []
  yield api.step('test', test_prefix+['grunt', 'test-buildbot'],
                 cwd=api.path.checkout(), allow_subannotations=True)


def GenTests(api):
  for plat in ('mac', 'linux', 'win'):
    yield 'polymer-%s' % plat, {
      'properties': api.properties_scheduled(
          repository='https://github.com/Polymer/polymer'),
      'mock': {
        'platform': {
            'name': plat
        }
      },
    }
