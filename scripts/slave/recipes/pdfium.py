# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/gclient',
  'depot_tools/bot_update',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]

from recipe_engine.recipe_api import Property

PROPERTIES = {
  'branch': Property(default=None, kind=str),
  'memory_tool': Property(default=None, kind=str),
}

def _CheckoutSteps(api, memory_tool, branch):
  # Checkout pdfium and its dependencies (specified in DEPS) using gclient
  api.gclient.set_config('pdfium')
  if branch:
    api.gclient.c.solutions[0].revision = 'origin/' + branch
  api.bot_update.ensure_checkout()

  env = {}
  if memory_tool == 'asan':
    env.update({'GYP_DEFINES': 'asan=1'})

  api.gclient.runhooks(env=env)


def _BuildSteps(api):
  # Build sample file using Ninja
  debug_path = api.path['checkout'].join('out', 'Debug')
  api.step('compile with ninja', ['ninja', '-C', debug_path])


def _RunDrMemoryTests(api):
  pdfium_tests_py = str(api.path['checkout'].join('tools',
                                                  'drmemory',
                                                  'scripts',
                                                  'pdfium_tests.py'))
  api.python('unittests', pdfium_tests_py,
             args=['--test', 'pdfium_unittests'],
             cwd=api.path['checkout'])
  api.python('embeddertests', pdfium_tests_py,
             args=['--test', 'pdfium_embeddertests'],
             cwd=api.path['checkout'])
  api.python('javascript tests', pdfium_tests_py,
             args=['--test', 'pdfium_javascript'],
             cwd=api.path['checkout'])
  api.python('pixel tests', pdfium_tests_py,
             args=['--test', 'pdfium_pixel'],
             cwd=api.path['checkout'])
  api.python('corpus tests', pdfium_tests_py,
             args=['--test', 'pdfium_corpus'],
             cwd=api.path['checkout'])


def _RunTests(api, memory_tool):
  if memory_tool == 'drmemory':
    _RunDrMemoryTests(api)
    return

  env = {}
  if memory_tool == 'asan':
    # TODO(ochang): Once PDFium is less leaky, remove the detect_leaks flag.
    env.update({
        'ASAN_OPTIONS': 'detect_leaks=0:allocator_may_return_null=1'})

  unittests_path = str(api.path['checkout'].join('out', 'Debug',
                                                 'pdfium_unittests'))
  if api.platform.is_win:
    unittests_path += '.exe'
  api.step('unittests', [unittests_path], cwd=api.path['checkout'], env=env)

  embeddertests_path = str(api.path['checkout'].join('out', 'Debug',
                                                     'pdfium_embeddertests'))
  if api.platform.is_win:
    embeddertests_path += '.exe'
  api.step('embeddertests', [embeddertests_path],
           cwd=api.path['checkout'],
           env=env)

  javascript_path = str(api.path['checkout'].join('testing', 'tools',
                                                  'run_javascript_tests.py'))
  api.python('javascript tests', javascript_path,
             cwd=api.path['checkout'], env=env)

  pixel_tests_path = str(api.path['checkout'].join('testing', 'tools',
                                                   'run_pixel_tests.py'))
  api.python('pixel tests', pixel_tests_path,
             cwd=api.path['checkout'], env=env)

  corpus_tests_path = str(api.path['checkout'].join('testing', 'tools',
                                                    'run_corpus_tests.py'))
  api.python('corpus tests', corpus_tests_path,
             cwd=api.path['checkout'], env=env)


def RunSteps(api, memory_tool, branch):
  _CheckoutSteps(api, memory_tool, branch)
  _BuildSteps(api)
  with api.step.defer_results():
    _RunTests(api, memory_tool)


def GenTests(api):
  yield (
      api.test('win') +
      api.platform('win', 64) +
      api.properties(mastername="client.pdfium",
                     buildername='windows',
                     slavename="test_slave")
  )
  yield (
      api.test('linux') +
      api.platform('linux', 64) +
      api.properties(mastername="client.pdfium",
                     buildername='linux',
                     slavename="test_slave")
  )
  yield (
      api.test('mac') +
      api.platform('mac', 64) +
      api.properties(mastername="client.pdfium",
                     buildername='mac',
                     slavename="test_slave")
  )

  yield (
      api.test('win_xfa') +
      api.platform('win', 64) +
      api.properties(branch='xfa',
                     mastername="client.pdfium",
                     buildername='windows_xfa',
                     slavename="test_slave")
  )

  yield (
      api.test('linux_xfa') +
      api.platform('linux', 64) +
      api.properties(branch='xfa',
                     mastername="client.pdfium",
                     buildername='linux_xfa',
                     slavename="test_slave")
  )

  yield (
      api.test('mac_xfa') +
      api.platform('mac', 64) +
      api.properties(branch='xfa',
                     mastername="client.pdfium",
                     buildername='mac_xfa',
                     slavename="test_slave")
  )

  yield (
      api.test('linux_asan') +
      api.platform('linux', 64) +
      api.properties(memory_tool='asan',
                     mastername="client.pdfium",
                     buildername='linux_asan',
                     slavename="test_slave")
  )

  yield (
      api.test('drm_win_xfa') +
      api.platform('win', 64) +
      api.properties(branch='xfa',
                     memory_tool='drmemory',
                     mastername="client.pdfium",
                     buildername='drm_win_xfa',
                     slavename="test_slave")
  )

  yield (
      api.test('linux_xfa_asan') +
      api.platform('linux', 64) +
      api.properties(branch='xfa',
                     memory_tool='asan',
                     mastername="client.pdfium",
                     buildername='linux_xfa_asan',
                     slavename="test_slave")
  )
