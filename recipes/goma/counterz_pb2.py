# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: counterz.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='counterz.proto',
  package='devtools_goma',
  syntax='proto2',
  serialized_pb=_b('\n\x0e\x63ounterz.proto\x12\rdevtools_goma\"q\n\x0c\x43ounterzStat\x12\x10\n\x08location\x18\x01 \x01(\t\x12\x15\n\rfunction_name\x18\x02 \x01(\t\x12\x0c\n\x04name\x18\x03 \x01(\t\x12\x13\n\x0btotal_count\x18\x04 \x01(\x03\x12\x15\n\rtotal_time_ns\x18\x05 \x01(\x03\"D\n\rCounterzStats\x12\x33\n\x0e\x63ounterz_stats\x18\x01 \x03(\x0b\x32\x1b.devtools_goma.CounterzStat')
)




_COUNTERZSTAT = _descriptor.Descriptor(
  name='CounterzStat',
  full_name='devtools_goma.CounterzStat',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='location', full_name='devtools_goma.CounterzStat.location', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='function_name', full_name='devtools_goma.CounterzStat.function_name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='name', full_name='devtools_goma.CounterzStat.name', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='total_count', full_name='devtools_goma.CounterzStat.total_count', index=3,
      number=4, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='total_time_ns', full_name='devtools_goma.CounterzStat.total_time_ns', index=4,
      number=5, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=33,
  serialized_end=146,
)


_COUNTERZSTATS = _descriptor.Descriptor(
  name='CounterzStats',
  full_name='devtools_goma.CounterzStats',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='counterz_stats', full_name='devtools_goma.CounterzStats.counterz_stats', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=148,
  serialized_end=216,
)

_COUNTERZSTATS.fields_by_name['counterz_stats'].message_type = _COUNTERZSTAT
DESCRIPTOR.message_types_by_name['CounterzStat'] = _COUNTERZSTAT
DESCRIPTOR.message_types_by_name['CounterzStats'] = _COUNTERZSTATS
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

CounterzStat = _reflection.GeneratedProtocolMessageType('CounterzStat', (_message.Message,), dict(
  DESCRIPTOR = _COUNTERZSTAT,
  __module__ = 'counterz_pb2'
  # @@protoc_insertion_point(class_scope:devtools_goma.CounterzStat)
  ))
_sym_db.RegisterMessage(CounterzStat)

CounterzStats = _reflection.GeneratedProtocolMessageType('CounterzStats', (_message.Message,), dict(
  DESCRIPTOR = _COUNTERZSTATS,
  __module__ = 'counterz_pb2'
  # @@protoc_insertion_point(class_scope:devtools_goma.CounterzStats)
  ))
_sym_db.RegisterMessage(CounterzStats)


# @@protoc_insertion_point(module_scope)
