# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import gitiles_poller
from master import master_config
from master.factory import annotator_factory
from master.factory import chromium_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumLKGR

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

def win_out(): return chromium_factory.ChromiumFactory('src/out', 'win32')
def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')
def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')

m_annotator = annotator_factory.AnnotatorFactory()

defaults['category'] = '1lkgr'

# Global scheduler
S(name='chromium_lkgr', branch='lkgr')

################################################################################
## Windows
################################################################################

# ASan/Win supports neither the component build nor NaCL at the moment.
asan_win_gyp = ('asan=1 component=static_library enable_ipc_fuzzer=1 '
                'v8_enable_verify_heap=1')

# Clang is not stable enough on Windows to use a gatekeeper yet.
B('Win ASan Release', 'win_asan_rel', scheduler='chromium_lkgr')
F('win_asan_rel', win_out().ChromiumASANFactory(
    compile_timeout=8*3600,  # We currently use a VM, which is extremely slow.
    clobber=True,
    options=['--build-tool=ninja', '--', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_win_gyp},
       'use_mb': True,
    }))

# ASan/Win coverage bot.
B('Win ASan Release Coverage', 'win_asan_rel_cov', scheduler='chromium_lkgr')
F('win_asan_rel_cov', win_out().ChromiumASANFactory(
    compile_timeout=8*3600,  # We currently use a VM, which is extremely slow.
    clobber=True,
    options=['--build-tool=ninja', '--', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan-coverage',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {
           'GYP_DEFINES': asan_win_gyp + ' sanitizer_coverage=edge',
       },
       'use_mb': True,
    }))


# ASan/Win supports neither the component build nor NaCL at the moment.
media_gyp = (' proprietary_codecs=1 ffmpeg_branding=Chrome')
asan_win_media_gyp = asan_win_gyp + media_gyp

# Clang is not stable enough on Windows to use a gatekeeper yet.
B('Win ASan Release Media', 'win_asan_rel_media',
   scheduler='chromium_lkgr')
F('win_asan_rel_media', win_out().ChromiumASANFactory(
    compile_timeout=8*3600,  # We currently use a VM, which is extremely slow.
    clobber=True,
    options=['--build-tool=ninja', '--', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan',
       'gs_bucket': 'gs://chrome-test-builds/media',
       'gclient_env': {'GYP_DEFINES': asan_win_media_gyp},
       'use_mb': True,
    }))

# Win SyzyASan bot.
B('Win SyzyASAN LKGR', 'win_syzyasan_lkgr', 'compile', 'chromium_lkgr')
F('win_syzyasan_lkgr', m_annotator.BaseFactory(recipe='chromium', timeout=7200))

################################################################################
## Mac
################################################################################

asan_mac_gyp = 'asan=1 v8_enable_verify_heap=1 enable_ipc_fuzzer=1 '

B('Mac ASAN Release', 'mac_asan_rel', 'compile', 'chromium_lkgr')
F('mac_asan_rel', linux().ChromiumASANFactory(
    clobber=True,
    options=['--compiler=goma-clang', '--', '-target', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_mac_gyp},
       'use_mb': True,
    }))

B('Mac ASAN Release Media', 'mac_asan_rel_media', 'compile', 'chromium_lkgr')
F('mac_asan_rel_media', linux().ChromiumASANFactory(
    clobber=True,
    options=['--compiler=goma-clang', '--', '-target', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan',
       'gs_bucket': 'gs://chrome-test-builds/media',
       'gclient_env': {'GYP_DEFINES': asan_mac_gyp + media_gyp},
       'use_mb': True,
    }))

B('Mac ASAN Debug', 'mac_asan_dbg', 'compile', 'chromium_lkgr')
F('mac_asan_dbg', linux().ChromiumASANFactory(
    clobber=True,
    target='Debug',
    options=['--compiler=goma-clang', '--', '-target', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_mac_gyp +
                                      ' component=static_library '},
       'use_mb': True,
    }))

################################################################################
## Linux
################################################################################

asan_rel_gyp = ('asan=1 lsan=1 sanitizer_coverage=edge '
                'v8_enable_verify_heap=1 enable_ipc_fuzzer=1 ')

