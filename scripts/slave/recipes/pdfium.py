# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'gclient',
  'path',
  'platform',
  'properties',
  'python',
  'step',
]

from recipe_engine.recipe_api import Property

PROPERTIES = {
  'drmemory': Property(default=False, kind=bool),
}

def _CheckoutSteps(api):
  # Checkout pdfium and its dependencies (specified in DEPS) using gclient
  api.gclient.set_config('pdfium')
  branch = api.properties.get('branch')
  if branch:
    api.gclient.c.solutions[0].revision = 'origin/' + branch
  api.gclient.checkout()
  api.gclient.runhooks()


def _BuildSteps(api):
  # Build sample file using Ninja
  debug_path = api.path['checkout'].join('out', 'Debug')
  api.step('compile with ninja', ['ninja', '-C', debug_path])


def _RunTests(api):
  drmemory = api.properties.get('drmemory')
  pdfium_tests_py = str(api.path['checkout'].join('tools',
                                                  'drmemory',
                                                  'scripts',
                                                  'pdfium_tests.py'))
  if drmemory:
    api.python('unittests', pdfium_tests_py,
               args=['--test', 'pdfium_unittests'],
               cwd=api.path['checkout'])
  else:
    unittests_path = str(api.path['checkout'].join('out', 'Debug',
                                                   'pdfium_unittests'))
    if api.platform.is_win:
      unittests_path += '.exe'
    api.step('unittests', [unittests_path], cwd=api.path['checkout'])

  if drmemory:
    api.python('embeddertests', pdfium_tests_py,
               args=['--test', 'pdfium_embeddertests'],
               cwd=api.path['checkout'])
  else:
    embeddertests_path = str(api.path['checkout'].join('out', 'Debug',
                                                       'pdfium_embeddertests'))
    if api.platform.is_win:
      embeddertests_path += '.exe'
    api.step('embeddertests', [embeddertests_path],
             cwd=api.path['checkout'])

  if drmemory:
    api.python('javascript tests', pdfium_tests_py,
               args=['--test', 'pdfium_javascript'],
               cwd=api.path['checkout'])
  else:
    javascript_path = str(api.path['checkout'].join('testing', 'tools',
                                                    'run_javascript_tests.py'))
    api.python('javascript tests', javascript_path, cwd=api.path['checkout'])

  if drmemory:
    api.python('pixel tests', pdfium_tests_py,
               args=['--test', 'pdfium_pixel'],
               cwd=api.path['checkout'])
  else:
    pixel_tests_path = str(api.path['checkout'].join('testing', 'tools',
                                                     'run_pixel_tests.py'))
    api.python('pixel tests', pixel_tests_path, cwd=api.path['checkout'])

  if drmemory:
    api.python('corpus tests', pdfium_tests_py,
               args=['--test', 'pdfium_corpus'],
               cwd=api.path['checkout'])
  else:
    corpus_tests_path = str(api.path['checkout'].join('testing', 'tools',
                                                      'run_corpus_tests.py'))
    api.python('corpus tests', corpus_tests_path, cwd=api.path['checkout'])


def RunSteps(api):
  _CheckoutSteps(api)
  _BuildSteps(api)
  with api.step.defer_results():
    _RunTests(api)


def GenTests(api):
  yield api.test('win') + api.platform('win', 64)
  yield api.test('linux') + api.platform('linux', 64)
  yield api.test('mac') + api.platform('mac', 64)

  yield (api.test('win_xfa') + api.platform('win', 64) +
         api.properties(branch='xfa'))
  yield (api.test('linux_xfa') + api.platform('linux', 64) +
         api.properties(branch='xfa'))
  yield (api.test('mac_xfa') + api.platform('mac', 64) +
         api.properties(branch='xfa'))
  yield (api.test('drm_win_xfa') + api.platform('win', 64) +
         api.properties(branch='xfa', drmemory=True))
