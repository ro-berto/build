# Copyright (c) 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'depot_tools/osx_sdk',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/cipd',
    'recipe_engine/path',
    'recipe_engine/platform',
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

  with api.osx_sdk('mac'):
    # 2-1. gn
    gn_args = ['is_debug=false', 'enable_revision_check=true']
    assert api.platform.bits == 64
    if api.platform.arch == 'arm':
      gn_args += ['target_cpu="arm64"']
    else:
      gn_args += ['cpu_arch="x64"']

    if api.tryserver.is_tryserver:
      gn_args.append('dcheck_always_on=true')
      gn_args.append('use_link_time_optimization=false')
    else:
      gn_args.append('use_link_time_optimization=true')
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
    # Not on arm because we're cross-building and the intel builder can't run
    # arm test binaries.
    if api.platform.arch != 'arm':
      api.python(
          name='tests',
          script=api.path['checkout'].join('build', 'run_unittest.py'),
          args=['--build-dir', build_out_dir,
                '--target', build_target, '--non-stop'])

  # 4. Create archive.
  platform = api.platform.name
  if api.platform.arch == 'arm':
    platform += '-arm64'
  api.python(
      name='archive',
      script=api.path['checkout'].join('build', 'archive.py'),
      args=['--platform', platform,
            '--build_dir', build_out_dir,
            '--target_dir', build_target,
            '--dist_dir', api.path['tmp_base']])

  # 5. Build CIPD package.
  # archive.py creates goma-<platform>/ in out/Release.
  root = build_out_dir.join(build_target, 'goma-%s' % platform)
  pkg_file = api.path['tmp_base'].join('package.cipd')
  tag = '${platform}' if api.platform.arch == 'intel' else platform
  pkg_name = 'infra/goma/client/' + tag
  api.cipd.build(root, pkg_file, pkg_name, install_mode='copy')

  # 6. Register CIPD package if prod.
  revision = api.buildbucket.build.input.gitiles_commit.id
  if revision and api.buildbucket.build.builder.bucket == 'prod':
    api.cipd.register(pkg_name, pkg_file, tags={'git_revision': revision},
                      refs=['latest'])


def GenTests(api):
  for platform in ['linux', 'mac', 'win']:
    archs = ['intel']
    if platform == 'mac':
      archs += ['arm']
    for arch in archs:
      bot_name = platform
      if arch != 'intel':
        bot_name += '_' + arch
      yield api.test(
          'goma_client_try_%s_rel' % bot_name,
          api.platform(platform, 64, arch),
          api.buildbucket.try_build(
              builder='%s_rel' % platform,
              git_repo='chromium.googlesource.com/infra/goma/client',
              change_number=456789,
              patch_set=12),
      )
      for bucket in ['prod', 'luci.goma-client.ci']:
        yield api.test(
            'goma_client_%s_%s_rel' % (bot_name, bucket),
            api.platform(platform, 64, arch),
            api.buildbucket.ci_build(
                bucket=bucket,
                git_repo='chromium.googlesource.com/infra/goma/client',
                revision='8b3cd40a25a512033cc8c0797e41de9ecfc2432c'),
        )
