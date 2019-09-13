# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from contextlib import contextmanager
import contextlib

from PB.recipes.build.flutter.engine_builder import InputProperties, EngineBuild

DEPS = [
  'build',
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'depot_tools/git',
  'depot_tools/osx_sdk',
  'goma',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/isolated',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'recipe_engine/swarming',
  'recipe_engine/python',
]

GIT_REPO = \
    'https://chromium.googlesource.com/external/github.com/flutter/engine'

PROPERTIES = InputProperties

def Build(api, config, disable_goma, *targets):
  checkout = api.path['cache'].join('builder', 'src')
  build_dir = checkout.join('out/%s' % config)

  if not disable_goma:
    ninja_args = [api.depot_tools.autoninja_path, '-C', build_dir]
    ninja_args.extend(targets)
    api.goma.build_with_goma(
      name='build %s' % ' '.join([config] + list(targets)),
      ninja_command=ninja_args)
  else:
    ninja_args = [api.depot_tools.autoninja_path, '-C', build_dir]
    ninja_args.extend(targets)
    api.step('build %s' % ' '.join([config] + list(targets)), ninja_args)

def RunGN(api, *args):
  checkout = api.path['cache'].join('builder', 'src')
  gn_cmd = ['python', checkout.join('flutter/tools/gn')]
  gn_cmd.extend(args)
  api.step('gn %s' % ' '.join(args), gn_cmd)

def GetCheckout(api, git_url, git_ref):
  git_url = git_url or GIT_REPO
  git_id = git_ref or api.buildbucket.gitiles_commit.id
  git_ref = git_ref or api.buildbucket.gitiles_commit.ref

  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = 'src/flutter'
  soln.url = git_url
  soln.revision = git_id
  src_cfg.parent_got_revision_mapping['parent_got_revision'] = 'got_revision'
  src_cfg.repo_path_map[git_url] = ('src/flutter', git_ref)
  api.gclient.c = src_cfg
  api.gclient.c.got_revision_mapping['src/flutter'] = 'got_engine_revision'
  api.bot_update.ensure_checkout()
  api.gclient.runhooks()

def IsolateOutputs(api, output_files):
  out_dir = api.path['cache'].join('builder', 'src')
  isolated = api.isolated.isolated(out_dir)
  isolated.add_files(output_files)
  return isolated.archive('Archive build outputs')

def RunSteps(api, properties):
  cache_root = api.path['cache'].join('builder')
  with api.context(cwd=cache_root):
    GetCheckout(api, properties.git_url, properties.git_ref)
    api.goma.ensure_goma()

    android_home = cache_root.join('src', 'third_party',
        'android_tools', 'sdk')
    with api.step.nest('Android SDK'):
      api.file.ensure_directory('mkdir licenses', android_home.join('licenses'))
      api.file.write_text('android sdk license',
          android_home.join('licenses', 'android-sdk-license'),
          str(properties.android_sdk_license))
      api.file.write_text('android sdk preview license',
          android_home.join('licenses', 'android-sdk-preview-license'),
          str(properties.android_sdk_preview_license))

    env = {
      'GOMA_DIR': api.goma.goma_dir,
      'ANDROID_HOME': str(android_home)
    }

    output_files = []
    with api.osx_sdk('ios'), api.depot_tools.on_path(), api.context(env=env):
      for build in properties.builds:
        with api.step.nest('build %s (%s)' % (
            build.dir, ','.join(build.targets))):
          RunGN(api, *build.gn_args)
          Build(api, build.dir, build.disable_goma, *build.targets)
          for output_file in build.output_files:
            output_files.append(cache_root.join('src', 'out',
                build.dir, output_file))

    isolated_hash = IsolateOutputs(api, output_files)
    output_props = api.step('Set output properties', None)
    output_props.presentation.properties['isolated_output_hash'] = isolated_hash

def GenTests(api):
  yield (
    api.test('Schedule two builds one with goma and one without') +
    api.platform('linux', 64) +
    api.buildbucket.ci_build(
      builder='Linux Drone',
      git_repo=GIT_REPO,
      project='flutter',
    ) +
    api.properties(
      InputProperties(
        mastername='client.flutter',
        android_sdk_license='sdk_hash',
        android_sdk_preview_license='sdk preview hash',
        builds=[
          EngineBuild(
            disable_goma=True,
            gn_args=['--unoptimized', '--android'],
            dir='android_debug_unopt',
            output_files=['libflutter.so']
          ),
          EngineBuild(
            disable_goma=False,
            gn_args=['--unoptimized'],
            dir='host_debug_unopt',
            output_files=['shell_unittests']
          )
        ]
      )
    )
  )
