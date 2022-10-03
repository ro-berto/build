#!/usr/bin/env python3
# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool which turns annotations into Kythe metadata.

These annotations are inserted by the Mojom compiler when the
"enable_kythe_annotations" gn arg is set. We use them to identify the locations
of identifiers in the generated file, and insert inline metadata tying these
locations to the name of the entity in the source Mojom file which generates
them.
"""

from __future__ import absolute_import
from __future__ import print_function

import argparse
import base64
import collections
import json
import os
import re
import sys

def _FindAllMojomGeneratedFiles(root_dir):
  for dirpath, _, filenames in os.walk(root_dir):
    for filename in filenames:
      if any(filename.endswith(suffix)
             for suffix in ('mojom.h', 'mojom-forward.h', 'mojom-shared.h',
                            'mojom-shared-internal.h', 'mojom-blink.h')):
        yield os.path.join(dirpath, filename)


def _GenerateMetadata(filename, file_contents, corpus, verbose):
  Annotation = collections.namedtuple('Annotation',
                                      ['signature', 'begin', 'end'])
  annotations = []
  for match in re.finditer(r'@generated_from: ([a-zA-Z0-9_.]*)$', file_contents,
                           re.MULTILINE):
    signature = match.group(1)
    components = signature.split('.')
    entity_name = components[-1]
    containing_name = components[-2] if len(components) >= 2 else ''

    end = match.end(0) + 1
    next_line = file_contents[end : file_contents.index('\n', end)]

    # Union fields produce methods with the name of the field preceded by "is_",
    # "get_" and "set_". Inner types are prefixed with the containing type name
    # and an underscore. InterfacePtr aliases have "Ptr" on the end. Union field
    # tags are an uppercase version of the name, hence the IGNORECASE flag.
    entity_name_match = re.search(
        r'\W((?:is|get|set|%s)?_?%s(?:Ptr)?)(?:\W|$)' %
            (containing_name, entity_name),
        next_line, re.IGNORECASE)
    if not entity_name_match:
      # We should always find the entity, but don't fail completely if we don't.
      print("Couldn't find name after annotation in %s for %s, at offset %d" %
            (filename, signature, match.start(0)))
      continue

    annotations.append(Annotation(signature, end + entity_name_match.start(1),
                        end + entity_name_match.end(1)))

  if verbose:
    print('found %d annotations' % len(annotations))

  return {
      # This has to be 'kythe0'. I guess it's a version number.
      'type': 'kythe0',
      'meta': [
          {
              # 'anchor_defines' maps from an anchor to a semantic node. The
              # resulting edge will be between the specified semantic node and
              # the semantic node which is defined by the anchor. So in our case
              # we have the semantic node of a Mojom object, and the location of
              # a C++ identifier in the generated code.
              'type': 'anchor_defines',
              'begin': annotation.begin,
              'end': annotation.end,
              'vname': {
                  'language': 'mojom',
                  'corpus': corpus,
                  'signature': annotation.signature,
              },
              # The leading '%' indicates a reverse edge, which means from VName
              # to anchor.
              'edge': '%/kythe/edge/generates'
          }
          for annotation in annotations
      ]
  }


def _FormatMetadata(metadata):
  b64_metadata = base64.encodestring(json.dumps(metadata).encode('utf-8'))

  # base64.encodedstring returns multi-line output. This is fine by us, as we
  # want to wrap the comment anyway.
  return '/* Metadata comment\n' + b64_metadata.decode('utf-8') + '*/'


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('gen_dir',
                      help='The generated output dir, which contains all the '
                           'Mojom generated files to add metadata to')
  parser.add_argument('--corpus',
                      default='chromium.googlesource.com/chromium/src',
                      help='The corpus to use in VNames in the metadata')
  parser.add_argument('--verbose', action='store_true')
  opts = parser.parse_args()

  for filename in _FindAllMojomGeneratedFiles(opts.gen_dir):
    if opts.verbose:
      print('Adding metadata to %s' % filename)
    with open(filename, 'a+') as f:
      # Depending on the OS and python version, "a+" will put the pointer
      # at the end of the file and without seek(), `contents` would be an
      # empty string.
      f.seek(0)
      contents = f.read()
      metadata = _GenerateMetadata(filename, contents, opts.corpus,
                                   opts.verbose)

      # Python files are a thin wrapper around libc. As fopen(3) states:
      #   Note that ANSI C requires that a file positioning function
      #   intervene between output and input.
      # and indeed, on Windows any following writes will fail without this seek,
      # since we did a read() above.
      f.seek(0, os.SEEK_CUR)

      # If there's already a metadata comment, this file is untouched since the
      # last time this script ran, and we still have the metadata we generated
      # last time. In this case we clear the existing metadata and generate new
      # metadata. In theory the metadata will be the same, since the file hasn't
      # changed. However, if this script has changed we want the output from
      # the new version rather than the old version, as it might be different.
      #
      # We search for both '//' and '/*' comment prefixes, to match both the
      # current output of this script, and the output from the previous version.
      match = re.search('\n/[/*] Metadata comment', contents)
      if match is not None:
        comment_pos = match.start()
        if opts.verbose:
          print('Clearing existing metadata from %s' % filename)
        f.seek(comment_pos)
        f.truncate()
        contents = contents[:comment_pos]

      # read() already put us at the end of the file
      if contents[-1] != '\n':
        f.write('\n')

      # Leave a blank line before the metadata comment.
      f.write('\n')
      f.write(_FormatMetadata(metadata))


if '__main__' == __name__:
  sys.exit(main())
