# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

from RECIPE_MODULES.build.chromium_tests_builder_config import try_spec

_SPEC = {
    'linux-clang-rel':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='linux-builder',
                    tester='linux-intel',
                ),
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='linux-builder',
                    tester='linux-nvidia',
                ),
            ],
            retry_failed_shards=False,
        ),
    'mac-rel':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='mac-builder',
                    tester='mac-amd',
                ),
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='mac-builder',
                    tester='mac-intel',
                ),
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='mac-builder',
                    tester='mac-nvidia',
                ),
            ],
            retry_failed_shards=False,
        ),
    'win-clang-x64-rel':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='win-x64-builder',
                    tester='win10-x64-intel',
                ),
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='win-x64-builder',
                    tester='win10-x64-nvidia',
                ),
            ],
            retry_failed_shards=False,
        ),
    'win-clang-x86-rel':
        try_spec.TrySpec.create(
            mirrors=[
                try_spec.TryMirror.create(
                    builder_group='angle',
                    buildername='win-x86-builder',
                    tester='win7-x86-amd',
                ),
            ],
            retry_failed_shards=False,
        ),
}

TRYBOTS = try_spec.TryDatabase.create({
    'angle': _SPEC,
})
