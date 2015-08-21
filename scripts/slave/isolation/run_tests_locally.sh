#!/bin/bash
# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

TMP_FILE=$(mktemp --tmpdir=.)
pwd
cd "$(dirname $0)"
pwd
./isolate_recipes.py $@ > $TMP_FILE
trap 'rm $TMP_FILE' EXIT
../../../../infra/luci/client/isolate.py run -i $TMP_FILE
