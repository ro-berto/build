# pylint: skip-file
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: kythe/proto/storage.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='kythe/proto/storage.proto',
  package='kythe.proto',
  syntax='proto3',
  serialized_options=_b('\n\037com.google.devtools.kythe.protoZ\020storage_go_proto'),
  serialized_pb=_b('\n\x19kythe/proto/storage.proto\x12\x0bkythe.proto\"X\n\x05VName\x12\x11\n\tsignature\x18\x01 \x01(\t\x12\x0e\n\x06\x63orpus\x18\x02 \x01(\t\x12\x0c\n\x04root\x18\x03 \x01(\t\x12\x0c\n\x04path\x18\x04 \x01(\t\x12\x10\n\x08language\x18\x05 \x01(\t\"\\\n\tVNameMask\x12\x11\n\tsignature\x18\x01 \x01(\x08\x12\x0e\n\x06\x63orpus\x18\x02 \x01(\x08\x12\x0c\n\x04root\x18\x03 \x01(\x08\x12\x0c\n\x04path\x18\x04 \x01(\x08\x12\x10\n\x08language\x18\x05 \x01(\x08\"\x89\x01\n\x05\x45ntry\x12\"\n\x06source\x18\x01 \x01(\x0b\x32\x12.kythe.proto.VName\x12\x11\n\tedge_kind\x18\x02 \x01(\t\x12\"\n\x06target\x18\x03 \x01(\x0b\x32\x12.kythe.proto.VName\x12\x11\n\tfact_name\x18\x04 \x01(\t\x12\x12\n\nfact_value\x18\x05 \x01(\x0c\".\n\x07\x45ntries\x12#\n\x07\x65ntries\x18\x01 \x03(\x0b\x32\x12.kythe.proto.Entry\"D\n\x0bReadRequest\x12\"\n\x06source\x18\x01 \x01(\x0b\x32\x12.kythe.proto.VName\x12\x11\n\tedge_kind\x18\x02 \x01(\t\"\xcc\x01\n\x0cWriteRequest\x12\"\n\x06source\x18\x01 \x01(\x0b\x32\x12.kythe.proto.VName\x12\x30\n\x06update\x18\x02 \x03(\x0b\x32 .kythe.proto.WriteRequest.Update\x1a\x66\n\x06Update\x12\x11\n\tedge_kind\x18\x01 \x01(\t\x12\"\n\x06target\x18\x02 \x01(\x0b\x32\x12.kythe.proto.VName\x12\x11\n\tfact_name\x18\x03 \x01(\t\x12\x12\n\nfact_value\x18\x04 \x01(\x0c\"\x0c\n\nWriteReply\"Y\n\x0bScanRequest\x12\"\n\x06target\x18\x01 \x01(\x0b\x32\x12.kythe.proto.VName\x12\x11\n\tedge_kind\x18\x02 \x01(\t\x12\x13\n\x0b\x66\x61\x63t_prefix\x18\x03 \x01(\t\"-\n\x0c\x43ountRequest\x12\r\n\x05index\x18\x01 \x01(\x03\x12\x0e\n\x06shards\x18\x02 \x01(\x03\"\x1d\n\nCountReply\x12\x0f\n\x07\x65ntries\x18\x01 \x01(\x03\"-\n\x0cShardRequest\x12\r\n\x05index\x18\x01 \x01(\x03\x12\x0e\n\x06shards\x18\x02 \x01(\x03\x42\x33\n\x1f\x63om.google.devtools.kythe.protoZ\x10storage_go_protob\x06proto3')
)




_VNAME = _descriptor.Descriptor(
  name='VName',
  full_name='kythe.proto.VName',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='signature', full_name='kythe.proto.VName.signature', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='corpus', full_name='kythe.proto.VName.corpus', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='root', full_name='kythe.proto.VName.root', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='path', full_name='kythe.proto.VName.path', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='language', full_name='kythe.proto.VName.language', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=42,
  serialized_end=130,
)


_VNAMEMASK = _descriptor.Descriptor(
  name='VNameMask',
  full_name='kythe.proto.VNameMask',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='signature', full_name='kythe.proto.VNameMask.signature', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='corpus', full_name='kythe.proto.VNameMask.corpus', index=1,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='root', full_name='kythe.proto.VNameMask.root', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='path', full_name='kythe.proto.VNameMask.path', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='language', full_name='kythe.proto.VNameMask.language', index=4,
      number=5, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=132,
  serialized_end=224,
)


