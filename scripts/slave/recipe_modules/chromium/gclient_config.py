# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import DEPS
CONFIG_CTX = DEPS['gclient'].CONFIG_CTX
ChromiumGitURL = DEPS['gclient'].config.ChromiumGitURL

gclient_api = DEPS['gclient'].api

def ChromiumSrcURL(c):
  return ChromiumGitURL(c, 'chromium', 'src.git')

def mirror_only(c, obj, default=None):
  return obj if c.USE_MIRROR else (default or obj.__class__())

@CONFIG_CTX()
def chromium_bare(c):
  s = c.solutions.add()
  s.name = 'src'
  s.url = ChromiumSrcURL(c)
  s.custom_vars = {}
  m = c.got_revision_reverse_mapping
  m['got_revision'] = 'src'
  m['got_nacl_revision'] = 'src/native_client'
  m['got_swarming_client_revision'] = 'src/tools/swarming_client'
  m['got_v8_revision'] = 'src/v8'
  m['got_angle_revision'] = 'src/third_party/angle'
  m['got_webrtc_revision'] = 'src/third_party/webrtc'
  m['got_buildtools_revision'] = 'src/buildtools'

  p = c.parent_got_revision_mapping
  p['parent_got_revision'] = None
  p['parent_got_angle_revision'] = 'angle_revision'
  p['parent_got_nacl_revision'] = 'nacl_revision'
  p['parent_got_swarming_client_revision'] = 'swarming_revision'
  p['parent_got_v8_revision'] = 'v8_revision'
  p['parent_got_webrtc_revision'] = 'webrtc_revision'

  p = c.patch_projects
  p['angle/angle'] = ('src/third_party/angle', None)
  p['blink'] = ('src/third_party/WebKit', None)
  p['buildtools'] = ('src/buildtools', 'HEAD')
  p['catapult'] = ('src/third_party/catapult', 'HEAD')
  p['flac'] = ('src/third_party/flac', 'HEAD')
  p['icu'] = ('src/third_party/icu', 'HEAD')
  p['pdfium'] = ('src/third_party/pdfium', 'HEAD')
  p['skia'] = ('src/third_party/skia', 'HEAD')
  p['v8'] = ('src/v8', 'HEAD')
  p['v8/v8'] = ('src/v8', 'HEAD')
  p['webrtc'] = ('src/third_party/webrtc', 'HEAD')

@CONFIG_CTX(includes=['chromium_bare'])
def chromium_empty(c):
  c.solutions[0].deps_file = ''  # pragma: no cover

@CONFIG_CTX(includes=['chromium_bare'])
def chromium(c):
  s = c.solutions[0]
  s.custom_deps = mirror_only(c, {})

@CONFIG_CTX(includes=['chromium'])
def chromium_lkcr(c):
  s = c.solutions[0]
  s.revision = 'origin/lkcr'

@CONFIG_CTX(includes=['chromium'])
def chromium_lkgr(c):
  s = c.solutions[0]
  s.revision = 'origin/lkgr'

@CONFIG_CTX(includes=['chromium_bare'])
def android_bare(c):
  # We inherit from chromium_bare to get the got_revision mapping.
  # NOTE: We don't set a specific got_revision mapping for src/repo.
  del c.solutions[0]
  c.got_revision_reverse_mapping['got_src_revision'] = 'src'
  del c.got_revision_reverse_mapping['got_revision']
  s = c.solutions.add()
  s.deps_file = '.DEPS.git'

@CONFIG_CTX(includes=['chromium'])
def blink(c):
  c.solutions[0].revision = 'HEAD'
  del c.solutions[0].custom_deps
  c.revisions['src/third_party/WebKit'] = 'HEAD'

# TODO(phajdan.jr): Move to proper repo and add coverage.
@CONFIG_CTX(includes=['chromium'])
def blink_merged(c):  # pragma: no cover
  c.solutions[0].url = \
      'https://chromium.googlesource.com/playground/chromium-blink-merge.git'

@CONFIG_CTX(includes=['chromium', 'chrome_internal'])
def ios(c):
  c.target_os.add('ios')

