# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import re
import sys
import os

# pylint: disable=relative-import
import manual_bisect_files
from PB.recipe_modules.build.archive.properties import ArchiveData
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
    super(ArchiveApi, self).__init__(**kwargs)

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
    args += self.m.build.slave_utils_args
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
    result = self.m.build.python(
        step_name,
        self.repo_resource('recipes', 'zip_build.py'),
        args,
        infra_step=True,
        **kwargs)
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
    if branch and branch != 'refs/heads/master':
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
    component is checked out in branch master with commit position number 234.

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
    filter_result = self.m.python(
        'filter build_dir',
        self.resource('filter_build_files.py'), [
            '--dir',
            build_dir,
            '--platform',
            self.m.platform.name,
            '--output',
            self.m.json.output(),
        ],
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

    self.m.build.python(
        'zipping',
        self.resource('zip_archive.py'), [
            staging_dir,
            zip_file_base_name,
            self.m.json.input(zip_file_list),
            build_dir,
        ],
        infra_step=True,
        **kwargs)

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
    args += self.m.build.slave_utils_args
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

    self.m.build.python(
        step_name,
        self.repo_resource('recipes', 'extract_build.py'),
        args,
        infra_step=True,
        **kwargs)

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
    zip_build.py, extract_build.py, slave_utils.py, and runtest.py
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

  def _replace_placeholders(self, update_properties, custom_vars, input_str):
    position_placeholder = '{%position%}'
    if position_placeholder in input_str:
      commit_position = self._get_commit_position(update_properties, None)
      if not commit_position:
        self.m.python.failing_step(
            'Missing position placeholder',
            'got_revision_cp or got_src_revision_cp is needed to populate '
            'the {%position%} placeholder')
      _, position = self.m.commit_position.parse(commit_position)
      input_str = input_str.replace(position_placeholder, str(position))

    arch_placeholder = '{%arch%}'
    if arch_placeholder in input_str:
      if (self.m.chromium.c.TARGET_ARCH == 'arm' and
          self.m.chromium.c.TARGET_BITS in (64, 32)):
        arch = 'arm' + str(self.m.chromium.c.TARGET_BITS)
      elif (self.m.chromium.c.TARGET_ARCH == 'intel' and
            self.m.chromium.c.TARGET_BITS == 64):
        arch = 'amd64'
      else:  # pragma: no cover
        api.python.failing_step(
            'Unresolved placeholder',
            'Unsupported value for arch placeholder: %s-%d' %
            (self.m.chromium.c.TARGET_ARCH, self.m.chromium.c.TARGET_BITS))
      input_str = input_str.replace(arch_placeholder, arch)

    commit_placeholder = '{%commit%}'
    if commit_placeholder in input_str:
      commit = self._get_git_commit(update_properties, None)
      if not commit:
        self.m.python.failing_step(
            'Missing commit placeholder',
            'got_revision is needed to populate the {%commit%} placeholder')
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
        if key in custom_vars.keys():
          input_str = input_str.replace(placeholder, custom_vars[key])
        else:
          self.m.python.failing_step('Unresolved placeholder',
                                     placeholder + ' can not be resolved')

    return input_str

  def generic_archive(self,
                      build_dir,
                      update_properties,
                      custom_vars=None,
                      config=None):
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
    """
    if config is None:
      config = self._default_config

    if not config.archive_datas and not config.cipd_archive_datas:
      return

    with self.m.step.nest('Generic Archiving Steps'):
      for archive_data in config.archive_datas:
        self.gcs_archive(build_dir, update_properties, archive_data,
                         custom_vars)
      for cipd_archive_data in config.cipd_archive_datas:
        self.cipd_archive(build_dir, update_properties, custom_vars,
                          cipd_archive_data)

  def gcs_archive(self,
                  build_dir,
                  update_properties,
                  archive_data,
                  custom_vars=None):
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

    gcs_bucket = archive_data.gcs_bucket
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
        expanded_files.add('/'.join(common_pieces))

    if archive_data.verifiable_key_path:
      sig_paths = set()
      # Immutable list of files to attach provenance.
      files_to_verify = set(expanded_files)
      for f in files_to_verify:
        # Files are relative to the base_path, so this generates the .sig
        # file next to the original.
        self.m.cloudkms.sign(archive_data.verifiable_key_path,
                             base_path.join(f), base_path.join(f + '.sig'))
        # This file path is appended directly to the provided gcs_path for
        # uploads. We'll uploaded this .sig next to the original
        # in GCS as well.
        sig_paths.add(f + '.sig')
      expanded_files = expanded_files.union(sig_paths)

      # Generates provenance to built artifacts at BCID L1. Note that this
      # does not record the top level source for the build.
      attestation_paths = set()
      provenance_manifest = {
          'recipe': self.m.properties.get('recipe'),
          'exp': 0,
      }
      for f in files_to_verify:
        # Files are relative to the base_path, so this generates the
        # .attestation file next to the original.
        file_hash = self.m.file.file_hash(
            base_path.join(f), test_data='deadbeef')
        provenance_manifest['subjectHash'] = file_hash
        temp_dir = self.m.path.mkdtemp('tmp')
        manifest_path = self.m.path.join(temp_dir, 'manifest.json')
        self.m.file.write_text('Provenance manifest', manifest_path,
                               json.dumps(provenance_manifest))
        self.m.provenance.generate(archive_data.verifiable_key_path,
                                   manifest_path,
                                   base_path.join(f + '.attestation'))
        # This file path is appended directly to the provided gcs_path for
        # uploads. We'll uploaded this .attestation next to the original
        # in GCS as well.
        attestation_paths.add(f + '.attestation')
      expanded_files = expanded_files.union(attestation_paths)

    # Copy all files to a temporary directory. Keeping the structure.
    # This directory will be used for archiving.
    temp_dir = self.m.path.mkdtemp()
    for filename in expanded_files:
      tmp_file_path = self.m.path.join(temp_dir, filename)
      tmp_file_dir = self.m.path.dirname(tmp_file_path)
      if str(tmp_file_dir) != str(temp_dir):
        self.m.file.ensure_directory(
            'Create temp dir %s' % os.path.dirname(filename), tmp_file_dir)
      self.m.file.copy("Copy file %s" % filename,
                       self.m.path.join(base_path, filename), tmp_file_path)

    for directory in archive_data.dirs:
      self.m.file.copytree("Copy folder %s" % directory,
                           self.m.path.join(base_path, directory),
                           self.m.path.join(temp_dir, directory))

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

    # Get map of local file path to upload -> destination file path in GCS
    # bucket.
    if archive_data.archive_type == ArchiveData.ARCHIVE_TYPE_FILES:
      if archive_data.dirs:
        self.m.python.failing_step(
            'ARCHIVE_TYPE_FILES does not support dirs',
            'archive_data properties with |archive_type| '
            'ARCHIVE_TYPE_FILES must have empty |dirs|')
      uploads = {
          base_path.join(f): _sanitize_gcs_path(gcs_path, f)
          for f in expanded_files
      }
    elif (archive_data.archive_type == ArchiveData.ARCHIVE_TYPE_FLATTEN_FILES):
      if archive_data.dirs:
        self.m.python.failing_step(
            'ARCHIVE_TYPE_FLATTEN_FILES does not support dirs',
            'archive_data properties with |archive_type| '
            'ARCHIVE_TYPE_FLATTEN_FILES must have empty |dirs|')
      uploads = {
          base_path.join(f): _sanitize_gcs_path(gcs_path,
                                                self.m.path.basename(f))
          for f in expanded_files
      }
    elif archive_data.archive_type == ArchiveData.ARCHIVE_TYPE_TAR_GZ:
      archive_file = self._create_targz_archive_for_upload(
          base_path, expanded_files, archive_data.dirs)
      uploads = {archive_file: gcs_path}
    elif archive_data.archive_type == ArchiveData.ARCHIVE_TYPE_RECURSIVE:
      if not archive_data.dirs:
        self.m.python.failing_step(
            'ARCHIVE_TYPE_RECURSIVE does not support '
            'empty dirs', 'archive_data properties with '
            '|archive_type| ARCHIVE_TYPE_RECURSIVE must '
            'specify |dirs|')
      uploads = {base_path.join(d): gcs_path for d in archive_data.dirs}
      gcs_args += ['-R']
    elif archive_data.archive_type == ArchiveData.ARCHIVE_TYPE_SQUASHFS:
      archive_file = self.m.path.mkdtemp().join('image.squash')
      self.m.squashfs.mksquashfs(base_path, archive_file)
      uploads = {archive_file: gcs_path}
    else:
      archive_file = self._create_zip_archive_for_upload(
          base_path, expanded_files, archive_data.dirs)
      uploads = {archive_file: gcs_path}

    for file_path in uploads:
      self.m.gsutil.upload(
          file_path,
          bucket=gcs_bucket,
          dest=uploads[file_path],
          args=gcs_args,
          name="upload {}".format(str(uploads[file_path])))

    if archive_data.HasField('latest_upload'):
      if (not archive_data.latest_upload.gcs_file_content or
          not archive_data.latest_upload.gcs_path):
        self.m.python.failing_step(
            'latest_upload.gcs_path or latest_upload.gcs_file_content'
            ' not declared', 'Both latest_gcs_path and '
            'latest_gcs_file_content must be non-empty.')
      content = self._replace_placeholders(
          update_properties, custom_vars,
          archive_data.latest_upload.gcs_file_content)
      content_ascii = content.encode('ascii', 'ignore')
      temp_dir = self.m.path.mkdtemp()
      output_file = temp_dir.join('latest.txt')
      self.m.file.write_text('Write latest file', output_file, content_ascii)
      self.m.gsutil.upload(
          output_file,
          bucket=gcs_bucket,
          dest=archive_data.latest_upload.gcs_path,
          name="upload {}".format(archive_data.latest_upload.gcs_path))

  def cipd_archive(self, build_dir, update_properties, custom_vars,
                   cipd_archive_data):
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

    for yaml_file in cipd_archive_data.yaml_files:
      pkg_def = self.m.path.abs_to_path(build_dir).join(yaml_file)
      self.m.cipd.create_from_yaml(
          pkg_def=pkg_def,
          refs=list(cipd_archive_data.refs),
          tags=tags,
          pkg_vars=pkg_vars,
          compression_level=compression_level)
