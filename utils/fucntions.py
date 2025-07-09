import base64 ,urllib ,json
from .structs import ServerStatus

class StepManager:
    def __init__(self):
        self.user_steps = {}

    def set_step(self, user_id, step):
        self.user_steps[user_id] = step

    def get_step(self, user_id):
        return self.user_steps.get(user_id)

    def reset_step(self, user_id):
        if user_id in self.user_steps:
            del self.user_steps[user_id]

    def is_in_step(self, user_id, step):
        return self.user_steps.get(user_id) == step

def format_size(bytes_amount):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_amount < 1024:
            return f"{bytes_amount:.2f} {unit}"
        bytes_amount /= 1024
    return f"{bytes_amount:.2f} PB"

def format_server_status(status: ServerStatus , users) -> str:
    uptime_hours = status.uptime // 3600
    uptime_minutes = (status.uptime % 3600) // 60
    uptime_seconds = status.uptime % 60

    message = (
        f"📊 <b>وضعیت سرور</b>\n\n"
        f"🖥️ <b>CPU:</b> {status.cpu:.2f}%\n"
        f"💾 <b>RAM:</b> {format_size(status.mem.current)} / {format_size(status.mem.total)}\n"
        f"📀 <b>SWAP:</b> {format_size(status.swap.current)} / {format_size(status.swap.total)}\n"
        f"💽 <b>Disk:</b> {format_size(status.disk.current)} / {format_size(status.disk.total)}\n\n"

        f"⚙️ <b>Xray:</b>\n"
        f"▫️State: {status.xray.state}\n"
        f"▫️Version: {status.xray.version}\n"
        f"▫️Error: {status.xray.errorMsg or 'None'}\n\n"

        f"⏳ <b>Uptime:</b> {uptime_hours}h {uptime_minutes}m {uptime_seconds}s\n"
        f"📈 <b>Loads:</b> {', '.join([str(load) for load in status.loads])}\n\n"

        f"🔌 <b>Connections:</b>\n"
        f"▫️TCP: {status.tcpCount}\n"
        f"▫️UDP: {status.udpCount}\n\n"

        f"📡 <b>Network IO:</b>\n"
        f"▫️Upload: {format_size(status.netIO.up)}\n"
        f"▫️Download: {format_size(status.netIO.down)}\n\n"

        f"📥 <b>Network Traffic:</b>\n"
        f"▫️Sent: {format_size(status.netTraffic.sent)}\n"
        f"▫️Received: {format_size(status.netTraffic.recv)}\n\n"
        
        f"📥<b>Users:</b>"
        f" {len(users)}\n"
    )

    return message

def build_vmess_link(client_id: str, remark, address: str, port: int, alter_id=0, security='none', network='tcp'):
    vmess_config = {
        "v": "2",
        "ps": remark,
        "add": address,
        "port": str(port),
        "id": client_id,
        "aid": str(alter_id),
        "net": network,
        "type": "none",
        "host": "",
        "path": "",
        "tls": "none",
        "sni": ""
    }
    json_str = json.dumps(vmess_config, separators=(',', ':'))
    b64 = base64.b64encode(json_str.encode()).decode()
    return "vmess://" + b64

def build_shadowsocks_link(method: str, password: str, address: str, port: int, remark):
    user_info = f"{method}:{password}@{address}:{port}"
    base64_user_info = base64.urlsafe_b64encode(user_info.encode()).decode().rstrip('=')
    tag = urllib.parse.quote(remark) if remark else 'shadowsocks'
    return f"ss://{base64_user_info}#{tag}"

def build_vless_link(client_id, address, port, remark,network='tcp', security='none', ):
    query_params = {
        "type": network,
        "security": security,
    }
    query_string = urllib.parse.urlencode(query_params)
    tag = urllib.parse.quote(remark) if remark else client_id[:8]
    
    link = f"vless://{client_id}@{address}:{port}?{query_string}#{tag}"
    return link

def get_user_config_link(remark, inbounds, server_address: str):
    for inbound in inbounds:
        if inbound.remark != remark:
            continue

        protocol = inbound.protocol
        settings = inbound.settings
        if isinstance(settings, str):
            settings = json.loads(settings)

        stream_settings = inbound.streamSettings
        if isinstance(stream_settings, str):
            stream_settings = json.loads(stream_settings)

        port = inbound.port
        network = stream_settings.get('network', 'tcp')
        security = stream_settings.get('security', 'none')

        if protocol in ('vmess', 'vless'):
            clients = settings.get('clients', [])
            if not clients:
                return None

            client = clients[0]  
            client_id = client['id']

            if protocol == 'vmess':
                return build_vmess_link(
                    remark=remark,
                    client_id=client_id,
                    address=server_address.split(":")[0],
                    port=port,
                    alter_id=client.get('alterId', 0),
                    security=security,
                    network=network
                )
            else:
                return build_vless_link(
                    client_id=client_id,
                    address=server_address.split(":")[0],
                    port=port,
                    network=network,
                    security=security,
                    remark=remark
                )

        elif protocol == 'shadowsocks':
            method = settings.get('method', '')
            password = settings.get('password', '')
            return build_shadowsocks_link(
                method=method,
                password=password,
                address=server_address.split(":")[0],
                port=port,
                remark=remark
            )

    return None



