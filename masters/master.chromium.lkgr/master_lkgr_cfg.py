# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import gitiles_poller
from master import master_config
from master.factory import annotator_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumLKGR

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

m_annotator = annotator_factory.AnnotatorFactory()

defaults['category'] = '1lkgr'

# Global scheduler
S(name='chromium_lkgr', branch='lkgr')

################################################################################
## Windows
################################################################################

# ASan/Win bot.
B('Win ASan Release', 'win_asan_rel', scheduler='chromium_lkgr')
F('win_asan_rel', m_annotator.BaseFactory(recipe='chromium'))

# ASan/Win coverage bot.
B('Win ASan Release Coverage', 'win_asan_rel_cov', scheduler='chromium_lkgr')
F('win_asan_rel_cov', m_annotator.BaseFactory(recipe='chromium'))

# ASan/Win media bot.
B('Win ASan Release Media', 'win_asan_rel_media', scheduler='chromium_lkgr')
F('win_asan_rel_media', m_annotator.BaseFactory(recipe='chromium'))

# Win SyzyASan bot.
B('Win SyzyASAN LKGR', 'win_syzyasan_lkgr', 'compile', 'chromium_lkgr')
F('win_syzyasan_lkgr', m_annotator.BaseFactory(recipe='chromium', timeout=7200))

################################################################################
## Mac
################################################################################

asan_mac_gyp = 'asan=1 v8_enable_verify_heap=1 enable_ipc_fuzzer=1 '

B('Mac ASAN Release', 'mac_asan_rel', 'compile', 'chromium_lkgr')
F('mac_asan_rel', m_annotator.BaseFactory(recipe='chromium'))

B('Mac ASAN Release Media', 'mac_asan_rel_media', 'compile', 'chromium_lkgr')
F('mac_asan_rel_media', m_annotator.BaseFactory(recipe='chromium'))

B('Mac ASAN Debug', 'mac_asan_dbg', 'compile', 'chromium_lkgr')
F('mac_asan_dbg', m_annotator.BaseFactory(recipe='chromium'))

################################################################################
## Linux
################################################################################


B('ASAN Release', 'linux_asan_rel', 'compile', 'chromium_lkgr')
F('linux_asan_rel', m_annotator.BaseFactory(recipe='chromium',
    # We started seeing 29 minute links, bug 360158
    timeout=2400))

B('ASAN Release Media', 'linux_asan_rel_media',
  'compile', 'chromium_lkgr')
F('linux_asan_rel_media', m_annotator.BaseFactory(recipe='chromium',
    # We started seeing 29 minute links, bug 360158
    timeout=2400))

B('ASAN Debug', 'linux_asan_dbg', 'compile', 'chromium_lkgr')
F('linux_asan_dbg', m_annotator.BaseFactory(recipe='chromium'))

B('ChromiumOS ASAN Release', 'linux_chromiumos_asan_rel', 'compile',
  'chromium_lkgr')
F('linux_chromiumos_asan_rel', m_annotator.BaseFactory(recipe='chromium',
    # We started seeing 29 minute links, bug 360158
    timeout=2400))

# The build process is described at
# https://sites.google.com/a/chromium.org/dev/developers/testing/addresssanitizer#TOC-Building-with-v8_target_arch-arm
B('ASan Debug (32-bit x86 with V8-ARM)',
  'linux_asan_dbg_ia32_v8_arm',
  'compile', 'chromium_lkgr')
F('linux_asan_dbg_ia32_v8_arm', m_annotator.BaseFactory(recipe='chromium'))

B('ASan Release (32-bit x86 with V8-ARM)',
  'linux_asan_rel_ia32_v8_arm',
  'compile', 'chromium_lkgr')
F('linux_asan_rel_ia32_v8_arm', m_annotator.BaseFactory(recipe='chromium'))

B('ASan Release Media (32-bit x86 with V8-ARM)',
  'linux_asan_rel_media_ia32_v8_arm',
  'compile', 'chromium_lkgr')
F('linux_asan_rel_media_ia32_v8_arm',
  m_annotator.BaseFactory(recipe='chromium'))

# TSan bots.
B('TSAN Release', 'linux_tsan_rel', 'compile', 'chromium_lkgr')
F('linux_tsan_rel', m_annotator.BaseFactory(recipe='chromium'))

B('TSAN Debug', 'linux_tsan_dbg', 'compile', 'chromium_lkgr')
F('linux_tsan_dbg', m_annotator.BaseFactory(recipe='chromium'))

# MSan bots.
B('MSAN Release (no origins)', 'linux_msan_rel_no_origins', 'compile',
  'chromium_lkgr')
F('linux_msan_rel_no_origins', m_annotator.BaseFactory(recipe='chromium'))

B('MSAN Release (chained origins)', 'linux_msan_rel_chained_origins', 'compile',
  'chromium_lkgr')
F('linux_msan_rel_chained_origins', m_annotator.BaseFactory(recipe='chromium'))

# This is a bot that uploads LKGR telemetry harnesses to Google Storage.
B('Telemetry Harness Upload', 'telemetry_harness_upload', None, 'chromium_lkgr')
F('telemetry_harness_upload',
  m_annotator.BaseFactory('perf/telemetry_harness_upload'))

# UBSan bots.
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
