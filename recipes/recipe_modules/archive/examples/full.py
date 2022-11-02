# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime

from PB.recipe_modules.build.archive import properties
from recipe_engine import post_process


DEPS = [
    'archive',
    'build/chromium',
    'squashfs',
    'recipe_engine/assertions',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/runtime',
]

TEST_CHROME_VERSION = '''MAJOR=91
MINOR=0
BUILD=4711
PATCH=0'''

TEST_HASH_MAIN='5e3250aadda2b170692f8e762d43b7e8deadbeef'
TEST_COMMIT_POSITON_MAIN='refs/heads/B1@{#123456}'

TEST_HASH_COMPONENT='deadbeefdda2b170692f8e762d43b7e8e7a96686'
TEST_COMMIT_POSITON_COMPONENT='refs/heads/master@{#234}'


def RunSteps(api):

  if 'test_get_channel_name' in api.properties:
    api.assertions.assertEqual(
        api.properties.get('channel'), api.archive.get_channel_name())
    return

  if 'build_archive_url' in api.properties:
    api.archive.zip_and_upload_build(
        step_name='zip build',
        target=api.path['checkout'].join('/Release/out'))
    return

  if 'gcs_archive' in api.properties:
    api.chromium.set_config('chromium')

    build_dir = api.m.path.mkdtemp()
    api.path.mock_add_paths(build_dir.join('existing-dir'))
    api.path.mock_add_paths(build_dir.join('existing-file.json'))
    api.path.mock_add_paths(api.path['start_dir'].join('squashfs',
                                                       'squashfs-tools',
                                                       'mksquashfs'))
    update_properties = api.properties.get('update_properties')
    custom_vars = api.properties.get('custom_vars')
    upload_results = api.archive.generic_archive(
        build_dir=build_dir,
        update_properties=update_properties,
        custom_vars=custom_vars,
        report_artifacts=True)
    api.archive.generic_archive_after_tests(
        build_dir=build_dir, upload_results=upload_results, test_success=True)
    return

  if 'no_llvm' not in api.properties:
    llvm_bin_dir = api.path['checkout'].join('third_party', 'llvm-build',
                                             'Release+Asserts', 'bin')
    api.path.mock_add_paths(api.path.join(llvm_bin_dir, 'llvm-symbolizer'))
    api.path.mock_add_paths(api.path.join(llvm_bin_dir, 'sancov'))

    llvm_lib_dir = api.path['checkout'].join('third_party', 'llvm-build',
                                             'Release+Asserts', 'lib')
    api.path.mock_add_paths(api.path.join(llvm_lib_dir, 'libstdc++.so.6'))

  build_dir = api.path['start_dir'].join('src', 'out', 'Release')

  api.archive.clusterfuzz_archive(
      build_dir=build_dir,
      update_properties=api.properties.get('update_properties'),
      gs_bucket='chromium',
      gs_acl=api.properties.get('gs_acl', ''),
      archive_prefix='chrome-asan',
      archive_subdir_suffix=api.properties.get('archive_subdir_suffix', ''),
      revision_dir=api.properties.get('revision_dir'),
      primary_project=api.properties.get('primary_project'),
      bitness=api.properties.get('bitness'),
      build_config=api.properties.get('build_config'),
      use_legacy=api.properties.get('use_legacy', True),
      sortkey_datetime=api.properties.get('sortkey_datetime', None),
  )


