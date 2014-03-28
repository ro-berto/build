# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from slave import recipe_api

class GitApi(recipe_api.RecipeApi):
  _GIT_HASH_RE = re.compile('[0-9a-f]{40}', re.IGNORECASE)

  def __call__(self, *args, **kwargs):
    """Return a git command step."""
    name = kwargs.pop('name', 'git '+args[0])
    # Distinguish 'git config' commands by the variable they are setting.
    if args[0] == 'config' and not args[1].startswith('-'):
      name += ' ' + args[1]
    if 'cwd' not in kwargs:
      kwargs.setdefault('cwd', self.m.path['checkout'])
    git_cmd = 'git'
    if self.m.platform.is_win:
      git_cmd = self.m.path['depot_tools'].join('git.bat')
    return self.m.step(name, [git_cmd] + list(args), **kwargs)

  def checkout(self, url, ref=None, dir_path=None, recursive=False,
               submodules=True, keep_paths=None):
    """Returns an iterable of steps to perform a full git checkout.
    Args:
      url (string): url of remote repo to use as upstream
      ref (string): ref to fetch and check out
      dir_path (Path): optional directory to clone into
      recursive (bool): whether to recursively fetch submodules or not
      submodules (bool): whether to sync and update submodules or not
      keep_paths (iterable of strings): paths to ignore during git-clean;
          paths are gitignore-style patterns relative to checkout_path.
    """
    if not dir_path:
      dir_path = url.rsplit('/', 1)[-1]
      if dir_path.endswith('.git'):  # ex: https://host/foobar.git
        dir_path = dir_path[:-len('.git')]

      # ex: ssh://host:repo/foobar/.git
      dir_path = dir_path or dir_path.rsplit('/', 1)[-1]

      dir_path = self.m.path['slave_build'].join(dir_path)

    if 'checkout' not in self.m.path:
      self.m.path['checkout'] = dir_path

    git_setup_args = ['--path', dir_path, '--url', url]
    if self.m.platform.is_win:
      git_setup_args += ['--git_cmd_path',
                         self.m.path['depot_tools'].join('git.bat')]

    steps = [
        self.m.python(
            'git setup',
            self.m.path['build'].join('scripts', 'slave', 'git_setup.py'),
            git_setup_args),
    ]

    # There are five kinds of refs we can be handed:
    # 0) None. In this case, we default to properties['branch'].
    # 1) A 40-character SHA1 hash.
    # 2) A fully-qualifed arbitrary ref, e.g. 'refs/foo/bar/baz'.
    # 3) A fully qualified branch name, e.g. 'refs/heads/master'.
    #    Chop off 'refs/heads' and now it matches case (4).
    # 4) A branch name, e.g. 'master'.
    # Note that 'FETCH_HEAD' can be many things (and therefore not a valid
    # checkout target) if many refs are fetched, but we only explicitly fetch
    # one ref here, so this is safe.
    if not ref:                                  # Case 0
      fetch_ref = self.m.properties.get('branch') or 'master'
      checkout_ref = 'FETCH_HEAD'
    elif self._GIT_HASH_RE.match(ref):        # Case 1.
      fetch_ref = ref
      checkout_ref = ref
    elif ref.startswith('refs/heads/'):       # Case 3.
      fetch_ref = ref[len('refs/heads/'):]
      checkout_ref = 'FETCH_HEAD'
    else:                                     # Cases 2 and 4.
      fetch_ref = ref
      checkout_ref = 'FETCH_HEAD'

    fetch_args = ['--recurse-submodules'] if recursive else []

    steps.append([
      self('fetch', 'origin', fetch_ref, *fetch_args, cwd=dir_path),
      self('checkout', '-f', checkout_ref, cwd=dir_path),
    ])

    clean_args = list(self.m.itertools.chain(
        *[('-e', path) for path in keep_paths or []]))

    steps.append([
      self('clean', '-f', '-d', '-x', *clean_args, cwd=dir_path),
    ])

    if submodules:
      steps.append([
        self('submodule', 'sync', name='submodule sync', cwd=dir_path),
        self('submodule', 'update', '--init', '--recursive',
             name='submodule update', cwd=dir_path),
      ])

    return steps
