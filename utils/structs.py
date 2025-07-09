from dataclasses import dataclass
from typing import List, Dict, Any
import uuid,json

@dataclass
class ClientStat:
    id: int
    inboundId: int
    enable: bool
    email: str
    up: int
    down: int
    expiryTime: int
    total: int

@dataclass
class Inbound:
    id: int
    up: int
    down: int
    total: int
    remark: str
    enable: bool
    expiryTime: int
    clientStats: List[ClientStat]
    listen: str
    port: int
    protocol: str
    settings: Dict[str, Any]
    streamSettings: Dict[str, Any]
    tag: str
    sniffing: Dict[str, Any]

@dataclass
class MemoryInfo:
    current: int
    total: int

@dataclass
class SwapInfo:
    current: int
    total: int

@dataclass
class DiskInfo:
    current: int
    total: int

@dataclass
class XrayInfo:
    state: str
    errorMsg: str
    version: str

@dataclass
class NetIOInfo:
    up: int
    down: int

@dataclass
class NetTrafficInfo:
    sent: int
    recv: int

@dataclass
class ServerStatus:
    cpu: float
    mem: MemoryInfo
    swap: SwapInfo
    disk: DiskInfo
    xray: XrayInfo
    uptime: int
    loads: List[float]
    tcpCount: int
    udpCount: int
    netIO: NetIOInfo
    netTraffic: NetTrafficInfo


@dataclass
class User:
    up: int
    down: int
    total: int
    remark: str
    enable: bool
    expiryTime: int
    listen: str
    port: int
    protocol: str

    def to_payload(self):
        raise NotImplementedError("This method must be implemented in subclasses.")

@dataclass
class VmessUser(User):
    client_id: str = str(uuid.uuid1())
    alter_id: int = 0

    def to_payload(self):
        return {
            'up': self.up,
            'down': self.down,
            'total': self.total,
            'remark': self.remark,
            'enable': str(self.enable).lower(),
            'expiryTime': self.expiryTime,
            'listen': self.listen,
            'port': self.port,
            'protocol': self.protocol,
            'settings': json.dumps({
                'clients': [{
                    'id': self.client_id,
                    'alterId': self.alter_id,
                    'email': '',
                    'limitIp': 0,
                    'totalGB': 0,
                    'expiryTime': ''
                }],
                'disableInsecureEncryption': False
            }),
            'streamSettings': json.dumps({
                'network': 'tcp',
                'security': 'none',
                'tcpSettings': {
                    'acceptProxyProtocol': False,
                    'header': {'type': 'none'}
                }
            }),
            'sniffing': json.dumps({
                'enabled': True,
                'destOverride': ['http', 'tls']
            })
        }

@dataclass
class VlessUser(User):
    client_id: str = str(uuid.uuid1())
    flow: str = 'xtls-rprx-direct'

    def to_payload(self):
        return {
            'up': self.up,
            'down': self.down,
            'total': self.total,
            'remark': self.remark,
            'enable': str(self.enable).lower(),
            'expiryTime': self.expiryTime,
            'listen': self.listen,
            'port': self.port,
            'protocol': self.protocol,
            'settings': json.dumps({
                'clients': [{
                    'id': self.client_id,
                    'flow': self.flow,
                    'email': '',
                    'limitIp': 0,
                    'totalGB': 0,
                    'expiryTime': ''
                }],
                'decryption': 'none',
                'fallbacks': []
            }),
            'streamSettings': json.dumps({
                'network': 'tcp',
                'security': 'none',
                'tcpSettings': {
                    'acceptProxyProtocol': False,
                    'header': {'type': 'none'}
                }
            }),
            'sniffing': json.dumps({
                'enabled': True,
                'destOverride': ['http', 'tls']
            })
        }

@dataclass
class ShadowsocksUser(User):
    method: str
    password: str

    def to_payload(self):
        return {
            'up': self.up,
            'down': self.down,
            'total': self.total,
            'remark': self.remark,
            'enable': str(self.enable).lower(),
            'expiryTime': self.expiryTime,
            'listen': self.listen,
            'port': self.port,
            'protocol': self.protocol,
            'settings': json.dumps({
                'method': self.method,
                'password': self.password,
                'network': 'tcp,udp'
            }),
            'streamSettings': json.dumps({
                'network': 'tcp',
                'security': 'tls',
                'tlsSettings': {
                    'serverName': '',
                    'certificates': [{'certificateFile': '', 'keyFile': ''}],
                    'alpn': []
                },
                'tcpSettings': {
                    'acceptProxyProtocol': False,
                    'header': {'type': 'none'}
                }
            }),
            'sniffing': json.dumps({
                'enabled': True,
                'destOverride': ['http', 'tls']
            })
        }