_ENTRY = _descriptor.Descriptor(
  name='Entry',
  full_name='kythe.proto.Entry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='source', full_name='kythe.proto.Entry.source', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='edge_kind', full_name='kythe.proto.Entry.edge_kind', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='target', full_name='kythe.proto.Entry.target', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='fact_name', full_name='kythe.proto.Entry.fact_name', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='fact_value', full_name='kythe.proto.Entry.fact_value', index=4,
      number=5, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=227,
  serialized_end=364,
)


_ENTRIES = _descriptor.Descriptor(
  name='Entries',
  full_name='kythe.proto.Entries',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='entries', full_name='kythe.proto.Entries.entries', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=366,
  serialized_end=412,
)


_READREQUEST = _descriptor.Descriptor(
  name='ReadRequest',
  full_name='kythe.proto.ReadRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='source', full_name='kythe.proto.ReadRequest.source', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='edge_kind', full_name='kythe.proto.ReadRequest.edge_kind', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=414,
  serialized_end=482,
)


_WRITEREQUEST_UPDATE = _descriptor.Descriptor(
  name='Update',
  full_name='kythe.proto.WriteRequest.Update',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='edge_kind', full_name='kythe.proto.WriteRequest.Update.edge_kind', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='target', full_name='kythe.proto.WriteRequest.Update.target', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='fact_name', full_name='kythe.proto.WriteRequest.Update.fact_name', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='fact_value', full_name='kythe.proto.WriteRequest.Update.fact_value', index=3,
      number=4, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=587,
  serialized_end=689,
)

_WRITEREQUEST = _descriptor.Descriptor(
  name='WriteRequest',
  full_name='kythe.proto.WriteRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='source', full_name='kythe.proto.WriteRequest.source', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='update', full_name='kythe.proto.WriteRequest.update', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[_WRITEREQUEST_UPDATE, ],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=485,
  serialized_end=689,
)


_WRITEREPLY = _descriptor.Descriptor(
  name='WriteReply',
  full_name='kythe.proto.WriteReply',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=691,
  serialized_end=703,
)


_SCANREQUEST = _descriptor.Descriptor(
  name='ScanRequest',
  full_name='kythe.proto.ScanRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='target', full_name='kythe.proto.ScanRequest.target', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='edge_kind', full_name='kythe.proto.ScanRequest.edge_kind', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='fact_prefix', full_name='kythe.proto.ScanRequest.fact_prefix', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=705,
  serialized_end=794,
)


_COUNTREQUEST = _descriptor.Descriptor(
  name='CountRequest',
  full_name='kythe.proto.CountRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='index', full_name='kythe.proto.CountRequest.index', index=0,
      number=1, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='shards', full_name='kythe.proto.CountRequest.shards', index=1,
      number=2, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=796,
  serialized_end=841,
)


_COUNTREPLY = _descriptor.Descriptor(
  name='CountReply',
  full_name='kythe.proto.CountReply',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='entries', full_name='kythe.proto.CountReply.entries', index=0,
      number=1, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=843,
  serialized_end=872,
)


_SHARDREQUEST = _descriptor.Descriptor(
  name='ShardRequest',
  full_name='kythe.proto.ShardRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='index', full_name='kythe.proto.ShardRequest.index', index=0,
      number=1, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='shards', full_name='kythe.proto.ShardRequest.shards', index=1,
      number=2, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=874,
  serialized_end=919,
)

_ENTRY.fields_by_name['source'].message_type = _VNAME
_ENTRY.fields_by_name['target'].message_type = _VNAME
_ENTRIES.fields_by_name['entries'].message_type = _ENTRY
_READREQUEST.fields_by_name['source'].message_type = _VNAME
_WRITEREQUEST_UPDATE.fields_by_name['target'].message_type = _VNAME
_WRITEREQUEST_UPDATE.containing_type = _WRITEREQUEST
_WRITEREQUEST.fields_by_name['source'].message_type = _VNAME
_WRITEREQUEST.fields_by_name['update'].message_type = _WRITEREQUEST_UPDATE
_SCANREQUEST.fields_by_name['target'].message_type = _VNAME
DESCRIPTOR.message_types_by_name['VName'] = _VNAME
DESCRIPTOR.message_types_by_name['VNameMask'] = _VNAMEMASK
DESCRIPTOR.message_types_by_name['Entry'] = _ENTRY
DESCRIPTOR.message_types_by_name['Entries'] = _ENTRIES
DESCRIPTOR.message_types_by_name['ReadRequest'] = _READREQUEST
DESCRIPTOR.message_types_by_name['WriteRequest'] = _WRITEREQUEST
DESCRIPTOR.message_types_by_name['WriteReply'] = _WRITEREPLY
DESCRIPTOR.message_types_by_name['ScanRequest'] = _SCANREQUEST
DESCRIPTOR.message_types_by_name['CountRequest'] = _COUNTREQUEST
DESCRIPTOR.message_types_by_name['CountReply'] = _COUNTREPLY
DESCRIPTOR.message_types_by_name['ShardRequest'] = _SHARDREQUEST
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

