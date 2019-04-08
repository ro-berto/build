#!/usr/bin/env python
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
                            'mojom-shared-internal.h')):
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
    # and an underscore. Union field tags are an uppercase version of the name,
    # hence the IGNORECASE flag.
    entity_name_match = re.search(
        r'\W((?:is|get|set|%s)?_?%s)(?:\W|$)' % (containing_name, entity_name),
        next_line,
        re.IGNORECASE)
    if not entity_name_match:
      # We should always find the entity, but don't fail completely if we don't.
      print "Couldn't find name after annotation in %s for %s, at offset %d" % (
          filename, signature, match.start(0))
      continue

    annotations.append(Annotation(signature, end + entity_name_match.start(1),
                        end + entity_name_match.end(1)))

  if verbose:
    print 'found %d annotations' % len(annotations)

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
                  'signature': annotation.signature,
                  'corpus': corpus
              },
              # The leading '%' indicates a reverse edge, which means from VName
              # to anchor.
              'edge': '%/kythe/edge/generates'
          }
          for annotation in annotations
      ]
  }


def _FormatMetadata(metadata):
  b64_metadata = base64.encodestring(json.dumps(metadata))

  # base64.encodedstring returns multi-line output. This is fine by us, as we
  # want to wrap the comment anyway. The first line will be longer than the rest
  # since we add the magic comment string, but we don't care too much about
  # prettiness of the output.
  return '// Metadata comment ' + b64_metadata[:-1].replace('\n', '\n// ')


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
      print 'Adding metadata to %s' % filename
    with open(filename, 'a+') as f:
      contents = f.read()
      metadata = _GenerateMetadata(filename, contents, opts.corpus,
                                   opts.verbose)

      # Python files are a thin wrapper around libc. As fopen(3) states:
      #   Note that ANSI C requires that a file positioning function
      #   intervene between output and input.
      # and indeed, on Windows any following writes will fail without this seek,
      # since we did a read() above.
      f.seek(0, os.SEEK_CUR)

      # read() already put us at the end of the file
      if contents[-1] != '\n':
        f.write('\n')

      # Leave a blank line before the metadata comment.
      f.write('\n')
      f.write(_FormatMetadata(metadata))


if '__main__' == __name__:
  sys.exit(main())
