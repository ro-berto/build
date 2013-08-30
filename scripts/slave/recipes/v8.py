# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'gclient',
  'path',
  'platform',
  'properties',
  'python',
]


def GetV8TargetArchitecture(api):
  """Return v8ish architecture names."""
  target_arch = api.properties.get('target_arch', 'intel')
  bits = api.properties.get('bits', None) or api.platform.bits

  if target_arch == 'arm':
    return 'arm'
  elif bits == 64:
    return 'x64'
  else:
    return 'ia32'


def GenSteps(api):
  # Checkout.
  cfg = api.gclient.make_config()
  soln = cfg.solutions.add()
  soln.name = 'v8'
  soln.url = 'http://v8.googlecode.com/svn/branches/bleeding_edge'
  yield api.gclient.checkout(cfg)

  # Hooks.
  gclient_env = {
    'GYP_DEFINES': 'v8_target_arch=%s' % GetV8TargetArchitecture(api),
  }
  yield api.gclient.runhooks(env=gclient_env)

  # Compile.
  compile_tool = api.path.build('scripts', 'slave', 'compile.py')
  build_config = api.properties.get('build_config', 'Release')
  compile_args = [
    '--target', build_config,
    '--build-dir', 'v8',
    '--src-dir', 'v8',
    '--build-tool', 'make',
    'buildbot',
  ]
  if api.properties.get('clobber') is not None:
    compile_args.append('--clobber')
  yield api.python('compile', compile_tool, compile_args)

  # Tests.
  # TODO(machenbach): Implement the tests.

def GenTests(api):
  for bits in [32, 64]:
    for build_config in ['Release', 'Debug']:
      yield '%s%s' % (build_config, bits), {
        'properties': {
          'build_config': build_config,
          'bits': bits,
        },
      }

  for build_config in ['Release', 'Debug']:
    yield 'arm_%s' % (build_config), {
      'properties': {
        'build_config': build_config,
        'target_arch': 'arm',
      },
  }

  yield 'default_platform', {
    'mock': {
      'platform': {
        'name': 'linux',
        'bits': 64,
      }
    },
  }

  yield 'clobber', {
    'properties': {
      'clobber': '',
    },
  }

