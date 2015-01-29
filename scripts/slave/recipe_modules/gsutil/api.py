# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from slave import recipe_api
from slave import recipe_util

class GSUtilApi(recipe_api.RecipeApi):
  def __call__(self, cmd, name=None, use_retry_wrapper=True, version='3.25',
               **kwargs):
    """A step to run arbitrary gsutil commands.

    Note that this assumes that gsutil authentication environment variables
    (AWS_CREDENTIAL_FILE and BOTO_CONFIG) are already set, though if you want to
    set them to something else you can always do so using the env={} kwarg.

    Note also that gsutil does its own wildcard processing, so wildcards are
    valid in file-like portions of the cmd. See 'gsutil help wildcards'.

    Arguments:
      cmd: list of (string) arguments to pass to gsutil.
           Include gsutil-level options first (see 'gsutil help options').
      name: the (string) name of the step to use.
            Defaults to the first non-flag token in the cmd.
    """
    if not name:
      name = (t for t in cmd if not t.startswith('-')).next()
    full_name = 'gsutil ' + name

    gsutil_path = self.m.path['depot_tools'].join('gsutil.py')
    cmd_prefix = []

    if use_retry_wrapper:
      # We pass the real gsutil_path to the wrapper so it doesn't have to do
      # brittle path logic.
      cmd_prefix = ['--', gsutil_path]
      gsutil_path = self.resource('gsutil_wrapper.py')

    cmd_prefix.extend(['--force-version', version])

    cmd_prefix.append('--')

    return self.m.python(full_name, gsutil_path, cmd_prefix + cmd,
                         infra_step=True, **kwargs)

  def upload(self, source, bucket, dest, args=None, link_name='gsutil.upload',
             metadata=None, **kwargs):
    args = [] if args is None else args[:]
    args += self._generate_metadata_args(metadata)
    full_dest = 'gs://%s/%s' % (bucket, dest)
    cmd = ['cp'] + args + [source, full_dest]
    name = kwargs.pop('name', 'upload')

    result = self(cmd, name, **kwargs)

    if link_name:
      result.presentation.links[link_name] = (
        'https://storage.cloud.google.com/%s/%s' % (bucket, dest)
      )
    return result

  def download(self, bucket, source, dest, args=None, **kwargs):
    args = [] if args is None else args[:]
    full_source = 'gs://%s/%s' % (bucket, source)
    cmd = ['cp'] + args + [full_source, dest]
    name = kwargs.pop('name', 'download')
    return self(cmd, name, **kwargs)

  def download_url(self, url, dest, args=None, **kwargs):
    args = args or []
    url = self._normalize_url(url)
    cmd = ['cp'] + args + [url, dest]
    name = kwargs.pop('name', 'download')
    self(cmd, name, **kwargs)

  def copy(self, source_bucket, source, dest_bucket, dest, args=None,
           link_name='gsutil.copy', metadata=None, **kwargs):
    args = args or []
    args += self._generate_metadata_args(metadata)
    full_source = 'gs://%s/%s' % (source_bucket, source)
    full_dest = 'gs://%s/%s' % (dest_bucket, dest)
    cmd = ['cp'] + args + [full_source, full_dest]
    name = kwargs.pop('name', 'copy')

    result = self(cmd, name, **kwargs)

    if link_name:
      result.presentation.links[link_name] = (
        'https://storage.cloud.google.com/%s/%s' % (dest_bucket, dest)
      )

  def signurl(self, private_key_file, bucket, dest, args=None,
              **kwargs):
    args = args or []
    full_source = 'gs://%s/%s' % (bucket, dest)
    cmd = ['signurl'] + args + [private_key_file, full_source]
    name = kwargs.pop('name', 'signurl')
    return self(cmd, name, **kwargs)

  def remove_url(self, url, args=None, **kwargs):
    args = args or []
    url = self._normalize_url(url)
    cmd = ['rm'] + args + [url]
    name = kwargs.pop('name', 'remove')
    self(cmd, name, **kwargs)

  def download_with_polling(self, url, destination, poll_interval, timeout,
                            name='Download GS file with polling'):
    """Returns a step that downloads a Google Storage file via polling.

    This step allows waiting for the presence of a file so that it can be
    used as a signal to continue work.

    Args:
      url: The Google Storage URL of the file to download.
      destination: The local path where the file will be stored.
      poll_interval: How often, in seconds, to poll for the file.
      timeout: How long, in seconds, to poll for the file before giving up.
      name: The name of the step.
    """
    gsutil_download_path = self.m.path['build'].join(
        'scripts', 'slave', 'gsutil_download.py')
    args = ['--poll',
            '--url', url,
            '--dst', destination,
            '--poll-interval', str(poll_interval),
            '--timeout', str(timeout)]
    return self.m.python(name,
                         gsutil_download_path,
                         args,
                         cwd=self.m.path['slave_build'])

  def _generate_metadata_args(self, metadata):
    result = []
    if metadata:
      for k, v in sorted(metadata.iteritems(), key=lambda (k, _): k):
        field = self._get_metadata_field(k)
        param = (field) if v is None else ('%s:%s' % (field, v))
        result += ['-h', param]
    return result

  def _normalize_url(self, url):
    gs_prefix = 'gs://'
    # Defines the regex that matches a normalized URL.
    url_regex = r'^(%s|https://storage.cloud.google.com/)' % gs_prefix
    normalized_url, subs_made = re.subn(url_regex, gs_prefix, url, count=1)
    assert subs_made == 1, "%s cannot be normalized" % url
    return normalized_url

  @staticmethod
  def _get_metadata_field(name, provider_prefix=None):
    """Returns: (str) the metadata field to use with Google Storage

    The Google Storage specification for metadata can be found at:
    https://developers.google.com/storage/docs/gsutil/addlhelp/WorkingWithObjectMetadata
    """
    # Already contains custom provider prefix
    if name.lower().startswith('x-'):
      return name

    # See if it's innately supported by Google Storage
    if name in (
        'Cache-Control',
        'Content-Disposition',
        'Content-Encoding',
        'Content-Language',
        'Content-MD5',
        'Content-Type',
    ):
      return name

    # Add provider prefix
    if not provider_prefix:
      provider_prefix = 'x-goog-meta'
    return '%s-%s' % (provider_prefix, name)
