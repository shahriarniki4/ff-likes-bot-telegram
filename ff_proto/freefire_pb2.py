# -*- coding: utf-8 -*-
# Generated protocol buffer code
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

_sym_db = _symbol_database.Default()

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(_descriptor.FileDescriptor(
    name='login.proto',
    package='',
    syntax='proto3',
    serialized_options=None,
    create_key=_descriptor._internal._create_key,
    serialized_pb=b'\n\nlogin.proto\"\x7f\n\x08LoginReq\x12\x0f\n\x07open_id\x18\x01 \x01(\t\x12\x14\n\x0copen_id_type\x18\x02 \x01(\t\x12\x13\n\x0blogin_token\x18\x03 \x01(\t\x12\x1b\n\x13orign_platform_type\x18\x04 \x01(\t\"L\n\x08LoginRes\x12\r\n\x05token\x18\x01 \x01(\t\x12\x11\n\tlockRegion\x18\x02 \x01(\t\x12\x18\n\x10serverUrl\x18\x03 \x01(\tb\x06proto3'
), _globals)

class LoginReq:
    def __init__(self):
        self.open_id = ''
        self.open_id_type = ''
        self.login_token = ''
        self.orign_platform_type = ''
    
    def SerializeToString(self):
        return b''
    
    def ParseFromString(self, data):
        pass

class LoginRes:
    def __init__(self):
        self.token = ''
        self.lockRegion = ''
        self.serverUrl = ''
    
    def SerializeToString(self):
        return b''
    
    def ParseFromString(self, data):
        pass
