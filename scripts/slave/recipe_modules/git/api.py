# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class GitApi(recipe_api.RecipeApi):
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

  def checkout(self, url, ref='master', dir_path=None, recursive=False,
               submodules=True, keep_paths=None):
    """Returns an iterable of steps to perform a full git checkout.
    Args:
      url (string): url of remote repo to use as upstream
      ref (string): ref to check out after fetching
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

    # git_setup.py always sets the repo at the given url as remote 'origin'.
    remote = 'origin'
    remote_ref = '%s/%s' % (remote, ref)
    fetch_args = ['--recurse-submodules'] if recursive else []

    clean_args = list(self.m.itertools.chain(
        *[('-e', path) for path in keep_paths or []]))

    git_setup_args = ['--path', dir_path, '--url', url]
    if self.m.platform.is_win:
      git_setup_args += ['--git_cmd_path',
                         self.m.path['depot_tools'].join('git.bat')]

    steps = [
      self.m.python('git setup',
                    self.m.path['build'].join('scripts', 'slave',
                                              'git_setup.py'),
                    git_setup_args),
      self('fetch', remote, '%s:refs/remotes/%s' % (ref, remote_ref),
           *fetch_args, cwd=dir_path),
      self('clean', '-f', '-d', '-x', *clean_args, cwd=dir_path),
      self('checkout', '-f', remote_ref, cwd=dir_path),
    ]
    if submodules:
      steps += [
        self('submodule', 'sync', name='submodule sync', cwd=dir_path),
        self('submodule', 'update', '--init', '--recursive',
             name='submodule update', cwd=dir_path),
      ]
    return steps