@CONFIG_CTX(includes=['chromium'])
def show_v8_revision(c):
  # Have the V8 revision appear in the web UI instead of Chromium's.
  c.got_revision_reverse_mapping['got_cr_revision'] = 'src'
  c.got_revision_reverse_mapping['got_revision'] = 'src/v8'
  # TODO(machenbach): Retain old behavior for now  and switch in separate CL.
  del c.got_revision_reverse_mapping['got_v8_revision']
  # Needed to get the testers to properly sync the right revision.
  c.parent_got_revision_mapping['parent_got_revision'] = 'got_revision'

@CONFIG_CTX(includes=['chromium'])
def v8_bleeding_edge_git(c):
  c.solutions[0].revision = 'HEAD'
  # TODO(machenbach): If bot_update is activated for all v8-chromium bots
  # and there's no gclient fallback, then the following line can be removed.
  c.solutions[0].custom_vars['v8_branch'] = 'branches/bleeding_edge'
  c.revisions['src/v8'] = 'HEAD'

@CONFIG_CTX()
def v8_canary(c):
  c.revisions['src/v8'] = 'origin/canary'

@CONFIG_CTX(includes=['chromium', 'chrome_internal'])
def perf(c):
  s = c.solutions[0]
  s.managed = False
  needed_components_internal = [
    "src/data/page_cycler",
  ]
  for key in needed_components_internal:
    del c.solutions[1].custom_deps[key]
  c.solutions[1].managed = False

@CONFIG_CTX(includes=['chromium', 'chrome_internal'])
def chromium_perf(c):
  pass

@CONFIG_CTX(includes=['chromium_perf', 'android'])
def chromium_perf_android(c):
  pass

@CONFIG_CTX(includes=['chromium'])
def chromium_skia(c):
  c.solutions[0].revision = 'HEAD'
  del c.solutions[0].custom_deps
  c.revisions['src/third_party/skia'] = (
      gclient_api.RevisionFallbackChain('origin/master'))
  c.got_revision_reverse_mapping['got_chromium_revision'] = 'src'
  c.got_revision_reverse_mapping['got_revision'] = 'src/third_party/skia'
  c.parent_got_revision_mapping['parent_got_revision'] = 'got_revision'

@CONFIG_CTX(includes=['chromium'])
def chromium_webrtc(c):
  c.got_revision_reverse_mapping['got_libvpx_revision'] = (
      'src/third_party/libvpx/source')

@CONFIG_CTX(includes=['chromium_webrtc'])
def chromium_webrtc_tot(c):
  """Configures WebRTC ToT revision for Chromium src/third_party/webrtc.

  Sets up ToT instead of the DEPS-pinned revision for WebRTC.
  This is used for some bots to provide data about which revisions are green to
  roll into Chromium.
  """
  c.revisions['src'] = 'HEAD'
  c.revisions['src/third_party/webrtc'] = 'HEAD'

  # Have the WebRTC revision appear in the web UI instead of Chromium's.
  # This is also important for set_component_rev to work, since got_revision
  # will become a WebRTC revision instead of Chromium.
  c.got_revision_reverse_mapping['got_cr_revision'] = 'src'
  c.got_revision_reverse_mapping['got_revision'] = 'src/third_party/webrtc'
  # TODO(machenbach): Retain old behavior for now and switch in separate CL.
  del c.got_revision_reverse_mapping['got_webrtc_revision']

  # Needed to get the testers to properly sync the right revision.
  c.parent_got_revision_mapping['parent_got_revision'] = 'got_revision'
  c.parent_got_revision_mapping['parent_got_webrtc_revision'] = (
      'got_webrtc_revision')

@CONFIG_CTX()
def webrtc_test_resources(c):
  """Add webrtc.DEPS solution for test resources and tools.

  The webrtc.DEPS solution pulls in additional resources needed for running
  WebRTC-specific test setups in Chromium.
  """
  s = c.solutions.add()
  s.name = 'webrtc.DEPS'
  s.url = ChromiumGitURL(c, 'chromium', 'deps', 'webrtc', 'webrtc.DEPS')
  s.deps_file = 'DEPS'

@CONFIG_CTX(includes=['chromium'])
def chromedriver(c):
  """Add Selenium Java tests to the gclient solution."""
  c.solutions[0].custom_deps[
      'src/chrome/test/chromedriver/third_party/java_tests'] = (
          ChromiumGitURL(c, 'chromium', 'deps', 'webdriver'))
