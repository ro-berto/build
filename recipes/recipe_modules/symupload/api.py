# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class SymuploadApi(recipe_api.RecipeApi):
  """Chromium specific module for symuploads."""

  def __init__(self, properties, **kwargs):
    super(SymuploadApi, self).__init__(**kwargs)
    self._properties = properties

  def symupload(self, binary, artifact, url):
    """Uploads the given symbols file.

    Args:
      artifact: Name of the artifact to upload. Will be found relative to the
        out directory, so must have already been compiled.
      url: URL of the symbol server to upload to.
    """
    cmd = [
        binary,
        artifact,
        url,
    ]
    self.m.step('symupload %s' % artifact, cmd)

  @property
  def symupload_binary(self):
    platform = self.m.chromium.c.TARGET_PLATFORM
    binary_name = 'symupload'
    if platform.startswith('win'):
      binary_name = 'symupload.exe'

    return binary_name

  def __call__(self, build_dir):
    """
    Args:
      build_dir: The absolute path to the build output directory, e.g.
                 [slave-build]/src/out/Release
    """
    if not self._properties.symupload_datas:
      return

    with self.m.step.nest('symupload'):
      # Check binary before moving on
      symupload_binary = self.m.path.join(build_dir, self.symupload_binary)
      if not self.m.path.exists(symupload_binary):
        raise self.m.step.StepFailure('The symupload binary cannot be found '
                                      'at %s. Please ensure targets symupload '
                                      'are being built such that the binaries '
                                      'are generated.' % str(symupload_binary))

      uploads = []
      for symupload_data in self._properties.symupload_datas:
        # File globs
        for filename in symupload_data.file_globs:
          for f in self.m.file.glob_paths(
              'expand file globs',
              build_dir,
              filename,
              test_data=('glob1.txt', 'glob2.txt')):
            # Turn the returned Path object back into a string relative to
            # build_dir.
            assert build_dir.base == f.base
            assert build_dir.is_parent_of(f)
            common_pieces = f.pieces[len(build_dir.pieces):]
            uploads.append(('/'.join(common_pieces), symupload_data.url))

        if symupload_data.artifact:
          uploads.append(
              (self.m.path.join(build_dir,
                                symupload_data.artifact), symupload_data.url))

      for artifact in uploads:
        self.symupload(symupload_binary, artifact[0], artifact[1])
