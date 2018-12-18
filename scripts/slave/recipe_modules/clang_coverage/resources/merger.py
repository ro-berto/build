# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Functions for interacting with llvm-profdata"""

import json
import logging
import os
import subprocess

logging.basicConfig(
    format='[%(asctime)s %(levelname)s] %(message)s', level=logging.DEBUG)


def _call_profdata_tool(profile_input_file_paths,
                        profile_output_file_path,
                        profdata_tool_path,
                        retries=3):
  """Calls the llvm-profdata tool.

  Args:
    profile_input_file_paths: A list of relative paths to the files that
        are to be merged.
    profile_output_file_path: The path to the merged file to write.
    profdata_tool_path: The path to the llvm-profdata executable.

  Returns:
    A list of paths to profiles that had to be excluded to get the merge to
    succeed, suspected of being corrupted or malformed.

  Raises:
    CalledProcessError: An error occurred merging profiles.
  """
  logging.info('Merging profiles.')

  try:
    subprocess_cmd = [
        profdata_tool_path, 'merge', '-o', profile_output_file_path,
        '-sparse=true'
    ]
    subprocess_cmd.extend(profile_input_file_paths)

    # Redirecting stderr is required because when error happens, llvm-profdata
    # writes the error output to stderr and our error handling logic relies on
    # that output.
    output = subprocess.check_output(subprocess_cmd, stderr=subprocess.STDOUT)
    logging.info('Merge succeeded with output: %s', output)
  except subprocess.CalledProcessError as error:
    if len(profile_input_file_paths) > 1 and retries >= 0:
      logging.warning('Merge failed with error output: %s', error.output)

      # The output of the llvm-profdata command will include the path of
      # malformed files, such as
      # `error: /.../default.profraw: Malformed instrumentation profile data`
      invalid_profiles = [
          f for f in profile_input_file_paths if f in error.output
      ]

      if not invalid_profiles:
        logging.info(
            'Merge failed, but wasn\'t able to figure out the culprit invalid '
            'profiles from the output, so skip retry and bail out.')
        raise error

      valid_profiles = list(
          set(profile_input_file_paths) - set(invalid_profiles))
      if valid_profiles:
        logging.warning(
            'Following invalid profiles are removed as they were mentioned in '
            'the merge error output: %r', invalid_profiles)
        logging.info('Retry merging with the remaining profiles: %r',
                     valid_profiles)
        return invalid_profiles + _call_profdata_tool(
            valid_profiles, profile_output_file_path, profdata_tool_path,
            retries - 1)

    logging.error('Failed to merge profiles, return code (%d), output: %s' %
                  (error.returncode, error.output))
    raise error

  logging.info('Profile data is created as: "%s".', profile_output_file_path)
  return []


def _get_profile_paths(input_dir, input_extension):
  """Finds all the profiles in the given directory (recursively)."""
  paths = []
  for dir_path, _sub_dirs, file_names in os.walk(input_dir):
    paths.extend([
        os.path.join(dir_path, fn)
        for fn in file_names
        if fn.endswith(input_extension)
    ])
  return paths


def merge_profiles(input_dir, output_file, input_extension, profdata_tool_path):
  """Merges the profiles produced by the shards using llvm-profdata.

  Args:
    input_dir (str): The path to traverse to find input profiles.
    output_file (str): Where to write the merged profile.
    input_extension (str): File extension to look for in the input_dir.
        e.g. '.profdata' or '.profraw'
    profdata_tool_path: The path to the llvm-profdata executable.
  Returns:
    The list of profiles that had to be excluded to get the merge to
    succeed.
  """
  profile_input_file_paths = _get_profile_paths(input_dir, input_extension)
  invalid_profiles = _call_profdata_tool(
      profile_input_file_paths=profile_input_file_paths,
      profile_output_file_path=output_file,
      profdata_tool_path=profdata_tool_path)

  # Remove inputs, as they won't be needed and they can be pretty large.
  for input_file in profile_input_file_paths:
    os.remove(input_file)

  return invalid_profiles
