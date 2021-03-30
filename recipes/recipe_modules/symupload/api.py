# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
from recipe_engine import recipe_api


class SymuploadApi(recipe_api.RecipeApi):
  """Chromium specific module for symuploads."""

  def __init__(self, properties, **kwargs):
    super(SymuploadApi, self).__init__(**kwargs)
    self._properties = properties

  @property
  def platform(self):
    return self.m.chromium.c.HOST_PLATFORM

  def _get_msdia_paths(self):
    """Returns a list of paths to search for msdia140.dll.

    The caller should add these to the PATH so symupload can find the DLL.

    Newer Win 10 bots have msdia140.dll available in the system, and it might in
    fact be causing problems due to some incompatibility with the win_toolchain
    version of DIA SDK (see also crbug/1085581). So the caller should add these
    to the END of PATH, so that the system default location will be searched
    first.
    """
    if not self.platform.startswith('win'):
      # Only needed on Windows.
      return []

    # Find the win_toolchain version of DIA SDK, which should include
    # msdia140.dll.
    #
    # NOTE: symupload.exe should always be compiled as 64-bit, even for 32-bit
    # Chrome builds, since the 32-bit symupload can't handle the huge
    # chrome.dll, so always use the 64-bit DLL.
    try:
      toolchain_data = self.m.file.read_json(
          'find_win_toolchain',
          self.m.chromium_checkout.checkout_dir.join('src', 'build',
                                                     'win_toolchain.json'))
      dia_dir = self.m.path.join(toolchain_data['path'], 'DIA SDK', 'bin',
                                 'amd64')
      x64_runtime_dir = toolchain_data['runtime_dirs'][0]
      return [dia_dir, x64_runtime_dir]
    # TODO(gbeaty) We really shouldn't catch Exception as it can hide
    # programming errors that should be fixed
    except Exception:
      # Ignore any errors.
      return []

  def symupload(self, symupload_binary, artifact, server_url):
    """Uploads the given symbols file with the V1 protocol.

    Note that V1 is deprecated and will be removed once all consumers migrate
    to V2.

    Args:
      artifact: Name of the artifact to upload. Will be found relative to the
        out directory, so must have already been compiled.
      server_url: URL of the symbol server to upload to.
    """
    cmd = [symupload_binary]
    if self.platform.startswith('win'):
      cmd.extend(['--timeout', '0', artifact, server_url])
    else:
      cmd.extend([artifact, server_url])

    self.m.step('symupload %s' % artifact, cmd)

  def symupload_v2(self,
                   artifacts,
                   artifact_type,
                   encrypted_key_path,
                   kms_key_path,
                   server_url,
                   symupload_binary,
                   name=None):
    """Invokes symupload.py for V2 protocol.

    Args:
      artifacts: (list) of artifacts to upload
      encrypted_key_path: Path object to the encrypted key
      kms_key_path: (str) path to the symupload kms key. Please refer to the
        definition in this .proto for details.
      server_url: (str) url to perform symupload on
      symupload_binary: Path object to the symupload binary
      name: (str) name of the step
    """
    with self.m.step.nest('Prepare API key') as key_presentation:
      output_api_key = self.m.path['cleanup'].join('symupload-api-key.txt')
      self.m.cloudkms.decrypt(kms_key_path, encrypted_key_path, output_api_key)

      api_key = self.m.file.read_raw(
          'read decrypted api key', output_api_key, test_data='test_key')
      key_presentation.logs['api_key sanity check'] = str(len(api_key))

    cmd_args = [
        '--artifacts',
        ','.join(artifacts),
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
        server_url,
    ]

    if artifact_type:
      cmd_args.extend(['--artifact_type', artifact_type])

    return self.m.build.python(name or 'symupload_v2',
                               self.resource('symupload.py'), cmd_args)

  @property
  def symupload_binary(self):
    binary_name = 'symupload'
    if self.platform.startswith('win'):
      binary_name = 'symupload.exe'

    return binary_name

  def __call__(self, build_dir, experimental=False):
    """
    Args:
      build_dir: The absolute path to the build output directory, e.g.
                 [slave-build]/src/out/Release.
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

      with self.m.context(env_suffixes={'PATH': self._get_msdia_paths()}):
        for symupload_data in self._properties.symupload_datas:
          # Gather all artifacts that are needed to upload via file glob.
          uploads = []
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

          for artifact in symupload_data.artifacts:
            uploads.append(self.m.path.join(build_dir, artifact))

          if experimental:
            presentation.step_text = 'Experimental mode. Skipping symupload.'
            presentation.status = self.m.step.SUCCESS
            return

          # Use the symupload resource to mask the API key for v2 protocol.
          # Because the symupload script accepts all urls to upload for a set of
          # artifacts, we'll invoke it here for each symupload data config.
          if symupload_data.base64_api_key:
            if not symupload_data.kms_key_path:
              raise self.m.step.StepFailure('api_key exists but kms_key_path '
                                            'is missing')

            # Write out decoded api key
            input_api_key = self.m.path['cleanup'].join(
                'symupload-api-key.encrypted')
            api_key_data = base64.b64decode(symupload_data.base64_api_key)
            self.m.file.write_raw('write encrypted api key', input_api_key,
                                  api_key_data)

            self.symupload_v2(
                artifacts=uploads,
                artifact_type=symupload_data.artifact_type,
                encrypted_key_path=input_api_key,
                kms_key_path=symupload_data.kms_key_path,
                server_url=symupload_data.url,
                symupload_binary=symupload_binary)
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
