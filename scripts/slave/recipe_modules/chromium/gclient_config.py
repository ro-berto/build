# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import DEPS
CONFIG_CTX = DEPS['gclient'].CONFIG_CTX
ChromiumGitURL = DEPS['gclient'].config.ChromiumGitURL
ChromeInternalGitURL = DEPS['gclient'].config.ChromeInternalGitURL

gclient_api = DEPS['gclient'].api

def mirror_only(c, obj, default=None):
  return obj if c.USE_MIRROR else (default or obj.__class__())

@CONFIG_CTX()
def chromium_bare(c):
  s = c.solutions.add()
  s.name = 'src'
  s.url = ChromiumGitURL(c, 'chromium', 'src.git')
  s.custom_vars = {
    # We always want the bots to fetch the dependencies needed to
    # run the telemetry tests, regardless of whether they are needed or not
    # (this makes things simpler and more consistent).
    'checkout_telemetry_dependencies': 'True',
  }
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

  p = c.repo_path_map
  p['https://chromium.googlesource.com/chromium/src'] = ('src', None)
  p['https://chromium.googlesource.com/angle/angle'] = (
      'src/third_party/angle', None)
  p['https://chromium.googlesource.com/chromium/buildtools'] = (
      'src/buildtools', 'HEAD')
  p['https://chromium.googlesource.com/catapult'] = (
      'src/third_party/catapult', 'HEAD')
  p['https://chromium.googlesource.com/chromium/deps/flac'] = (
      'src/third_party/flac', 'HEAD')
  p['https://chromium.googlesource.com/chromium/deps/icu'] = (
      'src/third_party/icu', 'HEAD')
  p['https://pdfium.googlesource.com/pdfium'] = (
      'src/third_party/pdfium', 'HEAD')
  p['https://skia.googlesource.com/skia'] = ('src/third_party/skia', 'HEAD')
  p['https://chromium.googlesource.com/v8/v8'] = ('src/v8', 'HEAD')
  p['https://webrtc.googlesource.com/src'] = ('src/third_party/webrtc', 'HEAD')

@CONFIG_CTX(includes=['chromium_bare'])
def chromium_empty(c):
  c.solutions[0].deps_file = ''  # pragma: no cover

@CONFIG_CTX(includes=['chromium_bare'])
def chromium(c):
  s = c.solutions[0]
  s.custom_deps = mirror_only(c, {})

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

@CONFIG_CTX(includes=['chromium'])
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
def v8_canary(c):
  c.revisions['src/v8'] = 'origin/canary'

@CONFIG_CTX(includes=['chromium'])
def v8_tot(c):
  c.revisions['src/v8'] = 'HEAD'

@CONFIG_CTX()
def chromeos(c):
  c.target_os.add('chromeos')

@CONFIG_CTX(includes=['chromeos'])
def chromeos_amd64_generic(c):
  c.solutions[0].custom_vars['cros_board'] = 'amd64-generic'

@CONFIG_CTX(includes=['chromeos'])
def chromeos_daisy(c):  # pragma: no cover
  c.solutions[0].custom_vars['cros_board'] = 'daisy'

@CONFIG_CTX(includes=['chromeos'])
def chromeos_kevin(c):  # pragma: no cover
  c.solutions[0].custom_vars['cros_board'] = 'kevin'

@CONFIG_CTX()
def fuchsia(c):
  c.target_os.add('fuchsia')

@CONFIG_CTX()
def win(c):
  c.target_os.add('win')

@CONFIG_CTX(includes=['chrome_internal'])
def perf(c):
  s = c.solutions[0]
  s.managed = False
  needed_components_internal = [
    "src/data/page_cycler",
  ]
  for key in needed_components_internal:
    s.custom_deps.pop(key, None)

@CONFIG_CTX(includes=['chrome_internal'])
def chromium_perf(_):
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