B('ASAN Release', 'linux_asan_rel', 'compile', 'chromium_lkgr')
F('linux_asan_rel', linux().ChromiumASANFactory(
    compile_timeout=2400,  # We started seeing 29 minute links, bug 360158
    clobber=True,
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_rel_gyp},
       'use_mb': True,
    }))

linux_media_gyp = (' proprietary_codecs=1 ffmpeg_branding=ChromeOS')
B('ASAN Release Media', 'linux_asan_rel_media',
  'compile', 'chromium_lkgr')
F('linux_asan_rel_media', linux().ChromiumASANFactory(
    compile_timeout=2400,  # We started seeing 29 minute links, bug 360158
    clobber=True,
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan',
       'gs_bucket': 'gs://chrome-test-builds/media',
       'gclient_env': {'GYP_DEFINES': asan_rel_gyp +
                       linux_media_gyp},
       'use_mb': True,
    }))

asan_rel_sym_gyp = ('asan=1 lsan=1 sanitizer_coverage=edge '
                    'v8_enable_verify_heap=1 enable_ipc_fuzzer=1 '
                    'release_extra_cflags="-O1 -fno-inline-functions '
                    '-fno-inline" ')

B('ASAN Release (symbolized)', 'linux_asan_rel_sym', 'compile', 'chromium_lkgr')
F('linux_asan_rel_sym', linux().ChromiumASANFactory(
    clobber=True,
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan-symbolized',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_rel_sym_gyp},
       'use_mb': True,
    }))

asan_debug_gyp = ('asan=1 lsan=1 sanitizer_coverage=edge enable_ipc_fuzzer=1 ')

B('ASAN Debug', 'linux_asan_dbg', 'compile', 'chromium_lkgr')
F('linux_asan_dbg', linux().ChromiumASANFactory(
    clobber=True,
    target='Debug',
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_debug_gyp},
       'use_mb': True,
    }))

asan_chromiumos_rel_gyp = ('%s chromeos=1' % asan_rel_gyp)

B('ChromiumOS ASAN Release', 'linux_chromiumos_asan_rel', 'compile',
  'chromium_lkgr')
F('linux_chromiumos_asan_rel', linux().ChromiumASANFactory(
    compile_timeout=2400,  # We started seeing 29 minute links, bug 360158
    clobber=True,
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan',
       'cf_archive_subdir_suffix': 'chromeos',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_chromiumos_rel_gyp},
       'use_mb': True,
    }))

asan_ia32_v8_arm = ('asan=1 sanitizer_coverage=edge disable_nacl=1 '
                    'v8_target_arch=arm host_arch=x86_64 target_arch=ia32 '
                    'v8_enable_verify_heap=1 enable_ipc_fuzzer=1 ')

asan_ia32_v8_arm_rel_sym = ('%s release_extra_cflags="-O1 '
                            '-fno-inline-functions -fno-inline"' %
                            asan_ia32_v8_arm)
asan_ia32_v8_arm_rel = asan_ia32_v8_arm

# The build process is described at
# https://sites.google.com/a/chromium.org/dev/developers/testing/addresssanitizer#TOC-Building-with-v8_target_arch-arm
B('ASan Debug (32-bit x86 with V8-ARM)',
  'linux_asan_dbg_ia32_v8_arm',
  'compile', 'chromium_lkgr')
F('linux_asan_dbg_ia32_v8_arm', linux().ChromiumASANFactory(
    clobber=True,
    target='Debug',
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_subdir_suffix': 'v8-arm',
       'cf_archive_name': 'asan-v8-arm',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_ia32_v8_arm},
       'use_mb': True,
    }))

B('ASan Release (32-bit x86 with V8-ARM)',
  'linux_asan_rel_ia32_v8_arm',
  'compile', 'chromium_lkgr')
F('linux_asan_rel_ia32_v8_arm', linux().ChromiumASANFactory(
    clobber=True,
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_subdir_suffix': 'v8-arm',
       'cf_archive_name': 'asan-v8-arm',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_ia32_v8_arm_rel},
       'use_mb': True,
    }))

B('ASan Release Media (32-bit x86 with V8-ARM)',
  'linux_asan_rel_media_ia32_v8_arm',
  'compile', 'chromium_lkgr')
