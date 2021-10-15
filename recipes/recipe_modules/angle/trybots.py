# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.engine_types import freeze

from RECIPE_MODULES.build.chromium_tests_builder_config import try_spec


def _create_compile_spec(buildername):
  return try_spec.TrySpec.create_for_single_mirror(
      builder_group='angle',
      buildername=buildername,
      is_compile_only=True,
  )


# TODO(jmadill): De-duplicate. http://anglebug.com/6496
_SPEC = {
    'android-arm-compile':
        _create_compile_spec('android-arm-compile'),
    'android-arm-dbg':
        _create_compile_spec('android-arm-dbg'),
    'android-arm-dbg-compile':
        _create_compile_spec('android-arm-dbg-compile'),
    'android-arm-rel':
        _create_compile_spec('android-arm-rel'),
    'android-arm64-dbg':
        _create_compile_spec('android-arm64-dbg'),
    'android-arm64-dbg-compile':
        _create_compile_spec('android-arm64-dbg-compile'),
    'android-arm64-rel':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='android-arm64-rel',
                    tester='android-arm64-pixel4',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'android-arm64-test':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='android-arm64-test',
                    tester='android-arm64-pixel4',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'android-pixel4-perf':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='android-perf',
                    tester='android-arm64-pixel4-perf',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'linux-clang-dbg':
        _create_compile_spec('linux-clang-dbg'),
    'linux-clang-rel':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='linux-clang-rel',
                    tester='linux-intel',
                ),
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='linux-clang-rel',
                    tester='linux-nvidia',
                ),
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='linux-clang-rel',
                    tester='linux-swiftshader',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'linux-dbg-compile':
        _create_compile_spec('linux-dbg-compile'),
    'linux-gcc-dbg':
        _create_compile_spec('linux-gcc-dbg'),
    'linux-gcc-rel':
        _create_compile_spec('linux-gcc-rel'),
    'linux-intel-hd630-perf':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='linux-perf',
                    tester='linux-intel-perf',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'linux-nvidia-p400-perf':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='linux-perf',
                    tester='linux-nvidia-perf',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'linux-test':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='linux-test',
                    tester='linux-intel',
                ),
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='linux-test',
                    tester='linux-nvidia',
                ),
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='linux-test',
                    tester='linux-swiftshader',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'linux-trace':
        _create_compile_spec('linux-trace'),
    'linux-trace-rel':
        _create_compile_spec('linux-trace-rel'),
    'mac-dbg':
        _create_compile_spec('mac-dbg'),
    'mac-dbg-compile':
        _create_compile_spec('mac-dbg-compile'),
    'mac-rel':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='mac-rel',
                    tester='mac-amd',
                ),
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='mac-rel',
                    tester='mac-intel',
                ),
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='mac-rel',
                    tester='mac-nvidia',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'mac-test':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='mac-test',
                    tester='mac-amd',
                ),
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='mac-test',
                    tester='mac-intel',
                ),
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='mac-test',
                    tester='mac-nvidia',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'win-clang-x64-dbg':
        _create_compile_spec('win-clang-x64-dbg'),
    'win-clang-x64-rel':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='win-clang-x64-rel',
                    tester='win10-x64-intel',
                ),
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='win-clang-x64-rel',
                    tester='win10-x64-nvidia',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'win-clang-x86-dbg':
        _create_compile_spec('win-clang-x86-dbg'),
    'win-clang-x86-rel':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='win-clang-x86-rel',
                    tester='win7-x86-amd',
                ),
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='win-clang-x86-rel',
                    tester='win10-x86-swiftshader',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'win-dbg-compile':
        _create_compile_spec('win-dbg-compile'),
    'win-msvc-compile':
        _create_compile_spec('win-msvc-compile'),
    'win-msvc-dbg-compile':
        _create_compile_spec('win-msvc-dbg-compile'),
    'win-msvc-x64-dbg':
        _create_compile_spec('win-msvc-x64-dbg'),
    'win-msvc-x64-rel':
        _create_compile_spec('win-msvc-x64-rel'),
    'win-msvc-x86-compile':
        _create_compile_spec('win-msvc-x86-compile'),
    'win-msvc-x86-dbg':
        _create_compile_spec('win-msvc-x86-dbg'),
    'win-msvc-x86-dbg-compile':
        _create_compile_spec('win-msvc-x86-dbg-compile'),
    'win-msvc-x86-rel':
        _create_compile_spec('win-msvc-x86-rel'),
    'win-test':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='win-test',
                    tester='win10-x64-intel',
                ),
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='win-test',
                    tester='win10-x64-nvidia',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'win-x86-dbg-compile':
        _create_compile_spec('win-x86-dbg-compile'),
    'win-x86-test':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='win-x86-test',
                    tester='win7-x86-amd',
                ),
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='win-x86-test',
                    tester='win10-x86-swiftshader',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'win10-intel-hd630-perf':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='win-perf',
                    tester='win10-x64-intel-perf',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'win10-nvidia-p400-perf':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='win-perf',
                    tester='win10-x64-nvidia-perf',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'win-trace':
        _create_compile_spec('win-trace'),
    'win-trace-rel':
        _create_compile_spec('win-trace-rel'),
    'winuwp-compile':
        _create_compile_spec('winuwp-compile'),
    'winuwp-dbg-compile':
        _create_compile_spec('winuwp-dbg-compile'),
    'winuwp-x64-dbg':
        _create_compile_spec('winuwp-x64-dbg'),
    'winuwp-x64-rel':
        _create_compile_spec('winuwp-x64-rel'),
}

TRYBOTS = try_spec.TryDatabase.create({
    'angle': _SPEC,
})