@CONFIG_CTX(includes=['chromium_no_telemetry_dependencies'])
def chromium_webrtc_tot(c):
  """Configures WebRTC ToT revision for Chromium src/third_party/webrtc.

  Sets up ToT instead of the DEPS-pinned revision for WebRTC.
  This is used for some bots to provide data about which revisions are green to
  roll into Chromium.
  """
  c.revisions['src'] = 'HEAD'
  c.revisions['src/third_party/webrtc'] = 'HEAD'

  c.got_revision_reverse_mapping['got_libvpx_revision'] = (
      'src/third_party/libvpx/source')

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
  s.url = 'https://webrtc.googlesource.com/webrtc.DEPS'
  s.deps_file = 'DEPS'

@CONFIG_CTX(includes=['chromium'])
def chromedriver(c):
  """Add Selenium Java tests to the gclient solution."""
  c.solutions[0].custom_deps[
      'src/chrome/test/chromedriver/third_party/java_tests'] = (
          ChromiumGitURL(c, 'chromium', 'deps', 'webdriver'))

# TODO(phajdan.jr): Move to proper repo and add coverage.
@CONFIG_CTX()
def angle_top_of_tree(c):  # pragma: no cover
  """Configures the top-of-tree ANGLE in a Chromium checkout.

  Sets up ToT instead of the DEPS-pinned revision for ANGLE.
  """
  # TODO(tandrii): I think patch_projects in bare_chromium fixed this.
  c.revisions['src/third_party/angle'] = 'HEAD'

# TODO(phajdan.jr): Move to proper repo and add coverage.
@CONFIG_CTX()
def valgrind(c):  # pragma: no cover
  """Add Valgrind binaries to the gclient solution."""
  c.solutions[0].custom_deps['src/third_party/valgrind'] = \
    ChromiumGitURL(c, 'chromium', 'deps', 'valgrind', 'binaries')

@CONFIG_CTX()
def ndk_next(c):
  c.revisions['src/third_party/android_ndk'] = 'origin/next'

@CONFIG_CTX(includes=['chromium'])
def chrome_internal(c):
  c.solutions[0].custom_vars['checkout_src_internal'] = 'True'
  c.solutions[0].custom_vars['checkout_google_internal'] = 'True'
  # Remove some things which are generally not needed
  c.solutions[0].custom_deps = {
    "src/data/autodiscovery" : None,
    "src/data/page_cycler" : None,
    "src/tools/grit/grit/test/data" : None,
    "src/chrome/test/data/perf/frame_rate/private" : None,
    "src/data/mozilla_js_tests" : None,
    "src/chrome/test/data/firefox2_profile/searchplugins" : None,
    "src/chrome/test/data/firefox2_searchplugins" : None,
    "src/chrome/test/data/firefox3_profile/searchplugins" : None,
    "src/chrome/test/data/firefox3_searchplugins" : None,
    "src/chrome/test/data/ssl/certs" : None,
    "src/data/mach_ports" : None,
    "src/data/esctf" : None,
    "src/data/selenium_core" : None,
    "src/chrome/test/data/plugin" : None,
    "src/data/memory_test" : None,
    "src/data/tab_switching" : None,
    "src/chrome/test/data/osdd" : None,
    "src/webkit/data/bmp_decoder":None,
    "src/webkit/data/ico_decoder":None,
    "src/webkit/data/test_shell/plugins":None,
    "src/webkit/data/xbm_decoder":None,
  }

@CONFIG_CTX()
def checkout_instrumented_libraries(c):
  c.solutions[0].custom_vars['checkout_instrumented_libraries'] = 'True'

@CONFIG_CTX(includes=['chromium'])
def chromium_no_telemetry_dependencies(c):  # pragma: no cover
  c.solutions[0].custom_vars['checkout_telemetry_dependencies'] = 'False'

@CONFIG_CTX()
def arm(c):
  c.target_cpu.add('arm')

@CONFIG_CTX()
def arm64(c):
  c.target_cpu.add('arm64')
