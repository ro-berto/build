# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import DEPS
CONFIG_CTX = DEPS['gclient'].CONFIG_CTX
ChromiumGitURL = DEPS['gclient'].config.ChromiumGitURL


@CONFIG_CTX()
def v8_bare(c):
  soln = c.solutions.add()
  soln.name = 'v8'
  soln.url = ChromiumGitURL(c, 'v8', 'v8')


@CONFIG_CTX(includes=['v8_bare'])
def v8(c):
  c.got_revision_reverse_mapping['got_revision'] = 'v8'
  # Needed to get the testers to properly sync the right revision.
  # TODO(infra): Upload full buildspecs for every build to isolate and then use
  # them instead of this gclient garbage.
  c.parent_got_revision_mapping['parent_got_revision'] = 'got_revision'

  p = c.repo_path_map
  p['https://chromium.googlesource.com/chromium/deps/icu'] = (
      'v8/third_party/icu', 'HEAD')


@CONFIG_CTX(includes=['v8'])
def llvm_compiler_rt(c):
  c.solutions[0].custom_deps['v8/third_party/llvm/projects/compiler-rt'] = (
    ChromiumGitURL(c, 'external', 'llvm.org', 'compiler-rt'))


@CONFIG_CTX()
def node_js(c):
  soln = c.solutions.add()
  soln.name = 'node.js'
  soln.url = ChromiumGitURL(c, 'external', 'github.com', 'v8', 'node')
  soln.revision = 'vee-eight-lkgr'
  c.got_revision_reverse_mapping['got_node_js_revision'] = soln.name

  # Specify node-build for side-by-side V8 and node solutions.
  c.solutions[0].custom_vars['build_for_node'] = 'True'
  soln.custom_vars['build_for_node'] = 'True'
