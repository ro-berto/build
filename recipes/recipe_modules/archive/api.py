# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
import re
import os

from . import manual_bisect_files

from google.protobuf import json_format

from PB.recipe_modules.build.archive.properties import ArchiveData, \
                                                       InputProperties
from recipe_engine import recipe_api

# Regular expression to identify a Git hash.
GIT_COMMIT_HASH_RE = re.compile(r'[a-zA-Z0-9]{40}')
# The Google Storage metadata key for the full commit position.
GS_COMMIT_POSITION_KEY = 'Cr-Commit-Position'
# The Google Storage metadata key for the commit position number.
GS_COMMIT_POSITION_NUMBER_KEY = 'Cr-Commit-Position-Number'
# The Google Storage metadata key for the Git commit hash.
GS_GIT_COMMIT_KEY = 'Cr-Git-Commit'


class ArchiveApi(recipe_api.RecipeApi):
  """Chromium specific module for zipping, uploading and downloading build
  artifacts implemented as a wrapper around zip_build.py script.

  If you need to upload or download build artifacts (or any other files) for
  something other than Chromium flavor, consider using 'zip' + 'gsutil' or
  'isolate' modules instead.
  """

  def __init__(self, props, **kwargs):
    super().__init__(**kwargs)

    # This input property is populated by the global property $build/archive.
    self._default_config = props

  def zip_and_upload_build(self,
                           step_name,
                           target,
                           build_url=None,
                           src_dir=None,
                           build_revision=None,
                           package_dsym_files=False,
                           exclude_files=None,
                           exclude_perf_test_files=False,
                           update_properties=None,
                           store_by_hash=True,
                           platform=None,
                           **kwargs):
    """Returns a step invoking zip_build.py to zip up a Chromium build.
       If build_url is specified, also uploads the build."""
    if not src_dir:
      src_dir = self.m.path['checkout']
    args = [
        '--target',
        target,
        '--gsutil-py-path',
        self.m.depot_tools.gsutil_py_path,
        '--staging-dir',
        self.m.path['cache'].join('chrome_staging'),
        '--src-dir',
        src_dir,
    ]
    args += self.m.build.bot_utils_args
    if 'build_archive_url' in self.m.properties:
      args.extend([
          '--use-build-url-name', '--build-url',
          self.m.properties['build_archive_url']
      ])
    elif build_url:
      args.extend(['--build-url', build_url])
    if build_revision:
      args.extend(['--build_revision', build_revision])
    if package_dsym_files:
      args.append('--package-dsym-files')
    if exclude_files:
      args.extend(['--exclude-files', exclude_files])
    if 'gs_acl' in self.m.properties:
      args.extend(['--gs-acl', self.m.properties['gs_acl']])
    if exclude_perf_test_files and platform:
      include_bisect_file_list = (
          manual_bisect_files.CHROME_REQUIRED_FILES.get(platform))
      include_bisect_strip_list = (
          manual_bisect_files.CHROME_STRIP_LIST.get(platform))
      include_bisect_whitelist = (
          manual_bisect_files.CHROME_WHITELIST_FILES.get(platform))
      if include_bisect_file_list:
        inclusions = ','.join(include_bisect_file_list)
        args.extend(['--include-files', inclusions])
      if include_bisect_strip_list:
        strip_files = ','.join(include_bisect_strip_list)
        args.extend(['--strip-files', strip_files])
      if include_bisect_whitelist:
        args.extend(['--whitelist', include_bisect_whitelist])
      args.extend(['--exclude-extra'])

      # If update_properties is passed in and store_by_hash is False,
      # we store it with commit position number instead of a hash
      if update_properties and not store_by_hash:
        commit_position = self._get_commit_position(update_properties, None)
        _, cp_number = self.m.commit_position.parse(commit_position)
        args.extend(['--build_revision', cp_number])

    properties_json = self.m.json.dumps(self.m.properties.legacy())
    args.extend(['--build-properties', properties_json])
    args.extend(['--json-urls', self.m.json.output()])

    kwargs['step_test_data'] = lambda: self.test_api.m.json.output({
        'storage_url':
            'gs://zip_build.example.com/output.zip',
        'zip_url':
            'https://storage.cloud.google.com/zip_build.example.com/output.zip',
    })
    cmd = [
        'python3',
        self.repo_resource('recipes', 'zip_build.py'),
    ] + args
    result = self.m.step(step_name, cmd, infra_step=True, **kwargs)
    urls = result.json.output
    if 'storage_url' in urls:
      result.presentation.links['download'] = urls['storage_url']
    if 'zip_url' in urls:
      result.presentation.properties['build_archive_url'] = urls['zip_url']
    return result

  def _get_commit_position(self, update_properties, primary_project):
    """Returns the commit position of the project (or the specified primary
    project).
    """
    if primary_project:
      key = 'got_%s_revision_cp' % primary_project
    else:
      key = 'got_revision_cp'
    return update_properties.get(key,
                                 update_properties.get('got_src_revision_cp'))

  def _get_git_commit(self, update_properties, primary_project):
    """Returns: (str/None) the git commit hash for a given project.

    Attempts to identify the git commit hash for a given project. If
    'primary_project' is None, or if there is no git commit hash for the
    specified primary project, the checkout-wide commit hash will be used.

    If none of the candidate configurations are present, the value None will be
    returned.
    """
    if primary_project:
      commit = update_properties.get('got_%s_revision' % primary_project)
      if commit:
        assert GIT_COMMIT_HASH_RE.match(commit), commit
        return commit

    commit = update_properties.get('got_revision')
    if commit:
      assert GIT_COMMIT_HASH_RE.match(commit), commit
    return commit

  def _get_comparable_upload_path_for_sort_key(self, branch, number):
    """Returns a sortable string corresponding to the commit position."""
    if branch and branch not in ('refs/heads/master', 'refs/heads/main'):
      branch = branch.replace('/', '_')
      return '%s-%s' % (branch, number)
    return str(number)

  def clusterfuzz_archive(self,
                          build_dir,
                          update_properties,
                          gs_bucket,
                          archive_prefix,
                          archive_subdir_suffix='',
                          gs_acl=None,
                          revision_dir=None,
                          primary_project=None,
                          bitness=None,
                          build_config=None,
                          use_legacy=True,
                          sortkey_datetime=None,
                          **kwargs):
    # TODO(machenbach): Merge revision_dir and primary_project. The
    # revision_dir is only used for building the archive name while the
    # primary_project is authoritative for the commit position.
    """Archives and uploads a build to google storage.

    The build is filtered by a list of file exclusions and then zipped. It is
    uploaded to google storage with some metadata about the commit position
    and revision attached. The zip file follows the naming pattern used by
    clusterfuzz. The file pattern is:
    <archive name>-<platform>-<target><optional component>-<sort-key>.zip

    If the build is experimental, -experimental is appended in the name.

    Example: cool-project-linux-release-refs_heads_b1-12345.zip
    The archive name is "cool-project" and there's no component build. The
    commit is on a branch called b1 at commit position number 12345.

    Example: cool-project-mac-debug-x10-component-234.zip
    The archive name is "cool-project" and the component's name is "x10". The
    component is checked out in branch main with commit position number 234.

    Args:
      build_dir: The absolute path to the build output directory, e.g.
                 [slave-build]/src/out/Release
      update_properties: The properties from the bot_update step (containing
                         commit information)
      gs_bucket: Name of the google storage bucket to upload to
      archive_prefix: Prefix of the archive zip file
      archive_subdir_suffix: Optional suffix to the google storage subdirectory
                             name that contains the archive files
      gs_acl: ACL used for the file on google storage
      revision_dir: Optional component name if the main revision for this
                    archive is a component revision
      primary_project: Optional project name for specifying the revision of the
                       checkout
      bitness: The bitness of the build (32 or 64) to distinguish archive
               names.
      build_config: Name of build config, e.g. release or debug. This is used
                    to qualify archive file names. If not given, it is inferred
                    from the build output directory.
      use_legacy: Specify if legacy paths and archive names should be used. Set
                  to false for new builders.
      sortkey_datetime: If set, the api will use this datetime as the sortable
                        key path in the archive name, instead of trying to infer
                        it from the commit information.  This will be formatted
                        as YYYYMMDDHHMM.
    """
    # We should distinguish build archives also by bitness on new bots, so that
    # 32 and 64 bit bots can coexist. We don't change old bots to not confuse
    # clusterfuzz bisect jobs.
    assert use_legacy or bitness, 'Must specify bitness for new builders.'
    build_config = (build_config or self.m.path.split(build_dir)[-1]).lower()
    gs_metadata = {}
    if sortkey_datetime is not None:
      sortkey_path = sortkey_datetime.strftime('%Y%m%d%H%M')
    else:
      commit_position = self._get_commit_position(update_properties,
                                                  primary_project)
      cp_ref, cp_number = self.m.commit_position.parse(commit_position)
      sortkey_path = self._get_comparable_upload_path_for_sort_key(
          cp_ref, cp_number)
      gs_metadata[GS_COMMIT_POSITION_NUMBER_KEY] = cp_number
      if commit_position:
        gs_metadata[GS_COMMIT_POSITION_KEY] = commit_position
    build_git_commit = self._get_git_commit(update_properties, primary_project)
    staging_dir = self.m.path['cleanup'].join('chrome_staging')
    self.m.file.ensure_directory('create staging_dir', staging_dir)

    llvm_tools_to_copy = ['llvm-symbolizer', 'sancov']
    llvm_bin_dir = self.m.path['checkout'].join('third_party', 'llvm-build',
                                                'Release+Asserts', 'bin')
    ext = '.exe' if self.m.platform.is_win else ''

    for tool in llvm_tools_to_copy:
      tool_src = self.m.path.join(llvm_bin_dir, tool + ext)
      tool_dst = self.m.path.join(build_dir, tool + ext)

      if not self.m.path.exists(tool_src):
        continue

      try:
        self.m.file.copy('Copy ' + tool, tool_src, tool_dst)
      except self.m.step.StepFailure:  # pragma: no cover
        # On some builds, it appears that a soft/hard link of llvm-symbolizer
        # exists in the build directory, which causes shutil.copy to raise an
        # exception. Either way, this shouldn't cause the whole build to fail.
        pass

    if not self.m.platform.is_win:
      llvm_lib_dir = self.m.path['checkout'].join('third_party', 'llvm-build',
                                                  'Release+Asserts', 'lib')
      libstdcplusplus_lib = 'libstdc++.so.6'
      libstdcplusplus_lib_src = self.m.path.join(llvm_lib_dir,
                                                 libstdcplusplus_lib)
      libstdcplusplus_lib_dst = self.m.path.join(build_dir, libstdcplusplus_lib)
      if self.m.path.exists(libstdcplusplus_lib_src):
        try:
          self.m.file.copy('Copy ' + libstdcplusplus_lib,
                           libstdcplusplus_lib_src, libstdcplusplus_lib_dst)
        except self.m.step.StepFailure:  # pragma: no cover
          # On some builds, it appears that a soft/hard link of libstdc++.so.6
          # exists in the build directory, which causes shutil.copy to raise an
          # exception. Either way, this shouldn't cause the whole build to fail.
          pass

    # Build the list of files to archive.
    cmd = [
        'python3',
        self.resource('filter_build_files.py'),
        '--dir',
        build_dir,
        '--platform',
        self.m.platform.name,
        '--output',
        self.m.json.output(),
    ]
    filter_result = self.m.step(
        'filter build_dir',
        cmd,
        infra_step=True,
        step_test_data=lambda: self.m.json.test_api.output(['file1', 'file2']),
        **kwargs)

    zip_file_list = filter_result.json.output

    # Use the legacy platform name if specified as Clusterfuzz has some
    # expectations on this (it only affects Windows, where it replace 'win'
    # by 'win32').
    if use_legacy:
      platform_name = self.legacy_platform_name()
      target_name = build_config
    else:
      # Always qualify platform with bitness on new bots. E.g. linux32 or win64.
      platform_name = self.m.platform.name + str(bitness)
      # Split off redundant _x64 suffix on windows. The bitness is part of the
      # platform.
      target_name = build_config.split('_')[0]

    pieces = [platform_name, target_name]
    if archive_subdir_suffix:
      pieces.append(archive_subdir_suffix)
    subdir = '-'.join(pieces)

    # Components like v8 get a <name>-v8-component-<revision> infix.
    component = ''
    if revision_dir:
      component = '-%s-component' % revision_dir

    zip_file_base_name = '%s-%s-%s%s-%s' % (
        archive_prefix, platform_name, target_name, component, sortkey_path)
    if self.m.runtime.is_experimental:
      zip_file_base_name += ('-experimental')
    zip_file_name = '%s.zip' % zip_file_base_name

    cmd = [
        'python3',
        self.resource('zip_archive.py'),
        staging_dir,
        zip_file_base_name,
        self.m.json.input(zip_file_list),
        build_dir,
    ]
    self.m.step('zipping', cmd, infra_step=True, **kwargs)

    zip_file = staging_dir.join(zip_file_name)

    if build_git_commit:
      gs_metadata[GS_GIT_COMMIT_KEY] = build_git_commit

    gs_args = []
    if gs_acl:
      gs_args.extend(['-a', gs_acl])
    self.m.gsutil.upload(
        zip_file,
        gs_bucket,
        "/".join([subdir, zip_file_name]),
        args=gs_args,
        metadata=gs_metadata,
        use_retry_wrapper=False,
    )
    self.m.file.remove(zip_file_name, zip_file)

  def download_and_unzip_build(self,
                               step_name,
                               target,
                               build_url,
                               src_dir=None,
                               build_revision=None,
                               build_archive_url=None,
                               **kwargs):
    """Returns a step invoking extract_build.py to download and unzip
       a Chromium build."""
    if not src_dir:
      src_dir = self.m.path['checkout']
    args = [
        '--gsutil-py-path',
        self.m.depot_tools.gsutil_py_path,
        '--target',
        target,
        '--src-dir',
        src_dir,
    ]
    args += self.m.build.bot_utils_args
    if build_archive_url:
      args.extend(['--build-archive-url', build_archive_url])
    else:
      args.extend(['--build-url', build_url])
      if build_revision:
        args.extend(['--build_revision', build_revision])

    if self.m.builder_group.for_current:
      args.extend(['--builder-group', self.m.builder_group.for_current])

    properties = (
        ('parent_builddir', '--parent-build-dir'),
        ('parentname', '--parent-builder-name'),
        ('parentslavename', '--parent-slave-name'),
        ('webkit_dir', '--webkit-dir'),
        ('revision_dir', '--revision-dir'),
    )
    for property_name, switch_name in properties:
      if self.m.properties.get(property_name):
        args.extend([switch_name, self.m.properties[property_name]])

    if self.m.properties.get('parent_buildnumber'):
      args.extend([
          '--parent-build-number',
          int(self.m.properties.get('parent_buildnumber')),
      ])
    args.extend(['--build-number', self.m.buildbucket.build.number])

    cmd = [
        'python3',
        self.repo_resource('recipes', 'extract_build.py'),
    ] + args
    self.m.step(step_name, cmd, infra_step=True, **kwargs)

  # FIXME(machenbach): This is currently used by win64 builders as well, which
  # have win32 in their archive names, which is confusing.
  def legacy_platform_name(self):
    """Replicates the behavior of PlatformName() in chromium_utils.py."""
    if self.m.platform.is_win:
      return 'win32'
    return self.m.platform.name

  def _legacy_url(self, is_download, gs_bucket_name, extra_url_components):
    """Computes a build_url suitable for uploading a zipped Chromium
    build to Google Storage.

    The reason this is named 'legacy' is that there are a large number
    of dependencies on the exact form of this URL. The combination of
    zip_build.py, extract_build.py, bot_utils.py, and runtest.py
    require that:

    * The platform name be exactly one of 'win32', 'mac', or 'linux'
    * The upload URL only name the directory on GS into which the
      build goes (zip_build.py computes the name of the file)
    * The download URL contain the unversioned name of the zip archive
    * The revision on the builder and tester machines be exactly the
      same

    There were too many dependencies to tease apart initially, so this
    function simply emulates the form of the URL computed by the
    underlying scripts.

    extra_url_components, if specified, should be a string without a
    trailing '/' which is inserted in the middle of the URL.

    The builder_name, or parent_buildername, is always automatically
    inserted into the URL.

    If build is running in experimental mode (see recipe_engine.runtime module),
    then 'experimental/' is prepended to path inside bucket automatically. This
    protects production builds from intererence from experimentation.
    """

    result = ('gs://' + gs_bucket_name)
    if self.m.runtime.is_experimental:
      result += ('/experimental')
    if extra_url_components:
      result += ('/' + extra_url_components)
    if is_download:
      result += ('/' + self.m.properties['parent_buildername'] + '/' +
                 'full-build-' + self.legacy_platform_name() + '.zip')
    else:
      result += '/' + self.m.buildbucket.builder_name
    return result

  def legacy_upload_url(self, gs_bucket_name, extra_url_components=None):
    """Returns a url suitable for uploading a Chromium build to Google
    Storage.

    extra_url_components, if specified, should be a string without a
    trailing '/' which is inserted in the middle of the URL.

    The builder_name, or parent_buildername, is always automatically
    inserted into the URL."""
    return self._legacy_url(False, gs_bucket_name, extra_url_components)

  def legacy_download_url(self, gs_bucket_name, extra_url_components=None):
    """Returns a url suitable for downloading a Chromium build from
    Google Storage.

    extra_url_components, if specified, should be a string without a
    trailing '/' which is inserted in the middle of the URL.

    The builder_name, or parent_buildername, is always automatically
    inserted into the URL."""
    return self._legacy_url(True, gs_bucket_name, extra_url_components)

  def _create_targz_archive_for_upload(self, build_dir, files, directories):
    """Adds files and dirs to a tar.gz file to be uploaded.

    Args:
      build_dir: The absolute path to the build output directory.
      files: List of files to include. Paths are relative to |build_dir|.
      directories: List of directories to include. Paths are relative to
                   |build_dir|.

    Returns:
      Absolute path to the archive file.
    """
    tmp_dir = self.m.path.mkdtemp()
    output = tmp_dir.join('artifact.tar.gz')
    pkg = self.m.tar.make_package(build_dir, output, 'gz')

    for f in files:
      pkg.add_file(build_dir.join(f))
    for directory in directories:
      pkg.add_directory(build_dir.join(directory))

    pkg.tar('Create tar.gz archive')
    return output

  def _create_zip_archive_for_upload(self, build_dir, files, directories):
    """Adds files and directories to a zip file to be uploaded.

    Args:
      build_dir: The absolute path to the build output directory.
      files: List of files to include. Paths are relative to |build_dir|.
      directories: List of directories to include. Paths are relative to
                   |build_dir|.

    Returns:
      Absolute path to the archive file.
    """
    # Create a temporary directory to hold the zipped archive.
    temp_dir = self.m.path.mkdtemp()
    output_path = temp_dir.join('artifact.zip')
    package = self.m.zip.make_package(build_dir, output_path)

    for f in files:
      package.add_file(build_dir.join(f))
    for directory in directories:
      package.add_directory(build_dir.join(directory))

    # An exception will be raised if there's an error, so we can assume that
    # this step succeeds.
    package.zip('Create generic archive')

    return output_path

  def get_channel_name(self):
    """Get the current branch's channel name.

    Returns:
      The string of channel's name: it can be 'canary', 'dev', 'beta', 'stable',
       or 'legacy88'. Or no return with an empty step.
    """
    base_name = '/'.join(['chrome', 'VERSION'])

    def step_test_data():
      contents = '\n'.join(['MAJOR=91', 'MINOR=0', 'BUILD=4458', 'PATCH=0'])
      response_data = base64.b64encode(contents.encode('utf-8')).decode('ascii')
      return self.m.json.test_api.output({
          'value': response_data,
      })

    contents = self.m.gitiles.download_file(
        "https://chromium.googlesource.com/chromium/src.git/",
        base_name,
        branch='refs/heads/main',
        step_name='fetch milestone_branch',
        step_test_data=step_test_data,
    )
    canary_milestone = int(contents.split('\n')[0].split('=')[1])
    milestone = int(self.m.chromium.get_version()['MAJOR'])

    # Compare the milestone of latest Chromium with the current build to
    # determine the channel.
    if milestone == canary_milestone:
      return 'canary'
    if milestone + 1 == canary_milestone:
      return 'beta'
    if milestone + 2 == canary_milestone:
      return 'stable'
    if milestone + 10 >= canary_milestone:
      # Channel name for old milestones set to legacy.
      return 'legacy%s' % milestone
    self.m.step.empty(  # pragma: no cover
        'Unknown channel',
        status=self.m.step.FAILURE,
        step_text='Can not find channel for milestone: %s' % milestone)

  def _replace_placeholders(self, update_properties, custom_vars, input_str):
    position_placeholder = '{%position%}'
    if position_placeholder in input_str:
      commit_position = self._get_commit_position(update_properties, None)
      if not commit_position:
        self.m.step.empty(
            'Missing position placeholder',
            status=self.m.step.FAILURE,
            step_text=(
                'got_revision_cp or got_src_revision_cp is needed to populate '
                'the {%position%} placeholder'))
      _, position = self.m.commit_position.parse(commit_position)
      input_str = input_str.replace(position_placeholder, str(position))

    channel_placeholder = '{%channel%}'
    if channel_placeholder in input_str:
      channel = self.get_channel_name()
      input_str = input_str.replace(channel_placeholder, channel)

    arch_placeholder = '{%arch%}'
    if arch_placeholder in input_str:
      if (self.m.chromium.c.TARGET_ARCH == 'arm' and
          self.m.chromium.c.TARGET_BITS in (64, 32)):
        arch = 'arm' + str(self.m.chromium.c.TARGET_BITS)
      elif (self.m.chromium.c.TARGET_ARCH == 'intel' and
            self.m.chromium.c.TARGET_BITS == 64):
        arch = 'amd64'
      else:  # pragma: no cover
        self.m.step.empty(
            'Unresolved placeholder',
            status=self.m.step.FAILURE,
            step_text='Unsupported value for arch placeholder: %s-%d' %
            (self.m.chromium.c.TARGET_ARCH, self.m.chromium.c.TARGET_BITS))
      input_str = input_str.replace(arch_placeholder, arch)

    commit_placeholder = '{%commit%}'
    if commit_placeholder in input_str:
      commit = self._get_git_commit(update_properties, None)
      if not commit:
        self.m.step.empty(
            'Missing commit placeholder',
            status=self.m.step.FAILURE,
            step_text=('got_revision is needed to populate '
                       'the {%commit%} placeholder'))
      input_str = input_str.replace(commit_placeholder, commit)

    timestamp_placeholder = '{%timestamp%}'
    if timestamp_placeholder in input_str:
      timestamp = str(self.m.time.utcnow().strftime('%Y%m%d%H%M%S'))
      input_str = input_str.replace(timestamp_placeholder, timestamp)

    chromium_version_placeholder = '{%chromium_version%}'
    if chromium_version_placeholder in input_str:
      version = self.m.chromium.get_version()
      value = "%s.%s.%s.%s" % (version['MAJOR'], version['MINOR'],
                               version['BUILD'], version['PATCH'])
      input_str = input_str.replace(chromium_version_placeholder, value)

    builder_name_placeholder = '{%builder_name%}'
    if builder_name_placeholder in input_str:
      builder_name = self.m.buildbucket.builder_name
      input_str = input_str.replace(builder_name_placeholder, builder_name)

    build_number_placeholder = '{%build_number%}'
    if build_number_placeholder in input_str:
      build_number = str(self.m.buildbucket.build.number)
      input_str = input_str.replace(build_number_placeholder, build_number)

    if custom_vars:
      for placeholder, key in re.findall('({%(.*?)%})', input_str):
        if key in custom_vars:
          input_str = input_str.replace(placeholder, custom_vars[key])
        else:
          self.m.step.empty(
              'Unresolved placeholder',
              status=self.m.step.FAILURE,
              step_text=placeholder + ' can not be resolved')

    return input_str

  def _deconstruct_version(self, version):
    """Breaks version down into list of parts."""
    segments = []
    for segment in version.strip().split('.'):
      segments.append(int(segment))
    return segments

  def _read_source_side_archive_spec(self, source_side_archive_spec_path):
    if not self.m.path.exists(source_side_archive_spec_path):
      return None
    archive_spec_result = self.m.json.read(
        'read archive spec (%s)' %
        self.m.path.basename(source_side_archive_spec_path),
        source_side_archive_spec_path,
        infra_step=True,
        step_test_data=lambda: self.m.json.test_api.output({}))
    archive_spec_result.presentation.step_text = ('path: %s' %
                                                  source_side_archive_spec_path)
    source_side_archive_spec = archive_spec_result.json.output
    return source_side_archive_spec

  def _get_source_side_archive_spec(self, spec_path):
    source_side_archive_spec_path = self.m.chromium_checkout.checkout_dir.join(
        *spec_path)
    archive_spec = self._read_source_side_archive_spec(
        source_side_archive_spec_path)
    return archive_spec

  def _get_archive_config(self, config):
    if config is None:
      config = self._default_config

    if not config.source_side_spec_path:
      return config

    source_side_archive_spec = self._get_source_side_archive_spec(
        config.source_side_spec_path)
    if source_side_archive_spec:
      return json_format.ParseDict(
          source_side_archive_spec,
          InputProperties(),
          ignore_unknown_fields=True)
    return config

  def _validate_paths(self, name, archive_data, base_path, paths):
    """Checks all paths for existence.

    Raises an error if at least one path is missing. If skip_empty_sources is
    set, return existing paths instead.
    """
    # In test mode, all paths exist by default and do not need to be mocked.
    if self._test_data.enabled:
      # These paths are used for testing the validation step
      if not ('missing-file.json' in paths or 'missing-dir' in paths):
        return paths

    with self.m.step.nest('Validate %s' % name) as presentation:
      valid = []
      missing = []
      for path in paths:
        path_exists = self.m.path.exists(self.m.path.join(base_path, path))
        (missing, valid)[path_exists].append(path)

      if missing:
        msg = 'The following %s are missing: %s' % (name, ', '.join(missing))
        presentation.step_text = msg

        if not archive_data.skip_empty_source:
          raise recipe_api.StepFailure('Missing %s' % name)

    return valid

  def generic_archive(self,
                      build_dir,
                      update_properties,
                      custom_vars=None,
                      config=None,
                      report_artifacts=False):
    """Archives one or multiple packages to either google cloud storage or CIPD.

    The exact configuration of the archive is specified by InputProperties. See
    archive/properties.proto.

    Args:
      build_dir: The absolute path to the build output directory, e.g.
                 [slave-build]/src/out/Release
      update_properties: The properties from the bot_update step (containing
                         commit information).
      custom_vars: Dict of custom string substitution for gcs paths.
                   E.g. custom_vars={'chrome_version':'1.2.3.4'}, then
                   gcs_path='gcs/{%chrome_version%}/path' will be replaced to
                   'gcs/1.2.3.4/path'.
      config: An instance of archive/properties.proto:InputProperties.
              DEPRECATED: If None, this will default to the global property
              $build/archive.
      report_artifacts: A boolean flag to enable artifact reporting. This is
                        set by recipe that uses this module.

    Returns:
      A dictionary that stores custom_vars and update_properties, as well as
      the following keys:
        gcs: A list of dictionaries of files and their respective upload
             destination urls.
        cipd: A dictionary containing information about unused references for
              each package.

    """
    upload_results = {}
    upload_results['cipd'] = {}
    upload_results['gcs'] = []
    upload_results['update_properties'] = update_properties
    upload_results['custom_vars'] = custom_vars

    archive_config = self._get_archive_config(config)

    if (not archive_config.archive_datas and
        not archive_config.cipd_archive_datas):
      return upload_results

    with self.m.step.nest('Generic Archiving Steps', status='last'):
      for archive_data in archive_config.archive_datas:
        if not archive_data.only_upload_on_tests_success:
          gcs_uploads = self.gcs_archive(build_dir, update_properties,
                                         archive_data, custom_vars,
                                         report_artifacts)
          upload_results['gcs'].append(gcs_uploads)
      for cipd_archive_data in archive_config.cipd_archive_datas:
        upload_results['cipd'].update(
            self.cipd_archive(build_dir, update_properties, custom_vars,
                              cipd_archive_data, report_artifacts))
    return upload_results

  def generic_archive_after_tests(self,
                                  build_dir,
                                  config=None,
                                  upload_results=None,
                                  test_success=False):
    """ Additional archiving steps after tests run.

    For google cloud storage packages, they will only be uploaded in this step
    if test_success is True and only_upload_on_tests_success is set to True,

    For CIPD packages, if test_success is True then refs will be added for each
    package with only_set_refs_on_tests_success set to True.

    Args:
      upload_results: The upload results from generic_archive.

    For information about other args see generic_archive.
    """
    if not upload_results or not test_success:
      return

    archive_config = self._get_archive_config(config)

    if (not archive_config.archive_datas and
        not archive_config.cipd_archive_datas):
      return

    with self.m.step.nest('Generic Archiving Steps After Tests'):
      for archive_data in archive_config.archive_datas:
        if archive_data.only_upload_on_tests_success:
          self.gcs_archive(build_dir, upload_results['update_properties'],
                           archive_data, upload_results['custom_vars'])
      if upload_results['cipd']:
        for pkg in upload_results['cipd']:
          self.m.cipd.set_ref(
              package_name=pkg,
              version=upload_results['cipd'][pkg]['instance'],
              refs=upload_results['cipd'][pkg]['refs'])

  def gcs_archive(self,
                  build_dir,
                  update_properties,
                  archive_data,
                  custom_vars=None,
                  report_artifacts=False):
    """Archives a single package to google cloud storage.

    The exact configuration of the archive is specified by InputProperties. See
    archive/properties.proto.

    Args:
      build_dir: The absolute path to the build output directory, e.g.
                 [slave-build]/src/out/Release
      update_properties: The properties from the bot_update step (containing
                         commit information).
      archive_data: An instance of
                    archive/properties.proto:InputProperties.archive_datas.
      custom_vars: Dict of custom string substitution for gcs paths.
                   E.g. custom_vars={'chrome_version':'1.2.3.4'}, then
                   gcs_path='gcs/{%chrome_version%}/path' will be replaced to
                   'gcs/1.2.3.4/path'.
      report_artifacts: A boolean flag to enable artifact reporting.
    """

    def _sanitize_gcs_path(gcs_path, file_path):
      gcs = gcs_path.split('/')
      f = file_path.split('/')
      return ('/'.join([x for x in gcs if x]) + '/' +
              '/'.join([x for x in f if x]))

    def _resolve_base_dir(base_dir):
      return self.m.chromium_checkout.checkout_dir.join(base_dir)

    base_path = build_dir
    if archive_data.base_dir:
      base_path = _resolve_base_dir(archive_data.base_dir)

    # Perform dynamic configuration from placeholders, if necessary.
    gcs_path = self._replace_placeholders(update_properties, custom_vars,
                                          archive_data.gcs_path)

    gcs_bucket = self._replace_placeholders(update_properties, custom_vars,
                                            archive_data.gcs_bucket)

    experimental = self.m.runtime.is_experimental
    if experimental:
      gcs_bucket += "/experimental"

    gcs_args = []
    expanded_files = set(archive_data.files)
    for filename in archive_data.file_globs:
      for f in self.m.file.glob_paths(
          'expand file globs',
          base_path,
          filename,
          test_data=('glob1.txt', 'glob2.txt')):
        # Turn the returned Path object back into a string relative to
        # base_path.
        assert base_path.base == f.base
        assert base_path.is_parent_of(f)
        common_pieces = f.pieces[len(base_path.pieces):]
        expanded_files.add(os.path.sep.join(common_pieces))

    expanded_files = set(
        self._validate_paths('files', archive_data, base_path, expanded_files))

    # Copy all files to a temporary directory. Keeping the structure.
    # This directory will be used for archiving.
    temp_dir = self.m.path.mkdtemp()
    if archive_data.root_permission_override:
      self.m.step('Update temporary folder permissions', [
          'chmod',
          archive_data.root_permission_override,
          str(temp_dir),
      ])
    for filename in sorted(expanded_files):
      tmp_file_path = self.m.path.join(temp_dir, filename)
      tmp_file_dir = self.m.path.dirname(tmp_file_path)
      if str(tmp_file_dir) != str(temp_dir):
        self.m.file.ensure_directory(
            'Create temp dir %s' % os.path.dirname(filename), tmp_file_dir)
      self.m.file.copy(
          "Copy file %s" % filename,
          self.m.path.join(base_path, filename),
          tmp_file_path)

    updated_dirs = self._validate_paths(
        'directories', archive_data, base_path, list(archive_data.dirs))

    for directory in updated_dirs:
      self.m.file.copytree(
          "Copy folder %s" % directory,
          self.m.path.join(base_path, directory),
          self.m.path.join(temp_dir, directory),
          symlinks=True)

    # Starting here, we will only need to care about the temporary folder
    # which holds the files. So reset the base_path to temp_dir.
    base_path = temp_dir

    for rename_file in archive_data.rename_files:
      expanded_files.remove(rename_file.from_file)

      # Support placeholder replacement for file renames.
      new_filename = self._replace_placeholders(update_properties, custom_vars,
                                                rename_file.to_file)
      expanded_files.add(new_filename)
      self.m.file.move("Move file",
                       self.m.path.join(base_path, rename_file.from_file),
                       self.m.path.join(base_path, new_filename))

    root_rename = None
    for rename_dir in archive_data.rename_dirs:
      # Renaming the archive root is a special case which would affect other
      # renames, so save it until all the other renames are finished.
      if rename_dir.from_dir == '.':
        root_rename = rename_dir
        continue

      # Support placeholder replacement for renames.
      new_dirname = self._replace_placeholders(update_properties, custom_vars,
                                               rename_dir.to_dir)

      move_from_path = self.m.path.join(base_path, rename_dir.from_dir)
      for idx, dirname in enumerate(updated_dirs):
        if (dirname == rename_dir.from_dir or
            dirname.startswith(rename_dir.from_dir + self.m.path.sep)):
          updated_dirs[idx] = dirname.replace(rename_dir.from_dir,
                                              rename_dir.to_dir, 1)

      moved_files = {}
      for fn in expanded_files:
        if fn.startswith(rename_dir.from_dir + self.m.path.sep):
          moved_files[fn] = fn.replace(rename_dir.from_dir, rename_dir.to_dir,
                                       1)
      expanded_files = expanded_files.difference(moved_files.keys())
      expanded_files = expanded_files.union(moved_files.values())

      self.m.file.move(
          "Move dir: '%s'->'%s'" % (rename_dir.from_dir, new_dirname),
          move_from_path, self.m.path.join(base_path, new_dirname))

    if root_rename:
      # Handle special case of adding a prefix path to the archive dir (i.e.
      # moving the archive to a subdir of itself).
      # The archive dir is temporarily moved to a new path because you can't
      # actually move a dir into a subdir of itself.
      new_dirname = self._replace_placeholders(update_properties, custom_vars,
                                               root_rename.to_dir)
      move_from_path = self.m.path.mkdtemp().join(
          self.m.path.basename(base_path))
      self.m.file.move("Prep archive root move", base_path, move_from_path)
      self.m.file.move(
          "Move dir: '%s'->'%s'" % (root_rename.from_dir, new_dirname),
          move_from_path, self.m.path.join(base_path, new_dirname))
      # All files and need to be prefixed with the new root.
      expanded_files = set(
          self.m.path.join(new_dirname, fn) for fn in expanded_files)
      updated_dirs = [self.m.path.join(new_dirname, d) for d in updated_dirs]

    expanded_files = sorted(expanded_files)

    # Get map of local file path to upload -> destination file path in GCS
    # bucket.
    if archive_data.archive_type == ArchiveData.ARCHIVE_TYPE_FILES:
      if archive_data.dirs:
        self.m.step.empty(
            'ARCHIVE_TYPE_FILES does not support dirs',
            status=self.m.step.FAILURE,
            step_text=('archive_data properties with |archive_type| '
                       'ARCHIVE_TYPE_FILES must have empty |dirs|'))
      uploads = {
          base_path.join(f): _sanitize_gcs_path(gcs_path, f)
          for f in expanded_files
      }
    elif (archive_data.archive_type == ArchiveData.ARCHIVE_TYPE_FLATTEN_FILES):
      if archive_data.dirs:
        self.m.step.empty(
            'ARCHIVE_TYPE_FLATTEN_FILES does not support dirs',
            status=self.m.step.FAILURE,
            step_text=('archive_data properties with |archive_type| '
                       'ARCHIVE_TYPE_FLATTEN_FILES must have empty |dirs|'))
      uploads = {
          base_path.join(f): _sanitize_gcs_path(gcs_path,
                                                self.m.path.basename(f))
          for f in expanded_files
      }
    elif archive_data.archive_type == ArchiveData.ARCHIVE_TYPE_TAR_GZ:
      archive_file = self._create_targz_archive_for_upload(
          base_path, expanded_files, updated_dirs)
      uploads = {archive_file: gcs_path}
    elif archive_data.archive_type == ArchiveData.ARCHIVE_TYPE_RECURSIVE:
      if not archive_data.dirs:
        self.m.step.empty(
            'ARCHIVE_TYPE_RECURSIVE does not support empty dirs',
            status=self.m.step.FAILURE,
            step_text=('archive_data properties with |archive_type| '
                       'ARCHIVE_TYPE_RECURSIVE must specify |dirs|'))
      uploads = {base_path.join(d): gcs_path for d in updated_dirs}
      gcs_args += ['-R']
    elif archive_data.archive_type == ArchiveData.ARCHIVE_TYPE_SQUASHFS:
      archive_file = self.m.path.mkdtemp().join('image.squash')
      algorithm = None
      compression_level = None
      block_size = None
      if (archive_data.squashfs_params.algorithm == 'zstd' or
          archive_data.squashfs_algorithm == 'zstd'):
        if archive_data.squashfs_params.algorithm:
          algorithm = archive_data.squashfs_params.algorithm
        else:
          algorithm = archive_data.squashfs_algorithm
        # We just set compression_level to 22(highest).
        compression_level = 22
      if archive_data.squashfs_params.block_size:
        block_size = archive_data.squashfs_params.block_size
      self.m.squashfs.mksquashfs(base_path, archive_file, algorithm,
                                 compression_level, block_size)
      uploads = {archive_file: gcs_path}
    else:
      archive_file = self._create_zip_archive_for_upload(
          base_path, expanded_files, updated_dirs)
      uploads = {archive_file: gcs_path}

    # Report artifacts that require provenance.
    if (archive_data.requires_provenance and
        not archive_data.archive_type == ArchiveData.ARCHIVE_TYPE_RECURSIVE):

      for f in uploads.keys():
        # Report artifacts for provenance generation.
        file_hash = self.m.file.file_hash(f, test_data='deadbeef')
        # TODO(akashmukherjee): Add support for custom backend url.
        # Need to report full destination path of the artifact.
        if report_artifacts:
          self.m.bcid_reporter.report_gcs(
              file_hash, 'gs://%s/%s' % (gcs_bucket, uploads[f]))

    for file_path in uploads.keys():
      self.m.gsutil.upload(
          file_path,
          bucket=gcs_bucket,
          dest=uploads[file_path],
          args=gcs_args,
          name="upload {}".format(str(uploads[file_path])))

    if archive_data.HasField('latest_upload'):
      if (not archive_data.latest_upload.gcs_file_content or
          not archive_data.latest_upload.gcs_path):
        self.m.step.empty(
            ('latest_upload.gcs_path or latest_upload.gcs_file_content'
             ' not declared'),
            status=self.m.step.FAILURE,
            step_text=('Both latest_gcs_path and '
                       'latest_gcs_file_content must be non-empty.'))

      latest_path = self._replace_placeholders(
          update_properties, custom_vars, archive_data.latest_upload.gcs_path)
      content = self._replace_placeholders(
          update_properties, custom_vars,
          archive_data.latest_upload.gcs_file_content)

      if archive_data.latest_upload.gcs_bucket:
        latest_gcs_bucket = self._replace_placeholders(
            update_properties, custom_vars,
            archive_data.latest_upload.gcs_bucket)
      else:
        latest_gcs_bucket = gcs_bucket

      if '{%chromium_version%}' in archive_data.latest_upload.gcs_file_content:
        file_name = self.m.path.basename(latest_path)
        dest_path = self.m.path.mkdtemp().join(file_name)

        try:
          self.m.gsutil.download(
              bucket=latest_gcs_bucket, source=latest_path, dest=dest_path)
          last_version = self.m.file.read_text(
              'Read in last version', dest_path, test_data='1.2.3.4')
        except Exception:
          last_version = '0.0.0.0'

        last_versions = self._deconstruct_version(last_version)
        new_versions = self._deconstruct_version(content)

        for last, new in zip(last_versions, new_versions):
          if last > new:
            content = last_version
            break
          if new > last:
            break

      content_ascii = content.encode('ascii', 'ignore')
      temp_dir = self.m.path.mkdtemp()
      output_file = temp_dir.join('latest.txt')
      self.m.file.write_text('Write latest file', output_file, content_ascii)
      self.m.gsutil.upload(
          output_file,
          bucket=latest_gcs_bucket,
          dest=latest_path,
          name="upload {}/{}".format(latest_gcs_bucket, latest_path))

    # Generates a REVISIONS file
    if archive_data.HasField('revisions_file'):
      pattern = re.compile('^got_.*revision(_cp)?$')
      cp_pattern = re.compile('{#(\d*)}')
      content = {}
      for key, val in update_properties.items():
        if re.search(pattern, key):
          if key == 'got_v8_revision':
            content['v8_revision_git'] = val
          elif key == 'got_revision_cp':
            cp = re.search(cp_pattern, update_properties[key])
            content['chromium_revision'] = cp.group(1)
          elif key == 'got_v8_revision_cp':
            cp = re.search(cp_pattern, update_properties[key])
            content["v8_revision"] = cp.group(1)
          content[key] = val
      content_json = self.m.json.dumps(content)

      temp_dir = self.m.path.mkdtemp()
      output_file = temp_dir.join('revisions.txt')
      self.m.file.write_text('Write REVISIONS file', output_file, content_json)
      revisions_path = self._replace_placeholders(
          update_properties, custom_vars, archive_data.revisions_file.gcs_path)
      self.m.gsutil.upload(
          output_file,
          bucket=gcs_bucket,
          dest=revisions_path,
          name="upload {}".format(revisions_path))

    return uploads

  def cipd_archive(self, build_dir, update_properties, custom_vars,
                   cipd_archive_data, report_artifacts=False):
    """Archives packages to CIPD.

    Args:
      build_dir: The absolute path to the build output directory, e.g.
                 [slave-build]/src/out/Release
      update_properties: The properties from the bot_update step (containing
                         commit information).
      custom_vars: Dict of custom string substitution for value used in
                   pkg_vars and tags.
      cipd_archive_data: An instance of archive/properties.proto:
                         InputProperties.cipd_archive_datas.
    """
    refs = []
    for ref in cipd_archive_data.refs:
      refs.append(
          self._replace_placeholders(update_properties, custom_vars, ref))

    tags = dict(cipd_archive_data.tags)
    for key in tags:
      tags[key] = self._replace_placeholders(update_properties, custom_vars,
                                             tags[key])

    pkg_vars = dict(cipd_archive_data.pkg_vars)
    for key in pkg_vars:
      pkg_vars[key] = self._replace_placeholders(update_properties, custom_vars,
                                                 pkg_vars[key])

    compression_level = None
    if cipd_archive_data.HasField('compression'):
      compression_level = cipd_archive_data.compression.compression_level
    verification_timeout = None
    if cipd_archive_data.HasField('verification'):
      verification_timeout = cipd_archive_data.verification.verification_timeout

    pkg_refs = refs
    if cipd_archive_data.only_set_refs_on_tests_success:
      pkg_refs = None

    upload_results = {}
    for yaml_file in cipd_archive_data.yaml_files:
      pkg_def = build_dir.join(yaml_file)
      create_results = self.m.cipd.create_from_yaml(
          pkg_def=pkg_def,
          refs=pkg_refs,
          tags=tags,
          pkg_vars=pkg_vars,
          compression_level=compression_level,
          verification_timeout=verification_timeout)
      # Report artifact if provenance is desired.
      if report_artifacts:
        # CIPD instance id is encoded hash of the artifact, hash will be
        # extracted by the server if not reported.
        self.m.bcid_reporter.report_cipd(
            "", create_results[0], create_results[1])
      if cipd_archive_data.only_set_refs_on_tests_success:
        # Store info needed for setting refs through calling
        # generic_archive_after_tests.
        upload_results[create_results[0]] = {
            'refs': refs,
            'instance': create_results[1]
        }
    return upload_results