VName = _reflection.GeneratedProtocolMessageType('VName', (_message.Message,), dict(
  DESCRIPTOR = _VNAME,
  __module__ = 'kythe.proto.storage_pb2'
  # @@protoc_insertion_point(class_scope:kythe.proto.VName)
  ))
_sym_db.RegisterMessage(VName)

VNameMask = _reflection.GeneratedProtocolMessageType('VNameMask', (_message.Message,), dict(
  DESCRIPTOR = _VNAMEMASK,
  __module__ = 'kythe.proto.storage_pb2'
  # @@protoc_insertion_point(class_scope:kythe.proto.VNameMask)
  ))
_sym_db.RegisterMessage(VNameMask)

Entry = _reflection.GeneratedProtocolMessageType('Entry', (_message.Message,), dict(
  DESCRIPTOR = _ENTRY,
  __module__ = 'kythe.proto.storage_pb2'
  # @@protoc_insertion_point(class_scope:kythe.proto.Entry)
  ))
_sym_db.RegisterMessage(Entry)

Entries = _reflection.GeneratedProtocolMessageType('Entries', (_message.Message,), dict(
  DESCRIPTOR = _ENTRIES,
  __module__ = 'kythe.proto.storage_pb2'
  # @@protoc_insertion_point(class_scope:kythe.proto.Entries)
  ))
_sym_db.RegisterMessage(Entries)

ReadRequest = _reflection.GeneratedProtocolMessageType('ReadRequest', (_message.Message,), dict(
  DESCRIPTOR = _READREQUEST,
  __module__ = 'kythe.proto.storage_pb2'
  # @@protoc_insertion_point(class_scope:kythe.proto.ReadRequest)
  ))
_sym_db.RegisterMessage(ReadRequest)

WriteRequest = _reflection.GeneratedProtocolMessageType('WriteRequest', (_message.Message,), dict(

  Update = _reflection.GeneratedProtocolMessageType('Update', (_message.Message,), dict(
    DESCRIPTOR = _WRITEREQUEST_UPDATE,
    __module__ = 'kythe.proto.storage_pb2'
    # @@protoc_insertion_point(class_scope:kythe.proto.WriteRequest.Update)
    ))
  ,
  DESCRIPTOR = _WRITEREQUEST,
  __module__ = 'kythe.proto.storage_pb2'
  # @@protoc_insertion_point(class_scope:kythe.proto.WriteRequest)
  ))
_sym_db.RegisterMessage(WriteRequest)
_sym_db.RegisterMessage(WriteRequest.Update)

WriteReply = _reflection.GeneratedProtocolMessageType('WriteReply', (_message.Message,), dict(
  DESCRIPTOR = _WRITEREPLY,
  __module__ = 'kythe.proto.storage_pb2'
  # @@protoc_insertion_point(class_scope:kythe.proto.WriteReply)
  ))
_sym_db.RegisterMessage(WriteReply)

ScanRequest = _reflection.GeneratedProtocolMessageType('ScanRequest', (_message.Message,), dict(
  DESCRIPTOR = _SCANREQUEST,
  __module__ = 'kythe.proto.storage_pb2'
  # @@protoc_insertion_point(class_scope:kythe.proto.ScanRequest)
  ))
_sym_db.RegisterMessage(ScanRequest)

CountRequest = _reflection.GeneratedProtocolMessageType('CountRequest', (_message.Message,), dict(
  DESCRIPTOR = _COUNTREQUEST,
  __module__ = 'kythe.proto.storage_pb2'
  # @@protoc_insertion_point(class_scope:kythe.proto.CountRequest)
  ))
_sym_db.RegisterMessage(CountRequest)

CountReply = _reflection.GeneratedProtocolMessageType('CountReply', (_message.Message,), dict(
  DESCRIPTOR = _COUNTREPLY,
  __module__ = 'kythe.proto.storage_pb2'
  # @@protoc_insertion_point(class_scope:kythe.proto.CountReply)
  ))
_sym_db.RegisterMessage(CountReply)

ShardRequest = _reflection.GeneratedProtocolMessageType('ShardRequest', (_message.Message,), dict(
  DESCRIPTOR = _SHARDREQUEST,
  __module__ = 'kythe.proto.storage_pb2'
  # @@protoc_insertion_point(class_scope:kythe.proto.ShardRequest)
  ))
_sym_db.RegisterMessage(ShardRequest)


DESCRIPTOR._options = None
# @@protoc_insertion_point(module_scope)
