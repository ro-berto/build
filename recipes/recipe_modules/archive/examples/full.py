# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime

from PB.recipe_modules.build.archive import properties
from recipe_engine import post_process


DEPS = [
    'archive',
    'squashfs',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/runtime',
]

TEST_HASH_MAIN='5e3250aadda2b170692f8e762d43b7e8deadbeef'
TEST_COMMIT_POSITON_MAIN='refs/heads/B1@{#123456}'

TEST_HASH_COMPONENT='deadbeefdda2b170692f8e762d43b7e8e7a96686'
TEST_COMMIT_POSITON_COMPONENT='refs/heads/master@{#234}'


def RunSteps(api):
  if 'build_archive_url' in api.properties:
    api.archive.zip_and_upload_build(
        step_name='zip build',
        target=api.path['checkout'].join('/Release/out'))
    return

  if 'gcs_archive' in api.properties:
    api.path.mock_add_paths(api.path['start_dir'].join('squashfs',
                                                       'squashfs-tools',
                                                       'mksquashfs'))
    api.archive.generic_archive(
        build_dir=api.m.path.mkdtemp(),
        update_properties=api.properties.get('update_properties'),
        custom_vars=api.properties.get('custom_vars'))
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

  for archive_type, archive_filename, include_dirs in (
      (properties.ArchiveData.ARCHIVE_TYPE_UNSPECIFIED, 'any-path.zip', True),
      (properties.ArchiveData.ARCHIVE_TYPE_ZIP, 'any-path.zip', True),
      (properties.ArchiveData.ARCHIVE_TYPE_FILES, '', False),
      (properties.ArchiveData.ARCHIVE_TYPE_FLATTEN_FILES, '', False),
      (properties.ArchiveData.ARCHIVE_TYPE_TAR_GZ, 'any-path.tar.gz', True),
      (properties.ArchiveData.ARCHIVE_TYPE_SQUASHFS, 'any-path.squash', True),
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
      ])
    rename_file = properties.ArchiveFileRename()
    rename_file.from_file = "before_rename_file"
    rename_file.to_file = "after_rename_file_{%timestamp%}"
    archive_data.rename_files.extend([rename_file])
    archive_data.file_globs.append('glob*.txt')
    if include_dirs:
      archive_data.dirs.extend(['locales', 'swiftshader'])
    archive_data.gcs_bucket = 'any-bucket'
    archive_data.gcs_path = ('{%position%}/{%commit%}/{%timestamp%}/'
                             '{%chromium_version%}' + archive_filename)
    archive_data.archive_type = archive_type
    input_properties.archive_datas.extend([archive_data])

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
  input_properties.archive_datas.extend([archive_data])

  yield api.test(
      'generic_archive_{}_with_update_latest',
      api.properties(
          gcs_archive=True,
          update_properties={
              'got_revision': TEST_HASH_MAIN,
              'got_revision_cp': TEST_COMMIT_POSITON_MAIN,
          },
          **{'$build/archive': input_properties}),
      api.post_process(post_process.StatusSuccess),
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
      'generic_archive_{}_no_latest_gcs_content',
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
      archive_datas=[{
          'files': ['/path/to/some/file.txt'],
          'gcs_bucket': 'any-bucket',
          'gcs_path': 'dest_dir/',
          'archive_type': properties.ArchiveData.ARCHIVE_TYPE_FILES,
          'verifiable_key_path': '/path/to/some/key',
          'base_dir': 'src-internal',
      }],)
  yield api.test(
      'verifiable_key_path',
      api.properties(
          gcs_archive=True,
          update_properties={},
          **{'$build/archive': input_properties}),
      api.post_process(post_process.StepCommandContains,
                       'Generic Archiving Steps.sign', [
                           '-input',
                           '/path/to/some/file.txt',
                           '-output',
                           '/path/to/some/file.txt.sig',
                       ]),
      api.post_process(
          post_process.StepCommandContains,
          'Generic Archiving Steps.gsutil upload '
          'dest_dir/path/to/some/file.txt.sig', [
              '/path/to/some/file.txt.sig',
              'gs://any-bucket/dest_dir/path/to/some/file.txt.sig',
          ]),
      api.post_process(
          post_process.StepCommandContains,
          'Generic Archiving Steps.gsutil upload '
          'dest_dir/path/to/some/file.txt.attestation', [
              '/path/to/some/file.txt.attestation',
              'gs://any-bucket/dest_dir/path/to/some/file.txt.attestation',
          ]),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'experimental',
      api.runtime(is_experimental=True),
      api.properties(
          gcs_archive=True,
          update_properties={},
          **{'$build/archive': input_properties}),
      api.post_process(post_process.StepCommandContains,
                       'Generic Archiving Steps.sign', [
                           '-input',
                           '/path/to/some/file.txt',
                           '-output',
                           '/path/to/some/file.txt.sig',
                       ]),
      api.post_process(
          post_process.StepCommandContains,
          'Generic Archiving Steps.gsutil upload '
          'dest_dir/path/to/some/file.txt.sig', [
              '/path/to/some/file.txt.sig',
              'gs://any-bucket/experimental/dest_dir/path/to/some/file.txt.sig',
          ]),
      api.post_process(
          post_process.StepCommandContains,
          'Generic Archiving Steps.gsutil upload '
          'dest_dir/path/to/some/file.txt.attestation', [
              '/path/to/some/file.txt.attestation',
              ('gs://any-bucket/experimental/dest_dir/path/to/'
               'some/file.txt.attestation'),
          ]),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
