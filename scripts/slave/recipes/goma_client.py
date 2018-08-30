# Copyright (c) 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'depot_tools/bot_update',
    'depot_tools/cipd',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
]


def RunSteps(api):
  # 1. Checkout the source
  src_cfg = api.gclient.make_config()
  src_cfg.got_revision_mapping['client'] = 'got_revision'
  soln = src_cfg.solutions.add()
  soln.name = 'client'
  soln.url = 'https://chromium.googlesource.com/infra/goma/client'
  api.gclient.c = src_cfg
  api.bot_update.ensure_checkout(clobber=False, gerrit_no_reset=True)
  api.gclient.runhooks()

  # 2. Build
  build_out_dir = api.path['checkout'].join('out')
  build_target = 'Release'
  build_dir = build_out_dir.join(build_target)

  # 2-1. gn
  gn_args = [
      'is_debug=false',
      'cpu_arch="x64"',
      'dcheck_always_on=true',
      'use_link_time_optimization=false'
  ]
  api.python(
      name='gn',
      script=api.depot_tools.gn_py_path,
      args=[
          '--root=%s' % str(api.path['checkout']),
          'gen',
          build_dir,
          '--args=%s' % ' '.join(gn_args)])

  # 2-2. ninja
  api.step('build', [api.depot_tools.ninja_path, '-C', build_dir])

  # 3. Run test
  with api.context():
    api.python(
        name='tests',
        script=api.path['checkout'].join('build', 'run_unittest.py'),
        args=['--build-dir', build_out_dir,
              '--target', build_target, '--non-stop'])

  # 4. Create archive.
  api.python(
      name='archive',
      script=api.path['checkout'].join('build', 'archive.py'),
      args=['--platform', api.platform.name,
            '--build_dir', build_out_dir,
            '--target_dir', build_target,
            '--dist_dir', api.path['tmp_base']])

  # 5. Build CIPD package.
  # archive.py creates goma-<platform>/ in out/Release.
  root = build_out_dir.join(build_target, 'goma-%s' % api.platform.name)
  pkg_file = api.path['tmp_base'].join('package.cipd')
  pkg_name = 'infra/goma/client/%s' % api.cipd.platform_suffix()
  api.cipd.build(root, pkg_file, pkg_name, install_mode='copy')

  # 6. Register CIPD package if prod.
  revision = api.buildbucket.build.input.gitiles_commit.id
  if revision and api.buildbucket.builder_id.bucket == 'prod':
    api.cipd.register(pkg_name, pkg_file, tags={'git_revision': revision},
                      refs=['latest'])


def GenTests(api):
  for platform in ['linux', 'mac', 'win']:
    for bucket in ['prod', 'luci.goma-client.ci']:
      yield (api.test('goma_client_%s_%s_rel' % (platform, bucket)) +
             api.platform(platform, 64) +
             api.properties(
                 buildername='%s_rel' % platform,
                 mastername='client.goma',
                 buildbucket={
                     'build': {
                         'bucket': bucket,
                         'tags': [
                             ('buildset:commit/git/'
                              '8b3cd40a25a512033cc8c0797e41de9ecfc2432c'),
                             ('buildset:commit/gitiles/'
                              'chromium.googlesource.com/infra/goma/client/'
                              '+/8b3cd40a25a512033cc8c0797e41de9ecfc2432c'),
                             'gitiles_ref:refs/heads/master',
                         ]
                     }
                 }
             ))
