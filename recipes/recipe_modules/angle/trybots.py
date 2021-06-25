# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

from RECIPE_MODULES.build.chromium_tests_builder_config import try_spec


def _create_compile_spec(buildername):
  return try_spec.TrySpec.create_for_single_mirror(
      builder_group='angle',
      buildername=buildername,
      execution_mode=try_spec.COMPILE,
  )


_SPEC = {
    'android-arm-dbg':
        _create_compile_spec('android-arm-dbg'),
    'android-arm-rel':
        _create_compile_spec('android-arm-rel'),
    'android-arm64-dbg':
        _create_compile_spec('android-arm-dbg'),
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
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'linux-gcc-dbg':
        _create_compile_spec('linux-gcc-dbg'),
    'linux-gcc-rel':
        _create_compile_spec('linux-gcc-rel'),
    'linux-trace-rel':
        _create_compile_spec('linux-trace-rel'),
    'mac-dbg':
        _create_compile_spec('mac-dbg'),
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
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'win-msvc-x64-dbg':
        _create_compile_spec('win-msvc-x64-dbg'),
    'win-msvc-x64-rel':
        _create_compile_spec('win-msvc-x64-rel'),
    'win-msvc-x86-dbg':
        _create_compile_spec('win-msvc-x86-dbg'),
    'win-msvc-x86-rel':
        _create_compile_spec('win-msvc-x86-rel'),
    'win-trace-rel':
        _create_compile_spec('win-trace-rel'),
    'winuwp-x64-dbg':
        _create_compile_spec('winuwp-x64-dbg'),
    'winuwp-x64-rel':
        _create_compile_spec('winuwp-x64-rel'),
}

TRYBOTS = try_spec.TryDatabase.create({
    'angle': _SPEC,
})