def GenTests(api):
  update_properties = {
    'got_revision': TEST_HASH_MAIN,
    'got_revision_cp': TEST_COMMIT_POSITON_MAIN,
  }
  for platform, build_files in (
        ('win', ['chrome', 'icu.dat', 'lib', 'file.obj']),
        ('mac', ['chrome', 'icu.dat', 'pdfsqueeze']),
        ('linux', ['chrome', 'icu.dat', 'lib.host']),
      ):
    yield api.test(
        'cf_archiving_%s' % platform,
        api.platform(platform, 64),
        api.properties(
            update_properties=update_properties,
            gs_acl='public-read',
            archive_subdir_suffix='subdir',
        ),
        api.override_step_data('filter build_dir',
                               api.json.output(build_files)),
    )

  yield api.test(
      'cf_archiving_win64',
      api.platform('win', 64),
      api.properties(
          bitness=64,
          update_properties=update_properties,
          use_legacy=False,
      ),
      api.override_step_data('filter build_dir', api.json.output(['chrome'])),
  )

  yield api.test(
      'cf_archiving_win64_exp',
      api.platform('win', 64),
      api.properties(
          bitness=64,
          update_properties=update_properties,
          use_legacy=False,
      ),
      api.override_step_data('filter build_dir', api.json.output(['chrome'])),
      api.runtime(is_experimental=True),
  )

  # Overwrite the build config and ensure it is used in the GS archive name.
  def check_gs_url_equals(check, steps, expected):
    check('gsutil upload' in steps)
    check(expected == steps['gsutil upload'].cmd[-1])

  yield api.test(
      'custom_build_config',
      api.platform('linux', 64),
      api.properties(
          build_config='debease',
          update_properties=update_properties),
      api.post_process(
          check_gs_url_equals,
          'gs://chromium/linux-debease/'
          'chrome-asan-linux-debease-refs_heads_B1-123456.zip'),
      api.post_process(post_process.DropExpectation),
  )

  # A component build with git.
  update_properties = {
    'got_x10_revision': TEST_HASH_COMPONENT,
    'got_x10_revision_cp': TEST_COMMIT_POSITON_COMPONENT,
  }
  yield api.test(
      'cf_archiving_component',
      api.platform('linux', 64),
      api.properties(
          update_properties=update_properties,
          revision_dir='x10',
          primary_project='x10',
      ),
      api.override_step_data('filter build_dir',
                             api.json.output(['chrome', 'resources'])),
  )

  update_properties = {
    'got_revision': TEST_HASH_MAIN,
    'got_revision_cp': TEST_COMMIT_POSITON_MAIN,
  }
  yield api.test(
      'cf_archiving_no_llvm',
      api.platform('linux', 64),
      api.properties(
          update_properties=update_properties,
          no_llvm=True,
      ),
      api.override_step_data('filter build_dir', api.json.output(['chrome'])),
  )

  yield api.test(
      'zip_and_upload_custom_location',
      api.platform('linux', 64),
      api.properties(
          build_archive_url='gs://dummy-bucket/Linux Release/full-build.zip'),
  )

  update_properties = {
      'got_revision': TEST_HASH_MAIN,
  }
  yield api.test(
      'cf_archiving_with_sortkey_datetime',
      api.platform('linux', 64),
      api.properties(
          update_properties=update_properties,
          gs_acl='public-read',
          archive_subdir_suffix='subdir',
          sortkey_datetime=datetime.datetime.utcfromtimestamp(100),
      ),
      api.override_step_data('filter build_dir',
                             api.json.output(['chrome', 'resources'])),
  )

  def check_stdin(check, step_odict, step, included_args, excluded_args=None):
    for included_arg in included_args:
      check('stdin for step %s contained %s' % (step, included_arg),
            included_arg in step_odict[step].stdin)
    excluded_args = excluded_args or []
    for excluded_arg in excluded_args:
      check('stdin for step %s did not contain %s' % (step, excluded_arg),
            excluded_arg not in step_odict[step].stdin)

  for archive_type, archive_filename, include_dirs in (
      (properties.ArchiveData.ARCHIVE_TYPE_UNSPECIFIED, 'any-path.zip', True),
      (properties.ArchiveData.ARCHIVE_TYPE_ZIP, 'any-path.zip', True),
      (properties.ArchiveData.ARCHIVE_TYPE_FILES, '', False),
      (properties.ArchiveData.ARCHIVE_TYPE_FLATTEN_FILES, '', False),
      (properties.ArchiveData.ARCHIVE_TYPE_TAR_GZ, 'any-path.tar.gz', True),
      (properties.ArchiveData.ARCHIVE_TYPE_SQUASHFS, 'any-path.squash', True),
      (properties.ArchiveData.ARCHIVE_TYPE_RECURSIVE, '', True),
  ):
    input_properties = properties.InputProperties()
    archive_data = properties.ArchiveData()
    archive_data.files.extend([
        'folder1/chrome',
        'folder2/snapshot_blob.bin',
        'before_rename_file',
    ])
    if include_dirs:
      archive_data.dirs.extend([
          'directory1',
          'directory2',
          'path/to/directory3',
          'locales',
          'swiftshader',
      ])
      rename_dir = properties.ArchiveDirRename()
      rename_dir.from_dir = "directory1"
      rename_dir.to_dir = "dir/one"
      archive_data.rename_dirs.extend([rename_dir])
      rename_partial_dir = properties.ArchiveDirRename()
      rename_partial_dir.from_dir = "path/to"
      rename_partial_dir.to_dir = "path_to"
      archive_data.rename_dirs.extend([rename_partial_dir])
      rename_root = properties.ArchiveDirRename()
      rename_root.from_dir = "."
      rename_root.to_dir = "archive_root"
      archive_data.rename_dirs.extend([rename_root])
    rename_file = properties.ArchiveFileRename()
    rename_file.from_file = "before_rename_file"
    rename_file.to_file = "after_rename_file_{%timestamp%}"
    archive_data.rename_files.extend([rename_file])
    # archive_data.rename_dirs should be able to modify any dir, not just those
    # added by archive_data.dirs.
    rename_file_dir = properties.ArchiveDirRename()
    rename_file_dir.from_dir = "folder1"
    rename_file_dir.to_dir = "folder_one"
    archive_data.rename_dirs.extend([rename_file_dir])
    archive_data.file_globs.append('glob*.txt')
    archive_data.gcs_bucket = 'any-bucket'
    archive_data.gcs_path = ('{%position%}/{%commit%}/{%timestamp%}/'
                             '{%chromium_version%}' + archive_filename)
    archive_data.archive_type = archive_type
    archive_data.root_permission_override = "755"
    input_properties.archive_datas.extend([archive_data])

    def add_directory_checks():
      post_tests = []
      if include_dirs:
        post_tests.append(
            api.post_process(
                post_process.StepCommandContains,
                "Generic Archiving Steps.Copy folder directory1", [
                    "copytree", "--symlinks", "[CLEANUP]/tmp_tmp_1/directory1",
                    "[CLEANUP]/tmp_tmp_2/directory1"
                ]))
        post_tests.append(
            api.post_process(
                post_process.StepCommandContains,
                "Generic Archiving Steps.Copy folder directory2", [
                    "copytree", "--symlinks", "[CLEANUP]/tmp_tmp_1/directory2",
                    "[CLEANUP]/tmp_tmp_2/directory2"
                ]))
        post_tests.append(
            api.post_process(
                post_process.StepCommandContains,
                "Generic Archiving Steps.Copy folder path/to/directory3", [
                    "copytree", "--symlinks",
                    "[CLEANUP]/tmp_tmp_1/path/to/directory3",
                    "[CLEANUP]/tmp_tmp_2/path/to/directory3"
                ]))
        post_tests.append(
            api.post_process(
                post_process.StepCommandContains,
                "Generic Archiving Steps.Move dir: 'directory1'->'dir/one'", [
                    "move", "[CLEANUP]/tmp_tmp_2/directory1",
                    "[CLEANUP]/tmp_tmp_2/dir/one"
                ]))
        post_tests.append(
            api.post_process(
                post_process.StepCommandContains,
                "Generic Archiving Steps.Move dir: 'path/to'->'path_to'", [
                    "move", "[CLEANUP]/tmp_tmp_2/path/to",
                    "[CLEANUP]/tmp_tmp_2/path_to"
                ]))
        post_tests.append(
            api.post_process(
                post_process.StepCommandContains,
                "Generic Archiving Steps.Move dir: '.'->'archive_root'",
                [
                    # NOTE: A "root move" involves moving the original archive
                    # dir to a temp dir before the final move, thus the new
                    # 'tmp_tmp_3' in the path.
                    "move",
                    "[CLEANUP]/tmp_tmp_3/tmp_tmp_2",
                    "[CLEANUP]/tmp_tmp_2/archive_root"
                ]))
      return sum(post_tests, api.empty_test_data())

    def add_naming_checks(archive_type):
      post_tests = []
      # Verify that renamed files/dirs are referenced by their new names in
      # relevant archiving steps.
      if archive_type in [
          properties.ArchiveData.ARCHIVE_TYPE_UNSPECIFIED,
          properties.ArchiveData.ARCHIVE_TYPE_ZIP,
      ]:
        post_tests.append(
            api.post_process(
                check_stdin, "Generic Archiving Steps.Create generic archive", [
                    "archive_root/after_rename_file_20120514125323",
                    "[CLEANUP]/tmp_tmp_2/archive_root/folder_one/chrome",
                    "[CLEANUP]/tmp_tmp_2/archive_root/dir/one",
                    "[CLEANUP]/tmp_tmp_2/archive_root/path_to/directory3",
                ]))
      if archive_type in [
          properties.ArchiveData.ARCHIVE_TYPE_FILES,
          properties.ArchiveData.ARCHIVE_TYPE_FLATTEN_FILES,
      ]:
        post_tests.append(
            api.post_process(
                post_process.StepCommandContains,
                "Generic Archiving Steps.gsutil upload 123456/5e3250aadda2b17"
                "0692f8e762d43b7e8deadbeef/20120514125321/51.0.2704.0/"
                "after_rename_file_20120514125323", [
                    "cp",
                    "[CLEANUP]/tmp_tmp_2/after_rename_file_20120514125323",
                ]))
      if archive_type in [
          properties.ArchiveData.ARCHIVE_TYPE_TAR_GZ,
      ]:
        post_tests.append(
            api.post_process(
                check_stdin, "Generic Archiving Steps.Create tar.gz archive", [
                    "archive_root/after_rename_file_20120514125323",
                    "[CLEANUP]/tmp_tmp_2/archive_root/folder_one/chrome",
                    "[CLEANUP]/tmp_tmp_2/archive_root/dir/one",
                    "[CLEANUP]/tmp_tmp_2/archive_root/path_to/directory3",
                ]))
      if archive_type in [
          properties.ArchiveData.ARCHIVE_TYPE_RECURSIVE,
      ]:
        post_tests.append(
            api.post_process(
                post_process.StepCommandContains,
                "Generic Archiving Steps.gsutil upload 123456/5e3250aadda2b"
                "170692f8e762d43b7e8deadbeef/20120514125321/51.0.2704.0", [
                    "cp",
                    "-R",
                    "[CLEANUP]/tmp_tmp_2/archive_root/dir/one",
                ]))
      return sum(post_tests, api.empty_test_data())

    yield api.test(
        'generic_archive_{}'.format(archive_type),
        api.properties(
            gcs_archive=True,
            update_properties={
                'got_revision': TEST_HASH_MAIN,
                'got_revision_cp': TEST_COMMIT_POSITON_MAIN,
            },
            **{'$build/archive': input_properties}),
        api.post_process(post_process.StatusSuccess),
        api.post_process(
            post_process.StepCommandContains,
            "Generic Archiving Steps.Move file", [
                "move", "[CLEANUP]/tmp_tmp_2/before_rename_file",
                "[CLEANUP]/tmp_tmp_2/after_rename_file_20120514125323"
            ]),
        api.post_process(
            post_process.StepCommandContains,
            "Generic Archiving Steps.Update temporary folder permissions",
            ["chmod", "755", "[CLEANUP]/tmp_tmp_2"]),
        api.post_process(
            post_process.StepCommandContains,
            "Generic Archiving Steps.Move dir: 'folder1'->'folder_one'", [
                "move", "[CLEANUP]/tmp_tmp_2/folder1",
                "[CLEANUP]/tmp_tmp_2/folder_one"
            ]),
        add_directory_checks(),
        add_naming_checks(archive_type),
        api.post_process(post_process.DropExpectation),
    )

    yield api.test(
        'generic_archive_missing_got_revision_cp_{}'.format(archive_type),
        api.properties(
            gcs_archive=True,
            update_properties={
                'got_revision': TEST_HASH_MAIN,
            },
            **{'$build/archive': input_properties}),
        api.post_process(post_process.StatusFailure),
        api.post_process(post_process.DropExpectation),
    )

    yield api.test(
        'generic_archive_missing_got_revision_{}'.format(archive_type),
        api.properties(
            gcs_archive=True,
            update_properties={
                'got_revision_cp': TEST_COMMIT_POSITON_MAIN,
            },
            **{'$build/archive': input_properties}),
        api.post_process(post_process.StatusFailure),
        api.post_process(post_process.DropExpectation),
    )

  yield api.test(
      'generic_archive_nothing_to_archive',
      api.properties(
          gcs_archive=True, update_properties={}, **{'$build/archive': {}}),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  input_properties = properties.InputProperties()
  archive_data = properties.ArchiveData()
  archive_data.dirs.extend(['anydir'])
  archive_data.gcs_bucket = 'any-bucket'
  archive_data.gcs_path = 'x86/{%position%}_{%commit%}_{%timestamp%}/chrome'
  archive_data.archive_type = properties.ArchiveData.ARCHIVE_TYPE_ZIP
  archive_data.latest_upload.gcs_path = "x86/latest/latest.txt"
  archive_data.latest_upload.gcs_file_content = \
      '{%position%}_{%commit%}_{%timestamp%}'
  archive_data.only_upload_on_tests_success = True
  input_properties.archive_datas.extend([archive_data])

  yield api.test(
      'generic_archive_with_update_latest',
      api.properties(
          gcs_archive=True,
          update_properties={
              'got_revision': TEST_HASH_MAIN,
              'got_revision_cp': TEST_COMMIT_POSITON_MAIN,
          },
          **{'$build/archive': input_properties}),
      api.post_process(
          post_process.StepCommandContains,
          'Generic Archiving Steps After Tests.Write latest file',
          ['123456_5e3250aadda2b170692f8e762d43b7e8deadbeef_'
           '20120514125323']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  input_properties = properties.InputProperties()
  archive_data = properties.ArchiveData()
  archive_data.dirs.extend(['missing-dir', 'existing-dir'])
  archive_data.files.extend(['missing-file.json', 'existing-file.json'])
  archive_data.archive_type = properties.ArchiveData.ARCHIVE_TYPE_ZIP
  archive_data.skip_empty_source = True
  input_properties.archive_datas.extend([archive_data])

  yield api.test(
      'generic_archive_skip_empty_sources',
      api.properties(
          gcs_archive=True,
          update_properties={
              'got_revision': TEST_HASH_MAIN,
              'got_revision_cp': TEST_COMMIT_POSITON_MAIN,
          },
          **{'$build/archive': input_properties}),
      api.post_process(
          post_process.MustRun,
          'Generic Archiving Steps.Copy file existing-file.json'),
      api.post_process(
          post_process.MustRun,
          'Generic Archiving Steps.Copy folder existing-dir'),
      api.post_process(
          post_process.DoesNotRun,
          'Generic Archiving Steps.Copy file missing-file.json'),
      api.post_process(
          post_process.DoesNotRun,
          'Generic Archiving Steps.Copy folder missing-dir'),
      api.post_process(
          check_stdin, 'Generic Archiving Steps.Create generic archive', [
              '[CLEANUP]/tmp_tmp_2/existing-file.json',
              '[CLEANUP]/tmp_tmp_2/existing-dir',
          ], [
              '[CLEANUP]/tmp_tmp_2/missing-file.json',
              '[CLEANUP]/tmp_tmp_2/missing-dir',
          ]),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  input_properties = properties.InputProperties()
  archive_data = properties.ArchiveData()
  archive_data.files.extend(['missing-file.json', 'existing-file.json'])
  archive_data.archive_type = properties.ArchiveData.ARCHIVE_TYPE_ZIP
  input_properties.archive_datas.extend([archive_data])

  yield api.test(
      'generic_archive_fail_missing_files',
      api.properties(
          gcs_archive=True,
          update_properties={
              'got_revision': TEST_HASH_MAIN,
              'got_revision_cp': TEST_COMMIT_POSITON_MAIN,
          },
          **{'$build/archive': input_properties}),
      api.post_process(post_process.StepFailure,
                       'Generic Archiving Steps.Validate files'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  input_properties = properties.InputProperties()
  archive_data = properties.ArchiveData()
  archive_data.dirs.extend(['missing-dir', 'existing-dir'])
  archive_data.archive_type = properties.ArchiveData.ARCHIVE_TYPE_ZIP
  input_properties.archive_datas.extend([archive_data])

  yield api.test(
      'generic_archive_fail_missing_dirs',
      api.properties(
          gcs_archive=True,
          update_properties={
              'got_revision': TEST_HASH_MAIN,
              'got_revision_cp': TEST_COMMIT_POSITON_MAIN,
          },
          **{'$build/archive': input_properties}),
      api.post_process(post_process.StepFailure,
                       'Generic Archiving Steps.Validate directories'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  input_properties = properties.InputProperties()
  archive_data = properties.ArchiveData()
  archive_data.dirs.extend(['anydir'])
  archive_data.gcs_bucket = 'any-bucket'
  archive_data.gcs_path = ('x86/{%position%}_{%commit%}_{%timestamp%}_'
                           '{%builder_name%}_{%build_number%}/chrome')
  archive_data.archive_type = properties.ArchiveData.ARCHIVE_TYPE_ZIP
  archive_data.latest_upload.gcs_path = "x86/latest/latest.txt"
  input_properties.archive_datas.extend([archive_data])

  yield api.test(
      'generic_archive_no_latest_gcs_content',
      api.properties(
          gcs_archive=True,
          update_properties={
              'got_revision': TEST_HASH_MAIN,
              'got_revision_cp': TEST_COMMIT_POSITON_MAIN,
          },
          **{'$build/archive': input_properties}),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  input_properties = properties.InputProperties()
  archive_data = properties.ArchiveData()
  archive_data.dirs.extend(['anydir'])
  archive_data.gcs_bucket = 'any-bucket'
  archive_data.gcs_path = 'x86/{%position%}/chrome'
  archive_data.archive_type = properties.ArchiveData.ARCHIVE_TYPE_ZIP
  archive_data.revisions_file.gcs_path = 'x86/{%position%}/REVISIONS'
  input_properties.archive_datas.extend([archive_data])

  yield api.test(
      'generic_archive_with_revisions_file',
      api.properties(
          gcs_archive=True,
          update_properties={
              'got_revision': TEST_HASH_MAIN,
              'got_revision_cp': TEST_COMMIT_POSITON_MAIN,
              'got_v8_revision': '466dd2d77f6dd56a9174d7389e788cb7367d818d',
              'got_v8_revision_cp': 'refs/heads/9.7.48@{#1}'
          },
          **{'$build/archive': input_properties}),
      api.post_process(
          post_process.StepCommandContains,
          'Generic Archiving Steps.Write REVISIONS file', [
              '{\"chromium_revision\": \"123456\", \"got_revision\": \"5e3250a'
              'adda2b170692f8e762d43b7e8deadbeef\", \"got_revision_cp\": '
              '\"refs/heads/B1@{#123456}\", \"got_v8_revision\": \"466dd2d77f6'
              'dd56a9174d7389e788cb7367d818d\", \"got_v8_revision_cp\": \"refs'
              '/heads/9.7.48@{#1}\", \"v8_revision\": \"1\", \"v8_revision_'
              'git\": \"466dd2d77f6dd56a9174d7389e788cb7367d818d\"}'
          ]),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  input_properties = properties.InputProperties()
  archive_data = properties.ArchiveData()
  archive_data.dirs.extend(['anydir'])
  archive_data.gcs_bucket = 'any-bucket'
  archive_data.gcs_path = 'x86/{%position%}/chrome'
  archive_data.archive_type = properties.ArchiveData.ARCHIVE_TYPE_SQUASHFS
  archive_data.squashfs_params.algorithm = 'zstd'
  archive_data.squashfs_params.block_size = '256K'
  archive_data.revisions_file.gcs_path = 'x86/{%position%}/REVISIONS'
  input_properties.archive_datas.extend([archive_data])

  yield api.test(
      'generic_archive_squashfs_with_compression_algorithm',
      api.properties(
          gcs_archive=True,
          update_properties={
              'got_revision': TEST_HASH_MAIN,
              'got_revision_cp': TEST_COMMIT_POSITON_MAIN,
              'got_v8_revision': '466dd2d77f6dd56a9174d7389e788cb7367d818d',
              'got_v8_revision_cp': 'refs/heads/9.7.48@{#1}'
          },
          **{'$build/archive': input_properties}),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  input_properties = properties.InputProperties()
  archive_data = properties.ArchiveData()
  archive_data.dirs.extend(['anydir'])
  archive_data.gcs_bucket = 'any-bucket'
  archive_data.gcs_path = 'x86/{%position%}/chrome'
  archive_data.archive_type = properties.ArchiveData.ARCHIVE_TYPE_SQUASHFS
  archive_data.squashfs_algorithm = 'zstd'
  archive_data.revisions_file.gcs_path = 'x86/{%position%}/REVISIONS'
  input_properties.archive_datas.extend([archive_data])

  yield api.test(
      'generic_archive_squashfs_with_compression_algorithm_deprecated',
      api.properties(
          gcs_archive=True,
          update_properties={
              'got_revision': TEST_HASH_MAIN,
              'got_revision_cp': TEST_COMMIT_POSITON_MAIN,
              'got_v8_revision': '466dd2d77f6dd56a9174d7389e788cb7367d818d',
              'got_v8_revision_cp': 'refs/heads/9.7.48@{#1}'
          },
          **{'$build/archive': input_properties}),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  input_properties = properties.InputProperties()
  archive_data = properties.ArchiveData()
  archive_data.dirs.extend(['anydir'])
  archive_data.gcs_bucket = 'any-bucket'
  archive_data.gcs_path = 'x86/{%chrome_version%}/chrome'
  archive_data.archive_type = properties.ArchiveData.ARCHIVE_TYPE_ZIP
  input_properties.archive_datas.extend([archive_data])

  yield api.test(
      'generic_archive_with_custom_vars',
      api.properties(
          gcs_archive=True,
          update_properties={
              'got_revision': TEST_HASH_MAIN,
              'got_revision_cp': TEST_COMMIT_POSITON_MAIN,
          },
          custom_vars={
              'chrome_version': '1.2.3.4',
          },
          **{'$build/archive': input_properties}),
      api.post_process(post_process.DropExpectation),
  )

  input_properties = properties.InputProperties()
  archive_data = properties.ArchiveData()
  archive_data.dirs.extend(['anydir'])
  archive_data.gcs_bucket = 'any-bucket'
  archive_data.gcs_path = 'x86/{%wrong_placeholder%}/chrome'
  archive_data.archive_type = properties.ArchiveData.ARCHIVE_TYPE_ZIP
  input_properties.archive_datas.extend([archive_data])

  yield api.test(
      'generic_archive_with_wrong_custom_vars',
      api.properties(
          gcs_archive=True,
          update_properties={
              'got_revision': TEST_HASH_MAIN,
              'got_revision_cp': TEST_COMMIT_POSITON_MAIN,
          },
          custom_vars={
              'chrome_version': '1.2.3.4',
          },
          **{'$build/archive': input_properties}),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  input_properties = properties.InputProperties()
  archive_data = properties.ArchiveData()
  archive_data.dirs.extend(['anydir'])
  archive_data.gcs_bucket = '{%gcs_bucket%}'
  archive_data.gcs_path = 'x86/{%position%}/chrome'
  archive_data.archive_type = properties.ArchiveData.ARCHIVE_TYPE_ZIP
  input_properties.archive_datas.extend([archive_data])

  yield api.test(
      'generic_archive_with_custom_var_gcs_bucket',
      api.properties(
          gcs_archive=True,
          update_properties={
              'got_revision': TEST_HASH_MAIN,
              'got_revision_cp': TEST_COMMIT_POSITON_MAIN,
          },
          custom_vars={
              'gcs_bucket': 'foo',
          },
          **{'$build/archive': input_properties}),
      api.post_process(
          post_process.StepCommandContains,
          'Generic Archiving Steps.gsutil upload x86/123456/chrome',
          ['gs://foo/x86/123456/chrome']),
      api.post_process(post_process.DropExpectation),
  )

  input_properties = properties.InputProperties()
  archive_data = properties.ArchiveData()
  archive_data.dirs.extend(['anydir'])
  archive_data.gcs_bucket = 'any-bucket'
  archive_data.gcs_path = 'dest_dir/'
  archive_data.archive_type = properties.ArchiveData.ARCHIVE_TYPE_RECURSIVE
  input_properties.archive_datas.extend([archive_data])
  yield api.test(
      'Raw dir archive',
      api.properties(
          gcs_archive=True,
          update_properties={},
          **{'$build/archive': input_properties}),
      api.post_process(post_process.StepCommandContains,
                       'Generic Archiving Steps.gsutil upload dest_dir/',
                       ['-R']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  input_properties = properties.InputProperties()
  archive_data = properties.ArchiveData()
  archive_data.gcs_bucket = 'any-bucket'
  archive_data.gcs_path = 'dest_dir/'
  archive_data.archive_type = properties.ArchiveData.ARCHIVE_TYPE_RECURSIVE
  input_properties.archive_datas.extend([archive_data])
  yield api.test(
      'No dirs for ARCHIVE_TYPE_RECURSIVE',
      api.properties(
          gcs_archive=True,
          update_properties={},
          **{'$build/archive': input_properties}),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  for archive_type in [
      properties.ArchiveData.ARCHIVE_TYPE_FILES,
      properties.ArchiveData.ARCHIVE_TYPE_FLATTEN_FILES
  ]:
    input_properties = properties.InputProperties()
    archive_data = properties.ArchiveData()
    archive_data.dirs.extend(['anydir'])
    archive_data.gcs_bucket = 'any-bucket'
    archive_data.gcs_path = 'dest_dir/'
    archive_data.archive_type = archive_type
    input_properties.archive_datas.extend([archive_data])
    yield api.test(
        'generic_archive_dirs unsupported for %s' % archive_type,
        api.properties(
            gcs_archive=True,
            update_properties={},
            **{'$build/archive': input_properties}),
        api.post_process(post_process.StatusFailure),
        api.post_process(post_process.DropExpectation),
    )

  input_properties = properties.InputProperties(
      archive_datas=[
          {
              'files': ['path/to/some/file.txt'],
              'gcs_bucket': 'any-bucket',
              'gcs_path': 'dest_dir/',
              'archive_type': properties.ArchiveData.ARCHIVE_TYPE_FILES,
              'verifiable_key_path': '/path/to/some/key',
              'base_dir': 'src-internal',
          },
          {
              'files': ['path/to/file.txt', 'path/tp/file2.txt'],
              'gcs_bucket': 'any-bucket',
              'gcs_path': 'dest_dir/files.zip',
              'archive_type': properties.ArchiveData.ARCHIVE_TYPE_ZIP,
              'verifiable_key_path': '/path/to/some/key',
              'base_dir': 'src-internal',
          },
      ],)

  yield api.test(
      'experimental',
      api.runtime(is_experimental=True),
      api.properties(
          gcs_archive=True,
          update_properties={},
          **{'$build/archive': input_properties}),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  input_properties = properties.InputProperties()
  archive_data = properties.ArchiveData()
  archive_data.dirs.extend(['anydir'])
  archive_data.gcs_bucket = 'any-bucket'
  archive_data.gcs_path = 'x86//chrome'
  archive_data.archive_type = properties.ArchiveData.ARCHIVE_TYPE_ZIP
  archive_data.latest_upload.gcs_path = "x86/latest/latest.txt"
  archive_data.latest_upload.gcs_file_content = \
      '{%chromium_version%}'
  archive_data.latest_upload.gcs_bucket = 'latest-bucket'
  input_properties.archive_datas.extend([archive_data])

  yield api.test(
      'deconstruct_version',
      api.chromium.ci_build(builder='test'),
      api.properties(
          gcs_archive=True,
          update_properties={},
          **{'$build/archive': input_properties}),
      api.step_data('Generic Archiving Steps.get version',
                    api.file.read_text('MAJOR=0\nMINOR=0\nBUILD=0\nPATCH=0')),
      api.post_process(post_process.StepCommandContains,
                       'Generic Archiving Steps.Write latest file',
                       ['1.2.3.4']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'if_latest_gcs_bucket_set',
      api.chromium.ci_build(builder='test'),
      api.properties(
          gcs_archive=True,
          update_properties={},
          **{'$build/archive': input_properties}),
      api.step_data('Generic Archiving Steps.get version',
                    api.file.read_text('MAJOR=0\nMINOR=0\nBUILD=0\nPATCH=0')),
      api.post_process(post_process.StepCommandContains,
                       'Generic Archiving Steps.Write latest file',
                       ['1.2.3.4']),
      api.post_process(post_process.StepCommandContains,
                       'Generic Archiving Steps.gsutil upload '
                       'latest-bucket/x86/latest/latest.txt',
                       ['gs://latest-bucket/x86/latest/latest.txt']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'if_last_version_is_older',
      api.chromium.ci_build(builder='test'),
      api.properties(
          gcs_archive=True,
          update_properties={},
          **{'$build/archive': input_properties}),
      api.step_data('Generic Archiving Steps.get version',
                    api.file.read_text('MAJOR=90\nMINOR=1\nBUILD=2\nPATCH=3')),
      api.post_process(post_process.StepCommandContains,
                       'Generic Archiving Steps.Write latest file',
                       ['90.1.2.3']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'if_latest_path_does_not_exist',
      api.chromium.ci_build(builder='test'),
      api.properties(
          gcs_archive=True,
          update_properties={},
          **{'$build/archive': input_properties}),
      api.step_data('Generic Archiving Steps.gsutil download', retcode=1),
      api.step_data('Generic Archiving Steps.get version',
                    api.file.read_text('MAJOR=90\nMINOR=1\nBUILD=2\nPATCH=3')),
      api.post_process(post_process.StepCommandContains,
                       'Generic Archiving Steps.Write latest file',
                       ['90.1.2.3']),
      api.post_process(post_process.StepSuccess, 'Generic Archiving Steps'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'test_get_channel_name',
      api.properties(test_get_channel_name=True, channel='canary'),
      api.step_data('get version', api.file.read_text(TEST_CHROME_VERSION)),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))
