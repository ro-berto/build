#!/usr/bin/env vpython
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

import add_kythe_metadata

class AddKytheMetadataTest(unittest.TestCase):
  def _GenerateMetadata(self, contents):
    return add_kythe_metadata._GenerateMetadata('', contents, 'corpus', False)

  def testMetadataBasic(self):
    metadata = self._GenerateMetadata("""
@generated_from: Foobar
class Foobar {};
""")
    self.assertEqual({
        'type': 'kythe0',
        'meta': [
            {
                'type': 'anchor_defines',
                'begin': 31,
                'end': 37,
                'vname': {
                    'signature': 'Foobar',
                    'corpus': 'corpus',
                    'language': 'mojom',
                },
                'edge': '%/kythe/edge/generates',
            }
        ]}, metadata)

  def testMetadataNameInModule(self):
    metadata = self._GenerateMetadata("""
@generated_from: foo.mojom.Foobar
class Foobar {};
""")
    self.assertEqual({
        'type': 'kythe0',
        'meta': [
            {
                'type': 'anchor_defines',
                'begin': 41,
                'end': 47,
                'vname': {
                    'signature': 'foo.mojom.Foobar',
                    'corpus': 'corpus',
                    'language': 'mojom',
                },
                'edge': '%/kythe/edge/generates',
            }
        ]}, metadata)

  def testMetadataUnionAccessors(self):
    metadata = self._GenerateMetadata("""
@generated_from: Union.field
  bool is_field();

@generated_from: Union.field
  int get_field();

@generated_from: Union.field
  void set_field(int x);
""")
    self.assertEqual({
        'type': 'kythe0',
        'meta': [
            {
                'type': 'anchor_defines',
                'begin': 37,
                'end': 45,
                'vname': {
                    'signature': 'Union.field',
                    'corpus': 'corpus',
                    'language': 'mojom',
                },
                'edge': '%/kythe/edge/generates',
            },
            {
                'type': 'anchor_defines',
                'begin': 85,
                'end': 94,
                'vname': {
                    'signature': 'Union.field',
                    'corpus': 'corpus',
                    'language': 'mojom',
                },
                'edge': '%/kythe/edge/generates',
            },
            {
                'type': 'anchor_defines',
                'begin': 135,
                'end': 144,
                'vname': {
                    'signature': 'Union.field',
                    'corpus': 'corpus',
                    'language': 'mojom',
                },
                'edge': '%/kythe/edge/generates',
            }
        ]}, metadata)

  def testMetadataUnionTags(self):
    metadata = self._GenerateMetadata("""
@generated_from: Union.field_name
  FIELD_NAME,
""")
    self.assertEqual({
        'type': 'kythe0',
        'meta': [
            {
                'type': 'anchor_defines',
                'begin': 37,
                'end': 47,
                'vname': {
                    'signature': 'Union.field_name',
                    'corpus': 'corpus',
                    'language': 'mojom',
                },
                'edge': '%/kythe/edge/generates',
            }
        ]}, metadata)

  def testMetadataNestedTypes(self):
    metadata = self._GenerateMetadata("""
@generated_from: foo.mojom.Struct.Enum
enum Struct_Enum {};
""")
    self.assertEqual({
        'type': 'kythe0',
        'meta': [
            {
                'type': 'anchor_defines',
                'begin': 45,
                'end': 56,
                'vname': {
                    'signature': 'foo.mojom.Struct.Enum',
                    'corpus': 'corpus',
                    'language': 'mojom',
                },
                'edge': '%/kythe/edge/generates',
            }
        ]}, metadata)

  def testMetadataUsingStatement(self):
    metadata = self._GenerateMetadata("""
@generated_from: foo.mojom.Struct.Enum
  using Enum = Struct_Enum;
""")
    self.assertEqual({
        'type': 'kythe0',
        'meta': [
            {
                'type': 'anchor_defines',
                'begin': 48,
                'end': 52,
                'vname': {
                    'signature': 'foo.mojom.Struct.Enum',
                    'corpus': 'corpus',
                    'language': 'mojom',
                },
                'edge': '%/kythe/edge/generates',
            }
        ]}, metadata)

  def testMetadataMethod(self):
    metadata = self._GenerateMetadata("""
@generated_from: foo.mojom.Interface.Method
  virtual void Method(MethodArg a) = 0;
""")
    self.assertEqual({
        'type': 'kythe0',
        'meta': [
            {
                'type': 'anchor_defines',
                'begin': 60,
                'end': 66,
                'vname': {
                    'signature': 'foo.mojom.Interface.Method',
                    'corpus': 'corpus',
                    'language': 'mojom',
                },
                'edge': '%/kythe/edge/generates',
            }
        ]}, metadata)


  def testFormatMetadataSingleLine(self):
    self.assertEqual('// Metadata comment eyJmb28iOiAiYmFyIn0=',
                     add_kythe_metadata._FormatMetadata({'foo': 'bar'}))

  def testFormatMetadataMultiLine(self):
    self.assertEqual('// Metadata comment WyJhIiwgImEiLCAiYSIsICJhIiwgImEiLCA' +
                                 'iYSIsICJhIiwgImEiLCAiYSIsICJhIiwgImEiLCAi\n' +
                     '// YSIsICJhIiwgImEiLCAiYSIsICJhIiwgImEiLCAiYSIsICJhIiwg' +
                                                  'ImEiLCAiYSIsICJhIiwgImEi\n' +
                     '// LCAiYSIsICJhIiwgImEiLCAiYSIsICJhIiwgImEiLCAiYSJd',
                     add_kythe_metadata._FormatMetadata(['a'] * 30))

if __name__ == '__main__':
  unittest.main()
