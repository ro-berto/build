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


_SPEC = {
    'android-arm-compile':
        _create_compile_spec('android-arm-compile'),
    'android-arm-dbg-compile':
        _create_compile_spec('android-arm-dbg-compile'),
    'android-arm64-dbg':
        _create_compile_spec('android-arm64-dbg'),
    'android-arm64-dbg-compile':
        _create_compile_spec('android-arm64-dbg-compile'),
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
    'android-arm64-exp-test':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='android-arm64-exp-test',
                    tester='android-arm64-pixel6',
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
    'linux-asan-test':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='linux-asan-test',
                    tester='linux-swiftshader-asan',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'linux-dbg-compile':
        _create_compile_spec('linux-dbg-compile'),
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
                    tester='linux-amd',
                ),
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
    'linux-tsan-test':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='linux-tsan-test',
                    tester='linux-swiftshader-tsan',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'linux-ubsan-test':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='linux-ubsan-test',
                    tester='linux-swiftshader-ubsan',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'linux-trace':
        _create_compile_spec('linux-trace'),
    'mac-dbg-compile':
        _create_compile_spec('mac-dbg-compile'),
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
    'mac-exp-test':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='mac-exp-test',
                    tester='mac-exp-amd',
                ),
            ],
            analyze_names=['angle'],
            retry_failed_shards=False,
        ),
    'win-asan-test':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='win-asan-test',
                    tester='win10-x64-swiftshader-asan',
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
    'win-msvc-x86-compile':
        _create_compile_spec('win-msvc-x86-compile'),
    'win-msvc-x86-dbg-compile':
        _create_compile_spec('win-msvc-x86-dbg-compile'),
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
    'winuwp-compile':
        _create_compile_spec('winuwp-compile'),
    'winuwp-dbg-compile':
        _create_compile_spec('winuwp-dbg-compile'),
}

TRYBOTS = try_spec.TryDatabase.create({
    'angle': _SPEC,
})
