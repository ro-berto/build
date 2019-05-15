# Copyright (c) 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'depot_tools/cipd',
    'depot_tools/git',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/runtime',
    'recipe_engine/step',
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
  build_root = api.path['cache'].join('builder')
  goma_src_dir = build_root.join('goma_src')
  gopath_dir = build_root.join('go')
  # TODO(yyanagisawa): move cipd to cached directory when we confirm it works.
  cipd_root = api.path['start_dir'].join('packages')
  env_prefixes = {
      'GOPATH': [gopath_dir],
      'PATH': SetupExecutables(api, cipd_root) + [gopath_dir.join('bin')],
  }
  env = {
      'GO111MODULE': 'on',
  }

  # Checkout
  # We do not have CI builder, but let me confirm.
  assert api.tryserver.is_tryserver
  ref = api.tryserver.gerrit_change_fetch_ref
  api.git.checkout(repository, ref=ref, dir_path=goma_src_dir)

  with api.context(cwd=api.path['checkout'],
                   env_prefixes=env_prefixes,
                   env=env):
    # Set up modules.
    api.step('list modules',
             ['go', 'list', '-m', 'all'])
    # Generate proto
    api.step('generate proto',
             ['go', 'generate', api.path.join(package_base, 'proto', '...')])
    # Build
    api.step('build',
             ['go', 'install', api.path.join(package_base, 'cmd', '...')])
    # Test
    api.step('test',
             ['go', 'test', '-race', '-cover',
              api.path.join(package_base, '...')])
    # Vet
    api.step('go vet',
             ['go', 'vet', api.path.join(package_base, '...')])
    # Go fmt
    api.step('go fmt',
             ['go', 'fmt', api.path.join(package_base, '...')])
    # Check diff
    api.git('diff', '--exit-code', name='check git diff')


def GenTests(api):
  yield (api.test('goma_server_presubmit') +
         api.platform('linux', 64) +
         api.runtime(is_luci=True, is_experimental=False) +
         api.buildbucket.try_build(
             builder='Goma Server Presubmit',
             change_number=4840,
             patch_set=2))
