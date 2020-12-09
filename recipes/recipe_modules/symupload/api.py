# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class SymuploadApi(recipe_api.RecipeApi):
  """Chromium specific module for symuploads."""

  def __init__(self, properties, **kwargs):
    super(SymuploadApi, self).__init__(**kwargs)
    self._properties = properties

  @property
  def platform(self):
    return self.m.chromium.c.HOST_PLATFORM

  def symupload(self, symupload_binary, artifact, server_url):
    """Uploads the given symbols file with the V1 protocol.

    Note that V1 is deprecated and will be removed once all consumers migrate
    to V2.

    Args:
      artifact: Name of the artifact to upload. Will be found relative to the
        out directory, so must have already been compiled.
      url: URL of the symbol server to upload to.
      api_key: API key used for Symupload V2
    """
    cmd = [symupload_binary]
    # This logic below ported from:
    # https://chrome-internal.googlesource.com/chrome/tools/release/scripts/+/
    # 7dde2e2b66e163680e6a30153096fc4de422e7e3/recipes/recipe_modules/chrome/
    # resources/official_utils.py#96
    if self.platform.startswith('win'):
      cmd.extend(['--timeout', '0', artifact, server_url])
    else:
      cmd.extend([artifact, server_url])

    self.m.step('symupload %s' % artifact, cmd)

  @property
  def symupload_binary(self):
    binary_name = 'symupload'
    if self.platform.startswith('win'):
      binary_name = 'symupload.exe'

    return binary_name

  def __call__(self,
               build_dir,
               api_key_path=None,
               kms_crypto_key=None,
               experimental=False):
    """
    Args:
      build_dir: The absolute path to the build output directory, e.g.
                 [slave-build]/src/out/Release.
      kms_crypto_key: (str) The name of the encryption key.
      api_key_path: (Path) to the input (ciphertext) file for symupload V2.
      experimental: (bool) flag for experimental, meaning it will skip
                    symuploads.
    """
    if not self._properties.symupload_datas:
      return

    with self.m.step.nest('symupload') as presentation:
      # Check binary before moving on
      symupload_binary = self.m.path.join(build_dir, self.symupload_binary)
      if not self.m.path.exists(symupload_binary):
        raise self.m.step.StepFailure('The symupload binary cannot be found '
                                      'at %s. Please ensure targets symupload '
                                      'are being built such that the binaries '
                                      'are generated.' % str(symupload_binary))

      output_api_key = None
      if kms_crypto_key and api_key_path:
        output_api_key = self.m.path['cleanup'].join('symupload-api-key.txt')
        self.m.cloudkms.decrypt(kms_crypto_key, api_key_path, output_api_key)

        api_key = self.m.file.read_raw(
            'read api key', output_api_key, test_data='test_key')
        presentation.logs['api_key sanity check'] = str(len(api_key))

      uploads = []
      for symupload_data in self._properties.symupload_datas:
        # Gather all artifacts that are needed to upload via file glob.
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
            uploads.append('/'.join(common_pieces))

        if symupload_data.artifact:
          uploads.append(self.m.path.join(build_dir, symupload_data.artifact))

        if experimental:
          presentation.step_text = 'Experimental mode. Skipping symupload.'
          presentation.status = self.m.step.SUCCESS
          return

        # Use the symupload resource to mask the API key for v2 protocol.
        # Because the symupload script accepts all urls to upload for a set of
        # artifacts, we'll invoke it here for each symupload data config.
        if output_api_key:
          self.m.build.python(
              'symupload_v2',
              self.resource('symupload.py'),
              [
                  '--artifacts',
                  ','.join(uploads),
                  '--api-key-file',
                  output_api_key,
                  '--binary-path',
                  symupload_binary,
                  '--platform',
                  self.platform,
                  '--server-urls',
                  # the recipe currently only supports one url at the
                  # moment, so this should be reworked to pass it a
                  # comma-delimited list of urls when supported.
                  symupload_data.url,
              ])
        else:
          # We'll continue to invoke the binary directly for V1.
          # TODO: Note that V1 is deprecated and will be removed once all
          # consumers migrate to V2.
          for artifact in uploads:
            self.symupload(
                symupload_binary,
                artifact,  # artifact
                symupload_data.url,
            )
