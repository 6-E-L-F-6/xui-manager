import requests
from utils.fucntions import *
from utils.structs import *

class UserFactory:
    @staticmethod
    def create_user(protocol: str, **kwargs):
        if protocol == 'vmess':
            return VmessUser(protocol='vmess', **kwargs)
        elif protocol == 'vless':
            return VlessUser(protocol='vless', **kwargs)
        elif protocol == 'shadowsocks':
            return ShadowsocksUser(protocol='shadowsocks', **kwargs)
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")
        
class XUIPanelAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': self.base_url,
            'Referer': f'{self.base_url}/',
            'Connection': 'keep-alive',
            'Cookie': 'lang=en-US',
        })
        self.is_logged_in = False

    def login(self, username: str, password: str) -> bool:
        clean_base_url = self.base_url.rstrip('/')
        if clean_base_url.endswith('/xui'):
            clean_base_url = clean_base_url[:-4]  


        url = f"{clean_base_url}/login"
        data = {
            'username': username,
            'password': password
        }

        response = self.session.post(url, data=data)

        if response.ok and response.json().get('success'):
            print("[+] Login successful!")
            self.is_logged_in = True
            return True
        else:
            print("[-] Login failed:", response.text)
            return False

        
    def logout(self) -> bool:
        if not self.is_logged_in:
            print("[-] You are not logged in.")
            return False
        clean_base_url = self.base_url.rstrip('/')
        if clean_base_url.endswith('/xui'):
            clean_base_url = clean_base_url[:-4]  

        url = f"{clean_base_url}/logout"

        cookies = self.session.cookies.get_dict()
        cookie_header = f"lang=en-US; session={cookies.get('session')}"

        response = self.session.get(
            url,
            headers={
                'Referer': f'{self.base_url}/inbounds',
                'Cookie': cookie_header
            }
        )

        if response.ok:
            print("[+] Logged out successfully.")
            self.is_logged_in = False
            self.session.cookies.clear()
            return True
        else:
            print(f"[-] Logout failed: HTTP {response.status_code}")
            return False

    def get_server_status(self):
        if not self.is_logged_in:
            print("[-] Please login first!")
            return None

        clean_base_url = self.base_url.rstrip('/')
        if clean_base_url.endswith('/xui'):
            clean_base_url = clean_base_url[:-4]  
            
        url = f"{clean_base_url}/server/status"

        cookies = self.session.cookies.get_dict()
        cookie_header = f"lang=en-US; session={cookies.get('session')}"

        response = self.session.post(
            url,
            data={},
            headers={
                'Referer': f'{self.base_url}/',
                'Cookie': cookie_header
            }
        )

        if response.ok:
            data = response.json()

            if not data.get('success'):
                print("[-] Server returned an error.")
                return None

            obj = data.get('obj')
            status = ServerStatus(
                cpu=obj['cpu'],
                mem=MemoryInfo(current=obj['mem']['current'], total=obj['mem']['total']),
                swap=SwapInfo(current=obj['swap']['current'], total=obj['swap']['total']),
                disk=DiskInfo(current=obj['disk']['current'], total=obj['disk']['total']),
                xray=XrayInfo(**obj['xray']),
                uptime=obj['uptime'],
                loads=obj['loads'],
                tcpCount=obj['tcpCount'],
                udpCount=obj['udpCount'],
                netIO=NetIOInfo(**obj['netIO']),
                netTraffic=NetTrafficInfo(**obj['netTraffic'])
            )

            return status

        else:
            print("[-] Failed to get server status:", response.text)
            return None



    def add_user(self, user: User):
        if not self.is_logged_in:
            print("[-] Please login first!")
            return None

        url = f"{self.base_url}/inbound/add"

        cookies = self.session.cookies.get_dict()
        cookie_header = f"lang=en-US; session={cookies.get('session')}"

        response = self.session.post(
            url,
            data=user.to_payload(),
            headers={
                'Referer': f'{self.base_url}/inbounds',
                'Cookie': cookie_header
            }
        )

        if response.ok:
            data = response.json()
            if data.get('success'):
                print("[+] User added successfully!")
                return data
            else:
                print("[-] Failed to add user:", data.get('msg'))
                return None
        else:
            print("[-] HTTP request failed:", response.status_code)
            return None
        
    def list_inbounds(self):
        if not self.is_logged_in:
            print("[-] Please login first!")
            return None

        url = f"{self.base_url}/inbound/list"

        cookies = self.session.cookies.get_dict()
        cookie_header = f"lang=en-US; session={cookies.get('session')}"

        response = self.session.post(
            url,
            data={},
            headers={
                'Referer': f'{self.base_url}/inbounds',
                'Cookie': cookie_header
            }
        )

        if response.ok:
            data = response.json()

            if not data.get('success'):
                print("[-] Server returned an error.")
                return None

            inbounds_list: List[Inbound] = []
            for item in data.get('obj', []):
                client_stats = [ClientStat(**client) for client in item.get('clientStats', [])]

                inbound = Inbound(
                    id=item['id'],
                    up=item['up'],
                    down=item['down'],
                    total=item['total'],
                    remark=item['remark'],
                    enable=item['enable'],
                    expiryTime=item['expiryTime'],
                    clientStats=client_stats,
                    listen=item.get('listen', ''),
                    port=item['port'],
                    protocol=item['protocol'],
                    settings=json.loads(item.get('settings', '{}')),
                    streamSettings=json.loads(item.get('streamSettings', '{}')),
                    tag=item['tag'],
                    sniffing=json.loads(item.get('sniffing', '{}'))
                )
                inbounds_list.append(inbound)

            return inbounds_list

        else:
            print("[-] Failed to get inbounds list:", response.text)
            return None

    
    def update_inbound(self, inbound):
        if not self.is_logged_in:
            print("[-] Please login first!")
            return False

        url = f"{self.base_url}/inbound/update/{inbound.id}"

        data = {
            "up": inbound.up,
            "down": inbound.down,
            "total": inbound.total,
            "remark": inbound.remark,
            "enable": str(inbound.enable).lower(),
            "expiryTime": inbound.expiryTime,
            "listen": inbound.listen or "",
            "port": inbound.port,
            "protocol": inbound.protocol,
            "settings": json.dumps(inbound.settings, separators=(',', ':')),
            "streamSettings": json.dumps(inbound.streamSettings, separators=(',', ':')),
            "sniffing": json.dumps(inbound.sniffing, separators=(',', ':'))
        }

        cookies = self.session.cookies.get_dict()
        cookie_header = f"lang=en-US; session={cookies.get('session')}"

        response = self.session.post(
            url,
            data=data,
            headers={
                'Referer': f'{self.base_url}/inbounds',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Cookie': cookie_header
            }
        )

        if response.ok:
            resp_json = response.json()
            if resp_json.get('success'):
                print(f"[+] Inbound {inbound.id} updated successfully.")
                return True
            else:
                print(f"[-] Update failed: {resp_json.get('msg')}")
                return False
        else:
            print(f"[-] HTTP error: {response.status_code} - {response.text}")
            return False
        
    def delete_inbound(self, inbound_id) :
        if not self.is_logged_in:
            print("[-] Please login first!")
            return False

        url = f"{self.base_url}/inbound/del/{inbound_id}"

        cookies = self.session.cookies.get_dict()
        cookie_header = f"lang=en-US; session={cookies.get('session')}"

        response = self.session.post(
            url,
            data={},
            headers={
                'Referer': f'{self.base_url}/inbounds',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Cookie': cookie_header
            }
        )

        if response.ok:
            resp_json = response.json()
            if resp_json.get('success'):
                print(f"[+] Inbound {inbound_id} deleted successfully.")
                return True
            else:
                print(f"[-] Failed to delete inbound: {resp_json.get('msg')}")
                return False
        else:
            print(f"[-] HTTP error: {response.status_code} - {response.text}")
            return False


