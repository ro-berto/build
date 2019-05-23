# Copyright (c) 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'depot_tools/cipd',
    'recipe_engine/buildbucket',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/runtime',
    'goma_server',
]

GO_VERSION = 'version:1.12.5'
PROTOC_VERSION = 'protobuf_version:v3.6.1'


# TODO(yyanagisawa): install go and protoc from the script in source.
#                    The compiler should be matched with the source, and the
#                    script in the source code should install them like clang in
#                    Chromium build.
def SetupExecutables(api, pkg_dir):
  """Set up go and protoc to run the script.

  Args:
    pkg_dir: a root directory to install cipd packages.

  Returns:
    a list of paths.
  """
  api.cipd.ensure(pkg_dir, {
      'infra/go/${platform}': GO_VERSION,
      'infra/tools/protoc/${platform}': PROTOC_VERSION,
  })
  return [pkg_dir, api.path.join(pkg_dir, 'bin')]


def RunSteps(api):
  repository = 'https://chromium.googlesource.com/infra/goma/server'
  package_base = 'go.chromium.org/goma/server'
  # TODO(yyanagisawa): move cipd to cached directory when we confirm it works.
  cipd_root = api.path['start_dir'].join('packages')
  api.goma_server.BuildAndTest(repository, package_base,
                               SetupExecutables(api, cipd_root))


def GenTests(api):
  yield (api.test('goma_server_presubmit') +
         api.platform('linux', 64) +
         api.runtime(is_luci=True, is_experimental=False) +
         api.buildbucket.try_build(
             builder='Goma Server Presubmit',
             change_number=4840,
             patch_set=2))
