# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from contextlib import contextmanager
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from recipe_engine.post_process import (DropExpectation, StatusFailure)
import json
import re

DEPS = [
    'chromium',
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/git',
    'depot_tools/gclient',
    'depot_tools/tryserver',
    'goma',
    'perf_dashboard',
    'recipe_engine/cipd',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
]

REPO_URL = 'https://chromium.googlesource.com/devtools/devtools-frontend.git'


def RunSteps(api):
  _configure(api)

  with _in_builder_cache(api):
    api.bot_update.ensure_checkout()
    _git_clean(api)
    api.gclient.runhooks()

  with _depot_on_path(api):
    api.chromium.ensure_goma()
    server_path = api.path['checkout'].join('back_end', 'CXXDWARFSymbols')
    sever_build_path = server_path.join('build')
    api.step('Ensure build path', ['mkdir', '-p', sever_build_path])
    with api.context(cwd=sever_build_path):
      api.step("Remove cmake cache", ['rm', '-f', 'CMakeCache.txt'])
      cmake(api)
      compile_n_check(api, sever_build_path)


def cmake(api):
  gomacc_path = api.goma.goma_dir.join("gomacc")
  api.step("cmake", [
      "cmake", "-DSYMBOL_SERVER_BUILD_FORMATTERS=OFF",
      "-DLLDB_INCLUDE_TESTS=OFF",
      "-DCMAKE_CXX_COMPILER_LAUNCHER=%s" % gomacc_path,
      "-DCMAKE_C_COMPILER_LAUNCHER=%s" % gomacc_path,
      "-DCMAKE_C_COMPILER=clang", "-DCMAKE_CXX_COMPILER=clang++", "-GNinja",
      ".."
  ])


def compile_n_check(api, sever_build_path):
  with api.step.nest('Compile and check'):
    api.goma.build_with_goma(
        [
            api.depot_tools.autoninja_path, "-v", "-j",
            api.goma.recommended_goma_jobs, 'check-symbol-server'
        ],
        name='ninja',
        ninja_log_outdir=sever_build_path,
        ninja_log_compiler='goma',
        goma_env={
            'GOMA_SERVER_HOST': None,
            'GOMA_RPC_EXTRA_PARAMS': None,
        },
    )


def _configure(api):
  _configure_source(api)
  _configure_build(api)


def _configure_source(api):
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = 'devtools-frontend'
  soln.url = REPO_URL
  soln.revision = api.properties.get('revision', 'HEAD')
  soln.custom_vars['build_symbol_server'] = 'True'
  src_cfg.got_revision_mapping[soln.name] = 'got_revision'
  api.gclient.c = src_cfg


def _configure_build(api):
  build_cfg = api.chromium.make_config()
  build_cfg.build_config_fs = 'Release'
  build_cfg.compile_py.use_autoninja = True
  build_cfg.compile_py.compiler = 'goma'
  api.chromium.c = build_cfg


# TODO(liviurau): remove this temp hack after devtools refactorings that
# involve .gitignore are done
def _git_clean(api):
  with api.context(cwd=api.path['checkout']):
    api.git('clean', '-xf', '--', 'front_end')


@contextmanager
def _in_builder_cache(api):
  cache_dir = api.path['cache'].join('builder')
  with api.context(cwd=cache_dir):
    yield


@contextmanager
def _depot_on_path(api):
  thirdparty_path = api.path['checkout'].join('third_party')
  depot_tools_path = thirdparty_path.join('depot_tools')
  path_prefix = [
      api.chromium.c.compile_py.goma_dir,
      thirdparty_path.join('cmake', 'bin'),
      thirdparty_path.join('protoc'),
      thirdparty_path.join('llvm-build', 'Release+Asserts', 'bin'),
      depot_tools_path,
      thirdparty_path,
      api.chromium.c.compile_py.goma_dir,
  ]
  with api.context(env_prefixes={'PATH': path_prefix}):
    yield


def GenTests(api):
  yield api.test('basic try') + api.properties(
      path_config='generic',
      mastername='tryserver.devtools-frontend',
  ) + api.buildbucket.try_build(
      'devtools',
      'linux',
      git_repo='https://chromium.googlesource.com/chromium/src',
      change_number=91827,
      patch_set=1)
