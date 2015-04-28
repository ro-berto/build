# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

class Package(object):
  """A dart pub package, which may have been published on pub.dartlang.org."""

  def __init__(self, name=None, github_project=None, github_repo=None,
               published=True, dart_repo_package=False, sample=False,
               run_tests=True, dependencies=(), extra_branches=None):
    """Constructs a new package object.

    Either name or github_repo must be supplied. If only github_repo is
    supplied, name is the github_repo with '-' replace by '_'.

    Keyword arguments:
    @param name: pub package name
    @param github_project: github project name (defaults to 'dart-lang')
    @param github_repo: github repo name (defaults to name)
    @param published: whether it has been published on pub.dartlang.org
    @param dart_repo_package: whether this package lives in dart/pkg/*
    @param sample: whether this package is a sample
    @param run_tests: whether to run tests for this package
    @param dependencies: the list of dependencies (if any)
    @param extra_branches: extra branches in the git repo that needs testing
    """
    if not name and not github_repo:
      raise Exception('Either "name" or "github_repo" must be supplied');

    if not name and github_repo:
      name = github_repo.replace('-', '_')

    if dart_repo_package:
      assert github_project is None
      assert github_repo is None
    else:
      if not github_project:
        github_project = 'dart-lang'
      if not github_repo:
        github_repo= name

    self.name = name
    self.github_project = github_project
    self.github_repo = github_repo
    self.published = published
    self.dart_repo_package = dart_repo_package
    self.sample = sample
    self.run_tests = run_tests
    self.dependencies = dependencies
    self.extra_branches = extra_branches or []

  def isGithubPackage(self):
    return self.github_repo is not None

  def isDartRepoPackage(self):
    return self.dart_repo_package

  def isSample(self):
    return self.sample

  def builderNames(self, system):
    all_names = [self.builderName(system)]
    for branch in self.extra_branches:
      all_names.append(self.builderName(system, branch))
    return all_names

  def builderName(self, system, branch=None):
    name = self.github_repo if self.isGithubPackage() else self.name
    repo = '-repo' if self.isDartRepoPackage() else ''
    sample = '-sample' if self.isSample() else ''
    branch = '-%s' % branch if branch else ''
    return 'packages-%s%s%s-%s%s' % (system, repo, sample, name, branch)

  def builderCategory(self):
    if self.isGithubPackage():
      return self.github_repo
    return self.name

  def __str__(self):
    return 'Package(%s)' % self.name

# Packages that we test:
#   We default to github-project dart-lang
#   is_sample means that we will append sample to the name
#   is_repo means if something is living in the dart repository, we will add
#     this to the name as well.
PACKAGES = [
  # Packages in the 'dart-lang' project which are published.
  Package(github_repo='args'),
  Package(github_repo='async'),
  Package(github_repo='barback'),
  Package(github_repo='code-transformers'),
  Package(github_repo='collection'),
  Package(github_repo='core-elements'),
  Package(github_repo='csslib'),
  Package(github_repo='crypto'),
  Package(github_repo='custom-element-apigen'),
  Package(github_repo='dart-protobuf', name='protobuf'),
  Package(github_repo='dart_style'),
  Package(github_repo='gcloud'),
  Package(github_repo='glob'),
  Package(github_repo='googleapis_auth'),
  Package(github_repo='html5lib'),
  Package(github_repo='http'),
  Package(github_repo='http_multi_server'),
  Package(github_repo='http_parser'),
  Package(github_repo='http_server'),
  Package(github_repo='http_throttle'),
  Package(github_repo='initialize'),
  Package(github_repo='intl'),
  Package(github_repo='json_rpc_2'),
  Package(github_repo='logging'),
  Package(github_repo='matcher'),
  Package(github_repo='metatest'),
  Package(github_repo='mime'),
  Package(github_repo='mock'),
  Package(github_repo='oauth2'),
  Package(github_repo='observe'),
  Package(github_repo='paper-elements'),
  Package(github_repo='path'),
  Package(github_repo='polymer-dart', name='polymer'),
  Package(github_repo='polymer-expressions'),
  Package(github_repo='pool'),
  Package(github_repo='reflectable'),
  Package(github_repo='scheduled_test'),
  Package(github_repo='shelf'),
  Package(github_repo='shelf_web_socket'),
  Package(github_repo='smoke'),
  Package(github_repo='source_maps'),
  Package(github_repo='source_span'),
  Package(github_repo='stack_trace'),
  Package(github_repo='string_scanner'),
  Package(github_repo='template-binding'),
  Package(github_repo='typed_data'),
  Package(github_repo='unittest', extra_branches=['stable']),
  Package(github_repo='watcher'),
  Package(github_repo='web-components'),
  Package(github_repo='yaml'),

  # These are living in the same repository but under a sub-directory.
  # The test runner does not understand the directory layout, so we
  # disable tests for googleapis/googleapis_beta.
  Package(name='googleapis', run_tests=False),
  Package(name='googleapis_beta', run_tests=False),

  # Packages in the 'google' github project which are published.
  Package(name='serialization',
          github_project='google',
          github_repo='serialization.dart'),

  # Dart repository packages in dart/pkg/* which are published
  Package(name="analysis_server", dart_repo_package=True),
  Package(name="analysis_services", dart_repo_package=True),
  Package(name="analysis_testing", dart_repo_package=True),
  Package(name="analyzer", dart_repo_package=True),
  Package(name="browser", dart_repo_package=True),
  Package(name="compiler_unsupported", dart_repo_package=True),
  Package(name="custom_element", dart_repo_package=True),
  Package(name="docgen", dart_repo_package=True),
  Package(name="fixnum", dart_repo_package=True),
  Package(name="http_base", dart_repo_package=True),
  Package(name="math", dart_repo_package=True),
  Package(name="mutation_observer", dart_repo_package=True),
  Package(name="typed_mock", dart_repo_package=True),
  Package(name="utf", dart_repo_package=True),

  # Packages in the dart-lang project which are not published.
  Package(github_repo='rpc', published=False),

  # Github samples which are not published on pub.dartlang.org
  Package(github_repo='sample-clock', sample=True, published=False),
  Package(github_repo='sample-dartiverse-search', sample=True, published=False),
  Package(github_repo='sample-dcat', sample=True, published=False),
  Package(github_repo='sample-dgrep', sample=True, published=False),
  Package(github_repo='sample-gauge', sample=True, published=False),
  Package(github_repo='sample-google-maps', sample=True, published=False),
  Package(github_repo='sample-jsonp', sample=True, published=False),
  Package(github_repo='sample-multi-touch', sample=True, published=False),
  Package(github_repo='sample-polymer-intl', sample=True, published=False),
  Package(github_repo='sample-pop_pop_win', sample=True, published=False),
  Package(github_repo='sample-searchable-list', sample=True, published=False),
  Package(github_repo='sample-solar', sample=True, published=False),
  Package(github_repo='sample-spirodraw', sample=True, published=False),
  Package(github_repo='sample-sunflower', sample=True, published=False),
  Package(github_repo='sample-swipe', sample=True, published=False),
  Package(github_repo='sample-todomvc-polymer', sample=True, published=False),
  Package(github_repo='sample-tracker', sample=True, published=False),
]

GITHUB_TESTING_PACKAGES = [
    p for p in PACKAGES if p.isGithubPackage() and p.run_tests]

PUBLISHED_PACKAGE_NAMES = [p.name for p in PACKAGES if p.published]

