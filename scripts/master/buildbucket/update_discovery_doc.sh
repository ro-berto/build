#!/bin/bash
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
curl 'https://cr-buildbucket.appspot.com/_ah/api/discovery/v1/apis/buildbucket/v1/rest' > $DIR/discovery_doc.json
