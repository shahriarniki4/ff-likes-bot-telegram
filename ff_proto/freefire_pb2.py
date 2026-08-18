# -*- coding: utf-8 -*-
"""Protocol messages used by the Free Fire login exchange.

This module intentionally keeps the generated message surface small while
using the protobuf runtime for real serialization and parsing. The previous
file only returned empty bytes, which made every login request invalid.
"""

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory


def _field(
    name: str,
    number: int,
    field_type: int,
    *,
    label: int = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
) -> descriptor_pb2.FieldDescriptorProto:
    field = descriptor_pb2.FieldDescriptorProto()
    field.name = name
    field.number = number
    field.type = field_type
    field.label = label
    return field


file_proto = descriptor_pb2.FileDescriptorProto()
file_proto.name = "FreeFire.proto"
file_proto.syntax = "proto3"

login_request = file_proto.message_type.add()
login_request.name = "LoginReq"
login_request.field.extend(
    [
        _field("open_id", 22, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
        _field("open_id_type", 23, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
        _field("login_token", 29, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
        _field(
            "orign_platform_type",
            99,
            descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
        ),
    ]
)

login_response = file_proto.message_type.add()
login_response.name = "LoginRes"
login_response.field.extend(
    [
        _field("account_id", 1, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
        _field("lock_region", 2, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
        _field("token", 8, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
        _field("server_url", 10, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
    ]
)

DESCRIPTOR = descriptor_pool.Default().AddSerializedFile(file_proto.SerializeToString())
LoginReq = message_factory.GetMessageClass(DESCRIPTOR.message_types_by_name["LoginReq"])
LoginRes = message_factory.GetMessageClass(DESCRIPTOR.message_types_by_name["LoginRes"])