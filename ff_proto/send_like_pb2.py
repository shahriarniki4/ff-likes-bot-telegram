# -*- coding: utf-8 -*-
"""Protocol message used by the Free Fire LikeProfile endpoint."""

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory


file_proto = descriptor_pb2.FileDescriptorProto()
file_proto.name = "like.proto"
file_proto.syntax = "proto3"

like_message = file_proto.message_type.add()
like_message.name = "like"

uid_field = like_message.field.add()
uid_field.name = "uid"
uid_field.number = 1
uid_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT64
uid_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

region_field = like_message.field.add()
region_field.name = "region"
region_field.number = 2
region_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
region_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

DESCRIPTOR = descriptor_pool.Default().AddSerializedFile(file_proto.SerializeToString())
like = message_factory.GetMessageClass(DESCRIPTOR.message_types_by_name["like"])