F('linux_asan_rel_media_ia32_v8_arm', linux().ChromiumASANFactory(
    clobber=True,
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_subdir_suffix': 'v8-arm',
       'cf_archive_name': 'asan-v8-arm',
       'gs_bucket': 'gs://chrome-test-builds/media',
       'gclient_env': {'GYP_DEFINES': asan_ia32_v8_arm_rel + linux_media_gyp},
       'use_mb': True,
    }))

B('ASan Release (32-bit x86 with V8-ARM, symbolized)',
  'linux_asan_rel_sym_ia32_v8_arm',
  'compile', 'chromium_lkgr')
F('linux_asan_rel_sym_ia32_v8_arm', linux().ChromiumASANFactory(
    clobber=True,
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_subdir_suffix': 'v8-arm',
       'cf_archive_name': 'asan-symbolized-v8-arm',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_ia32_v8_arm_rel_sym},
       'use_mb': True,
    }))

# The build process for TSan is described at
# http://dev.chromium.org/developers/testing/threadsanitizer-tsan-v2
tsan_gyp = ('tsan=1 disable_nacl=1 '
            'debug_extra_cflags="-gline-tables-only" ')

B('TSAN Release', 'linux_tsan_rel', 'compile', 'chromium_lkgr')
F('linux_tsan_rel', linux().ChromiumFactory(
    clobber=True,
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'tsan',
       'gs_bucket': 'gs://chromium-browser-tsan',
       'gs_acl': 'public-read',
       'tsan': True,
       'gclient_env': {'GYP_DEFINES': tsan_gyp},
       'use_mb': True,
    }))

B('TSAN Debug', 'linux_tsan_dbg', 'compile', 'chromium_lkgr')
F('linux_tsan_dbg', linux().ChromiumFactory(
    clobber=True,
    target='Debug',
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'tsan',
       'gs_bucket': 'gs://chromium-browser-tsan',
       'gs_acl': 'public-read',
       'tsan': True,
       'gclient_env': {'GYP_DEFINES': tsan_gyp},
       'use_mb': True,
    }))

# The build process for MSan is described at
# http://dev.chromium.org/developers/testing/memorysanitizer
msan_gyp = ('msan=1 sanitizer_coverage=edge '
            'use_prebuilt_instrumented_libraries=1 ')

B('MSAN Release (no origins)', 'linux_msan_rel_no_origins', 'compile',
  'chromium_lkgr')
F('linux_msan_rel_no_origins', linux().ChromiumFactory(
    clobber=True,
    target='Release',
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'msan-no-origins',
       'gs_bucket': 'gs://chromium-browser-msan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': msan_gyp + 'msan_track_origins=0 '},
       'use_mb': True,
    }))

B('MSAN Release (chained origins)', 'linux_msan_rel_chained_origins', 'compile',
  'chromium_lkgr')
F('linux_msan_rel_chained_origins', linux().ChromiumFactory(
    clobber=True,
    target='Release',
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'msan-chained-origins',
       'gs_bucket': 'gs://chromium-browser-msan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': msan_gyp + 'msan_track_origins=2 '},
       'use_mb': True,
    }))

# This is a bot that uploads LKGR telemetry harnesses to Google Storage.
B('Telemetry Harness Upload', 'telemetry_harness_upload', None, 'chromium_lkgr')
F('telemetry_harness_upload',
  m_annotator.BaseFactory('perf/telemetry_harness_upload'))


B('UBSan Release', 'linux_ubsan_rel', 'compile', 'chromium_lkgr')
# UBSan builds very slowly with edge level coverage
F('linux_ubsan_rel', m_annotator.BaseFactory(recipe='chromium', timeout=5400))

B('UBSan vptr Release', 'linux_ubsan_vptr_rel', 'compile', 'chromium_lkgr')
F('linux_ubsan_vptr_rel', m_annotator.BaseFactory(recipe='chromium'))

def Update(_config, active_master, c):
  lkgr_poller = gitiles_poller.GitilesPoller(
      'https://chromium.googlesource.com/chromium/src',
      branches=['lkgr'])
  c['change_source'].append(lkgr_poller)
  return helper.Update(c)
