# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import types

from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import Single, Static, Dict, List
from recipe_engine.config_types import Path

def BaseConfig(CHECKOUT_PATH, COMPILE_TARGETS=[], PACKAGE_FILENAME=None,
               PLATFORM=None, SYNC_GENERATED_FILES=False,
               GEN_REPO_BRANCH='master', CORPUS=None, ROOT=None, **_kwargs):
  """Filter out duplicate compilation units.

  Args:
    CHECKOUT_PATH: the source checkout path.
    COMPILE_TARGETS: the compile targets.
    PACKAGE_FILENAME: The prefix of the name of the source archive.
    PLATFORM: The platform for which the code is compiled.
    SYNC_GENERATED_FILES: Whether to sync generated files into a git repo.
    GEN_REPO_BRANCH: Which branch in the generated files repo to sync to.
    CORPUS: Kythe corpus to generate index packs under.
    ROOT: Kythe root to generate index packs under.
  """
  return ConfigGroup(
    CHECKOUT_PATH = Static(CHECKOUT_PATH),
    COMPILE_TARGETS = List(COMPILE_TARGETS),
    PACKAGE_FILENAME = Static(PACKAGE_FILENAME),
    PLATFORM = Static(PLATFORM),
    SYNC_GENERATED_FILES = Static(SYNC_GENERATED_FILES),
    GEN_REPO_BRANCH = Static(GEN_REPO_BRANCH),
    CORPUS = Static(CORPUS),
    ROOT = Static(ROOT),
    debug_path = Single(Path),
    compile_commands_json_file = Single(Path),
    bucket_name = Single(basestring, required=False),
    chromium_git_url = Single(basestring, required=False,
                              empty_val='https://chromium.googlesource.com'),
    additional_repos = Dict(value_type=(basestring, types.NoneType)),
    generated_repo = Single(basestring, required=False),
    generated_author_email = Single(basestring, required=False,
                                    empty_val='git-generated-files-sync@chromium.org'),
    generated_author_name = Single(basestring, required=False,
                                   empty_val='Automatic Generated Files Sync'),
  )

config_ctx = config_item_context(BaseConfig)

@config_ctx(is_root=True)
def base(c):
  c.debug_path = c.CHECKOUT_PATH.join('out', 'Debug')
  c.compile_commands_json_file = c.debug_path.join('compile_commands.json')

@config_ctx(includes=['chromium_additional_repos', 'generate_file', 'chromium_gs'])
def chromium(c):
  pass

@config_ctx()
def chromium_gs(c):
  c.bucket_name = 'chrome-codesearch'

@config_ctx()
def chromium_git(c):
  pass

@config_ctx(includes=['chromium_git'])
def chromium_additional_repos(c):
  # Lists the additional repositories that should be checked out to be included
  # in the source archive that is indexed by Codesearch.
  c.additional_repos['infra'] = '%s/infra/infra' % c.chromium_git_url
  c.additional_repos['tools/chrome-devtools-frontend'] = (
      '%s/chromium/tools/chrome-devtools-frontend' % c.chromium_git_url)
  c.additional_repos['tools/chromium-jobqueue'] = (
      '%s/chromium/tools/chromium-jobqueue' % c.chromium_git_url)
  c.additional_repos['tools/chromium-shortener'] = (
      '%s/chromium/tools/chromium-shortener' % c.chromium_git_url)
  c.additional_repos['tools/command_wrapper/bin'] = (
      '%s/chromium/tools/command_wrapper/bin' % c.chromium_git_url)
  c.additional_repos['tools/depot_tools'] = (
      '%s/chromium/tools/depot_tools' % c.chromium_git_url)
  c.additional_repos['tools/gsd_generate_index'] = (
      '%s/chromium/tools/gsd_generate_index' % c.chromium_git_url)
  c.additional_repos['tools/perf'] = '%s/chromium/tools/perf' % c.chromium_git_url

@config_ctx()
def generate_file(c):
  c.generated_repo = '%s/chromium/src/out' % c.chromium_git_url
