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
  'polymer',
  'platform',
  'WeakMap',
  'CustomElements',
  'ShadowDOM',
  'HTMLImports',
  'observe-js',
  'NodeBind',
  'TemplateBinding',
  'polymer-expressions',
  'PointerGestures',
  'PointerEvents',
  'tools'
)


def _CheckoutSteps(api):
  url_base = 'https://github.com/Polymer/'

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
  this_repo = api.properties['buildername'].split()[0]
  api.path.set_dynamic_path('checkout', api.path.slave_build(this_repo))

  tmp_path = ''
  tmp_args = []
  if not api.platform.is_win:
    tmp_path = api.path.slave_build('.tmp')
    yield api.path.makedirs('tmp', tmp_path)
    tmp_args = ['--tmp', tmp_path]

  cmd_suffix = ''
  node_env = {}
  if api.platform.is_win:
    cmd_suffix = '.cmd'
    node_env = {
      'PATH': api.path.pathsep.join((
        api.path.join('C:', api.path.sep, 'Program Files (x86)', 'nodejs'),
        api.path.join('C:', api.path.sep, 'Users', 'chrome-bot', 'AppData',
                      'Roaming', 'npm'),
        r'%(PATH)s')),
      'CHROME_BIN':
        api.path.join('C:', api.path.sep, 'Program Files (x86)', 'Google',
                      'Chrome', 'Application', 'chrome.exe'),
      'IE_BIN':
        api.path.join('C:', api.path.sep, 'Program Files', 'Internet Explorer',
                      'iexplore.exe'),
    }

  test_prefix = []
  if api.platform.is_linux:
    test_prefix = ['xvfb-run']

  yield api.git('clean', '-xdf', cwd=api.path.checkout,
                can_fail_build=False)

  yield api.step('update-install', ['npm' + cmd_suffix, 'install'] + tmp_args,
                 cwd=api.path.checkout, env=node_env)

  yield api.step('test', test_prefix + ['grunt' + cmd_suffix,
                 'test-buildbot'], cwd=api.path.checkout,
                 env=node_env, allow_subannotations=True)


def GenTests(api):
  # Test paths and commands on each platform.
  for plat in ('mac', 'linux', 'win'):
    yield (
      api.test('polymer-%s' % plat) +
      api.properties.scheduled(
        repository='https://github.com/Polymer/polymer',
        buildername='polymer %s' % plat,
      ) +
      api.platform.name(plat)
    )

  # Make sure the steps are right for deps-triggered jobs.
  yield (
    api.test('polymer-from-platform') +
    api.properties.scheduled(
      repository='https://github.com/Polymer/platform',
      buildername='polymer linux',
      scheduler='polymer-platform'
    )
  )
