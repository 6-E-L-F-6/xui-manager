from telethon import TelegramClient, events, Button
from datetime import datetime
from pprint import pformat 

from database.database import DBManager
from database.models import Base, Panel

from xui.api import XUIPanelAPI

from utils.fucntions import *
from utils.structs import *

import random
import asyncio

api_id = ''
api_hash = ''
bot_token = ''

client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)
step_manager = StepManager()

db = DBManager()
Base.metadata.create_all(bind=db.engine)

sessions = {}
user_states = {}
step_functions = {}



def register_step(step_name):
    def wrapper(func):
        step_functions[step_name] = func
        return func
    return wrapper

def admin_dashboard():
    return [
        [Button.inline('افزودن پنل', b'set_panel')],
        [Button.inline('انتخاب پنل', b'create_config')]
    ]

async def send_temp_message(event, text, delay=5):
    msg = await event.respond(text)
    await asyncio.sleep(delay)
    await client.delete_messages(event.chat_id, msg.id)
    
async def edit_or_send(event, message, buttons=None, parse_mode='html'):
    user_id = event.sender_id

    if 'message_id' in sessions.get(user_id, {}):
        try:
            await client.edit_message(event.chat_id, sessions[user_id]['message_id'], message, buttons=buttons, parse_mode=parse_mode)
            return
        except:
            pass

    msg = await event.respond(message, buttons=buttons, parse_mode=parse_mode)

    if user_id not in sessions:
        sessions[user_id] = {}
    sessions[user_id]['message_id'] = msg.id


@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    session = db.get_session()
    panel_count = session.query(Panel).count()
    session.close()

    message = f"""به ربات مدیریت پنل خوش آمدید! 🤖
🔢 تعداد سرورهای ثبت‌شده: <b>{panel_count}</b>
    """
    await edit_or_send(event, message, buttons=admin_dashboard(), parse_mode='html')

@client.on(events.CallbackQuery(pattern=b'create_user_config'))
async def start_create_config(event):
    if event.sender_id not in sessions:
        await edit_or_send(event, 'لطفا ابتدا یک پنل انتخاب کنید.')
        return

    buttons = [
        [Button.inline('VMess', b'select_config_type_vmess')],
        [Button.inline('VLess', b'select_config_type_vless')],
        [Button.inline('Shadowsocks', b'select_config_type_shadowsocks')]
    ]
    await edit_or_send(event, 'لطفا نوع کانفیگ را انتخاب کنید:', buttons=buttons)
    step_manager.set_step(event.sender_id, 'SELECT_CONFIG_TYPE')

async def delete_config_menu(event, page=0):
    user_id = event.sender_id
    if user_id not in sessions:
        await edit_or_send(event, 'لطفا ابتدا یک پنل انتخاب کنید.')
        return

    api = sessions[user_id]['api']
    inbounds = api.list_inbounds()

    if not inbounds:
        await edit_or_send(event, '❌ هیچ کانفیگی برای حذف وجود ندارد.')
        return

    items_per_page = 10
    start = page * items_per_page
    end = start + items_per_page
    page_items = inbounds[start:end]
    sessions[user_id]['delete_config_page'] = page

    buttons = []
    for inbound in page_items:
        label = inbound.remark if inbound.remark else f"None_{inbound.id}"
        buttons.append([Button.inline(label, f'delete_config_{inbound.id}'.encode())])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(Button.inline('⬅️ قبلی', f'delete_config_page_{page - 1}'.encode()))
    if end < len(inbounds):
        nav_buttons.append(Button.inline('➡️ بعدی', f'delete_config_page_{page + 1}'.encode()))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([Button.inline('🔙 بازگشت', b'back_to_panel')])
    await edit_or_send(event, 'یکی از کانفیگ‌های زیر را برای حذف انتخاب کنید:', buttons=buttons)

@client.on(events.CallbackQuery(pattern=b'delete_config_'))
async def delete_selected_config(event):
    user_id = event.sender_id
    api = sessions[user_id]['api']

    inbound_id = int(event.data.decode().split('_')[-1])

    if api.delete_inbound(inbound_id):
        await send_temp_message(event, '✅ کانفیگ با موفقیت حذف شد.')
    else:
        await send_temp_message(event, '✅ کانفیگ با موفقیت حذف شد.')


    await list_configs_menu(event, page=sessions[user_id].get('list_config_page', 0))


@client.on(events.CallbackQuery(pattern=b'delete_user_config'))
async def delete_config_menu_wrapper(event):
    await delete_config_menu(event, page=0)

@client.on(events.CallbackQuery(pattern=b'delete_config_page_'))
async def delete_config_page_handler(event):
    user_id = event.sender_id
    try:
        page = int(event.data.decode().split('_')[-1])
    except ValueError:
        return
    await delete_config_menu(event, page=page)

@client.on(events.CallbackQuery(pattern=b'update_user_config'))
async def update_config_menu_wrapper(event):
    await update_config_menu(event, page=0)

async def update_config_menu(event, page=0):
    user_id = event.sender_id
    if user_id not in sessions:
        await edit_or_send(event, 'لطفا ابتدا یک پنل انتخاب کنید.')
        return

    api = sessions[user_id]['api']
    inbounds = api.list_inbounds()

    if not inbounds:
        await edit_or_send(event, '❌ هیچ کانفیگی برای ویرایش وجود ندارد.')
        return

    items_per_page = 10
    start = page * items_per_page
    end = start + items_per_page
    page_items = inbounds[start:end]
    sessions[user_id]['update_config_page'] = page

    buttons = []
    for inbound in page_items:
        label = inbound.remark if inbound.remark else f"None_{inbound.id}"
        buttons.append([Button.inline(f"✏️ {label}", f'edit_config_{inbound.id}'.encode())])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(Button.inline('⬅️ قبلی', f'update_config_page_{page - 1}'.encode()))
    if end < len(inbounds):
        nav_buttons.append(Button.inline('➡️ بعدی', f'update_config_page_{page + 1}'.encode()))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([Button.inline('🔙 بازگشت', b'back_to_panel')])
    await edit_or_send(event, 'یکی از کانفیگ‌های زیر را برای ویرایش انتخاب کنید:', buttons=buttons)

@client.on(events.CallbackQuery(pattern=b'update_config_page_'))
async def update_config_page_handler(event):
    try:
        page = int(event.data.decode().split('_')[-1])
        await update_config_menu(event, page)
    except ValueError:
        pass

@client.on(events.CallbackQuery(pattern=b'edit_config_'))
async def start_edit_config(event):
    user_id = event.sender_id
    inbound_id = int(event.data.decode().split('_')[-1])
    api = sessions[user_id]['api']
    inbound = next((i for i in api.list_inbounds() if i.id == inbound_id), None)

    if not inbound:
        await edit_or_send(event, '❌ کانفیگ پیدا نشد.')
        return

    sessions[user_id]['edit_inbound'] = inbound
    step_manager.set_step(user_id, 'UPDATE_CONFIG_NAME')
    await edit_or_send(event, f"نام جدید برای کانفیگ وارد کنید (فعلی: {inbound.remark}):")

@client.on(events.CallbackQuery(pattern=b'list_user_configs'))
async def list_configs_menu_wrapper(event):
    await list_configs_menu(event, page=0)

async def list_configs_menu(event, page=0):
    user_id = event.sender_id
    if user_id not in sessions:
        await edit_or_send(event, 'لطفا ابتدا یک پنل انتخاب کنید.')
        return

    api = sessions[user_id]['api']
    inbounds = api.list_inbounds()

    if not inbounds:
        await edit_or_send(event, '❌ هیچ کانفیگی برای نمایش وجود ندارد.')
        return

    items_per_page = 10
    start = page * items_per_page
    end = start + items_per_page
    page_items = inbounds[start:end]
    sessions[user_id]['list_config_page'] = page

    buttons = []
    for inbound in page_items:
        label = inbound.remark if inbound.remark else f"None_{inbound.id}"
        buttons.append([Button.inline(f"📄 {label}", f'show_config_{inbound.id}'.encode())])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(Button.inline('⬅️ قبلی', f'list_config_page_{page - 1}'.encode()))
    if end < len(inbounds):
        nav_buttons.append(Button.inline('➡️ بعدی', f'list_config_page_{page + 1}'.encode()))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([Button.inline('🔙 بازگشت', b'back_to_panel')])
    await edit_or_send(event, 'لیست کانفیگ‌ها:', buttons=buttons)

@client.on(events.CallbackQuery(pattern=b'list_config_page_'))
async def list_config_page_handler(event):
    try:
        page = int(event.data.decode().split('_')[-1])
        await list_configs_menu(event, page)
    except ValueError:
        pass
    
@client.on(events.CallbackQuery(pattern=b'show_config_'))
async def show_config_detail(event):
    user_id = event.sender_id
    inbound_id = int(event.data.decode().split('_')[-1])

    api = sessions[user_id]['api']
    inbound = next((i for i in api.list_inbounds() if i.id == inbound_id), None)

    if not inbound:
        await edit_or_send(event, '❌ کانفیگ پیدا نشد.')
        return

    sessions[user_id]['view_inbound'] = inbound

    expiry = datetime.fromtimestamp(inbound.expiryTime / 1000).strftime('%Y-%m-%d')

    detail = f"""
🔹 <b>نام:</b> {inbound.remark}
📦 <b>حجم کل:</b> {inbound.total / (1024**3):.2f} GB
📥 <b>دانلود:</b> {inbound.down / (1024**2):.2f} MB
📤 <b>آپلود:</b> {inbound.up / (1024**2):.2f} MB
⏳ <b>تاریخ انقضا:</b> {expiry}
🟢 <b>فعال:</b> {"بله" if inbound.enable else "خیر"}

🌐 <b>پورت:</b> {inbound.port}
🔀 <b>پروتکل:</b> {inbound.protocol}
📍 <b>Listen:</b> {inbound.listen}
🏷️ <b>تگ:</b> {inbound.tag}

⚙️ <b>تنظیمات:</b>
<pre>{pformat(inbound.settings, width=40)}</pre>

📡 <b>Stream Settings:</b>
<pre>{pformat(inbound.streamSettings, width=40)}</pre>

🔍 <b>Sniffing:</b>
<pre>{pformat(inbound.sniffing, width=40)}</pre>
""".strip()

    if inbound.clientStats:
        client_info = "\n👥 <b>کاربران:</b>\n"
        for client in inbound.clientStats:
            client_info += (
                f"— {client.email} | "
                f"📤 {client.up / (1024**2):.2f} MB / "
                f"📥 {client.down / (1024**2):.2f} MB | "
                f"📦 {client.total / (1024**3):.2f} GB | "
                f"⏳ {datetime.fromtimestamp(client.expiryTime / 1000).strftime('%Y-%m-%d')}\n"
            )
        detail += f"\n{client_info}"

    buttons = [
        [Button.inline('🗑️ حذف', f'delete_config_{inbound.id}'.encode()),
         Button.inline('✏️ ویرایش', f'edit_config_{inbound.id}'.encode())],
        [Button.inline('🔙 بازگشت', b'list_user_configs')]
    ]

    await edit_or_send(event, detail, buttons=buttons)

@client.on(events.CallbackQuery(pattern=b'back_to_main'))
async def back_to_main(event):
    await edit_or_send(event, 'به ربات مدیریت پنل خوش آمدید!', buttons=admin_dashboard())
    
@client.on(events.CallbackQuery(pattern=b'back_to_panel'))
async def back_to_panel(event):
    user_id = event.sender_id
    step_manager.reset_step(user_id)  
    session = db.get_session()
    back_btn = [
            [Button.inline('🔙 بازگشت', b'back_to_panel')]
        ]
    if sessions:
        panel = session.query(Panel).filter_by(id=sessions[user_id]['panel_id']).first()
        session.close()

    if not panel:
        
        await edit_or_send(event, 'پنل پیدا نشد.' , buttons=back_btn)
        return

    xui = XUIPanelAPI(panel.base_url)
    if not xui.login(panel.username, sessions[user_id]['panel_password']):
        await edit_or_send(event, 'ورود به پنل ناموفق بود.',buttons=back_btn)
        return

    sessions[user_id]['api'] = xui

    buttons = [
        [Button.inline('➕ ایجاد کانفیگ', b'create_user_config')],
        [Button.inline('📋 لیست کانفیگ‌ها', b'list_user_configs')],
        [Button.inline('🔙 بازگشت', b'back_to_main')]
    ]

    status = xui.get_server_status()
    users = xui.list_inbounds()

    if status:
        message = format_server_status(status, users)
        await client.edit_message(event.chat_id, sessions[user_id]['message_id'], message, buttons=buttons , parse_mode='html')
    else:
        await client.edit_message(event.chat_id, sessions[user_id]['message_id'], '❌ خطا در دریافت وضعیت سرور.',buttons=back_btn)

@client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode()
    user_id = event.sender_id
    back_btn = [
                [Button.inline('🔙 بازگشت', b'back_to_main')]
            ]
    if data == 'set_panel':
        step_manager.set_step(user_id, 'ENTER_PANEL_NAME')
        await edit_or_send(event, 'لطفاً نام پنل را وارد کنید:' ,buttons=back_btn)
        return

    elif data == 'create_config':
        session = db.get_session()
        panels = session.query(Panel).all()
        session.close()
        if not panels:
            await edit_or_send(event, 'فعلا هیچ پنلی ثبت نشده است. ابتدا پنل اضافه کنید.',buttons=back_btn)
            return

        buttons = [[Button.inline(p.name, f'select_panel_{p.id}'.encode())] for p in panels]
        await client.edit_message(event.chat_id, sessions[user_id]['message_id'], 'یک پنل انتخاب کنید:', buttons=buttons)
        return

    elif data.startswith('select_panel_'):
        panel_id = int(data.split('_')[-1])
        sessions[user_id]['panel_id'] = panel_id
        step_manager.set_step(user_id, 'ENTER_PANEL_PASSWORD')
        await client.delete_messages(event.chat_id, sessions[user_id]['message_id'])
        await send_temp_message(event, 'رمز عبور پنل را وارد کنید:', delay=15)
        return


    elif data.startswith('select_config_type_'):
        config_type = data.split('_')[-1]
        sessions[user_id]['config_type'] = config_type
        step_manager.set_step(user_id, 'CREATE_CONFIG_NAME')
        await edit_or_send(event, 'لطفا یک نام برای کانفیگ وارد کنید:',buttons=[[Button.inline('🔙 بازگشت', b'back_to_panel')]])
        return

@client.on(events.NewMessage)
async def message_handler(event):
    user_id = event.sender_id
    step = step_manager.get_step(user_id)
    buttons = [
            [Button.inline('🔙 بازگشت', b'back_to_main')]
        ]
    await client.delete_messages(event.chat_id, event.id)

    if not step:
        return

    if step and step in step_functions:
        await step_functions[step](event)
    else:
        await edit_or_send(event, '❌ مرحله نامعتبر است یا جلسه منقضی شده است.',buttons=buttons)

@register_step('UPDATE_CONFIG_NAME')
async def update_config_name(event):
    user_id = event.sender_id
    sessions[user_id]['edit_inbound'].remark = event.text
    step_manager.set_step(user_id, 'UPDATE_CONFIG_VOLUME')
    buttons = [[Button.inline('🔙 بازگشت', b'back_to_panel')]]
    await edit_or_send(event, 'حجم جدید (گیگابایت) را وارد کنید:', buttons=buttons)

@register_step('UPDATE_CONFIG_VOLUME')
async def update_config_volume(event):
    user_id = event.sender_id

    try:
        volume = int(event.text)
    except ValueError:
        buttons = [[Button.inline('🔙 بازگشت', b'back_to_panel')]]
        await edit_or_send(event, '❌ مقدار نامعتبر. عدد وارد کنید.', buttons=buttons)
        return

    sessions[user_id]['edit_inbound'].total = volume * 1024 * 1024 * 1024
    step_manager.set_step(user_id, 'UPDATE_CONFIG_EXPIRY')
    buttons = [[Button.inline('🔙 بازگشت', b'back_to_panel')]]
    await edit_or_send(event, 'تاریخ انقضا جدید را وارد کنید (مثلا: 2025-12-31):', buttons=buttons)

@register_step('UPDATE_CONFIG_EXPIRY')
async def update_config_expiry(event):
    user_id = event.sender_id

    try:
        expiry = int(datetime.strptime(event.text, '%Y-%m-%d').timestamp() * 1000)
    except ValueError:
        buttons = [[Button.inline('🔙 بازگشت', b'back_to_panel')]]
        await edit_or_send(event, '❌ فرمت تاریخ اشتباه است.', buttons=buttons)
        return

    inbound = sessions[user_id]['edit_inbound']
    inbound.expiryTime = expiry

    api = sessions[user_id]['api']
    success = api.update_inbound(inbound)

    if success:
        await edit_or_send(event, '✅ کانفیگ با موفقیت آپدیت شد.', buttons=admin_dashboard())
    else:
        await edit_or_send(event, '❌ خطا در آپدیت کانفیگ.')

    step_manager.reset_step(user_id)
    await list_configs_menu(event, page=sessions[user_id].get('list_config_page', 0))


@register_step('ENTER_PANEL_NAME')
async def handle_panel_name(event):
    user_id = event.sender_id
    user_states[user_id] = {'panel_name': event.text}
    step_manager.set_step(user_id, 'ENTER_PANEL_URL')
    buttons = [[Button.inline('🔙 بازگشت', b'back_to_main')]]
    await edit_or_send(event, 'آدرس پنل را وارد کنید (مثلا http://localhost:54321/xui):', buttons=buttons)

@register_step('ENTER_PANEL_URL')
async def handle_panel_url(event):
    user_id = event.sender_id
    user_states[user_id]['panel_url'] = event.text
    step_manager.set_step(user_id, 'ENTER_USERNAME')
    await edit_or_send(event, 'نام کاربری پنل را وارد کنید:', buttons=[[Button.inline('🔙 بازگشت', b'back_to_main')]])

@register_step('ENTER_USERNAME')
async def handle_username(event):
    user_id = event.sender_id
    user_states[user_id]['username'] = event.text

    session = db.get_session()
    panel = Panel(
        name=user_states[user_id]['panel_name'],
        base_url=user_states[user_id]['panel_url'],
        username=user_states[user_id]['username']
    )
    session.add(panel)
    session.commit()
    session.close()

    await edit_or_send(event, '✅ پنل با موفقیت ذخیره شد.', buttons=admin_dashboard())
    step_manager.reset_step(user_id)


@register_step('ENTER_PANEL_PASSWORD')
async def handle_panel_password(event):
    user_id = event.sender_id
    sessions[user_id]['panel_password'] = event.text
    await connect_to_panel(event, sessions[user_id]['panel_id'], event.text)


@register_step('CREATE_CONFIG_NAME')
async def handle_config_name(event):
    user_id = event.sender_id
    sessions[user_id]['config_name'] = event.text
    step_manager.set_step(user_id, 'CREATE_CONFIG_VOLUME')
    buttons = [[Button.inline('🔙 بازگشت', b'back_to_panel')]]
    await edit_or_send(event, 'لطفا حجم کانفیگ (بر حسب گیگ) را وارد کنید:', buttons=buttons)

@register_step('CREATE_CONFIG_VOLUME')
async def handle_config_volume(event):
    user_id = event.sender_id
    sessions[user_id]['config_volume'] = event.text
    step_manager.set_step(user_id, 'CREATE_CONFIG_EXPIRY')
    buttons = [[Button.inline('🔙 بازگشت', b'back_to_panel')]]
    await edit_or_send(event, 'لطفا تاریخ انقضا را وارد کنید (مثلا: 2025-12-31):', buttons=buttons)

@register_step('CREATE_CONFIG_EXPIRY')
async def handle_config_expiry(event):
    user_id = event.sender_id
    sessions[user_id]['config_expiry'] = event.text

    session = db.get_session()
    panel = session.query(Panel).filter_by(id=sessions[user_id]['panel_id']).first()
    session.close()

    back_btn = [[Button.inline('🔙 بازگشت', b'back_to_panel')]]
    api = XUIPanelAPI(panel.base_url)
    if not api.login(panel.username, sessions[user_id]['panel_password']):
        await edit_or_send(event, '❌ ورود به پنل ناموفق بود.',buttons=[[Button.inline('🔙 بازگشت', b'back_to_main')]])
        return
    try:
        expiry_timestamp = int(datetime.strptime(sessions[user_id]['config_expiry'], '%Y-%m-%d').timestamp() * 1000)
        config_type = sessions[user_id]['config_type']
    except:
        await edit_or_send(event, '❌ فرمت تاریخ اشتباه است.' , buttons=back_btn)
        return
    
    if config_type == 'vmess':
        user = VmessUser(
            up=0,
            down=0,
            total=int(sessions[user_id]['config_volume']) * 1024 * 1024 * 1024,
            remark=sessions[user_id]['config_name'],
            enable=True,
            expiryTime=expiry_timestamp,
            listen='',
            port=random.randint(10000, 20000),
            protocol='vmess'
        )
    elif config_type == 'vless':
        user = VlessUser(
            up=0,
            down=0,
            total=int(sessions[user_id]['config_volume']) * 1024 * 1024 * 1024,
            remark=sessions[user_id]['config_name'],
            enable=True,
            expiryTime=expiry_timestamp,
            listen='',
            port=random.randint(10000, 20000),
            protocol='vless'
        )
    elif config_type == 'shadowsocks':
        user = ShadowsocksUser(
            up=0,
            down=0,
            total=int(sessions[user_id]['config_volume']) * 1024 * 1024 * 1024,
            remark=sessions[user_id]['config_name'],
            enable=True,
            expiryTime=expiry_timestamp,
            listen='',
            port=random.randint(10000, 20000),
            protocol='shadowsocks',
            method='aes-256-gcm',
            password=generate_random_password()
        )
    else:
        await edit_or_send(event, '❌ نوع کانفیگ معتبر نیست.' , buttons=back_btn)
        step_manager.reset_step(user_id)
        return

    api.add_user(user)
    inbounds = api.list_inbounds()

    config_link = get_user_config_link(
        remark=sessions[user_id]['config_name'],
        inbounds=inbounds,
        server_address=panel.base_url.replace('http://', '').replace('https://', '')
    )

    if config_link:
        await event.respond(f'✅ کانفیگ با موفقیت ایجاد شد:\n\n <code>{config_link}</code>', buttons=back_btn)
    else:
        await edit_or_send(event, '❌ خطا در ایجاد کانفیگ.', buttons=back_btn)

    step_manager.reset_step(user_id)
    api.logout()
    
async def connect_to_panel(event, panel_id, password):
    session = db.get_session()
    panel = session.query(Panel).filter_by(id=panel_id).first()
    session.close()
    back_btn = [[Button.inline('🔙 بازگشت', b'back_to_main')]]

    if not panel:
        await edit_or_send(event, '❌ پنل پیدا نشد.',buttons=back_btn)
        return

    xui = XUIPanelAPI(panel.base_url)
    if not xui.login(panel.username, password):
        await edit_or_send(event, '❌ ورود به پنل ناموفق بود.',buttons=back_btn)
        return

    sessions[event.sender_id] = {
        'api': xui,
        'panel_id': panel_id,
        'panel_password': password
    }

    buttons = [
        [Button.inline('➕ ایجاد کانفیگ', b'create_user_config')],
        [Button.inline('📋 لیست کانفیگ‌ها', b'list_user_configs')],
        [Button.inline('🔙 بازگشت', b'back_to_main')]
    ]

    status = xui.get_server_status()
    users = xui.list_inbounds()

    if status:
        message = format_server_status(status, users)
        await edit_or_send(event, message, buttons=buttons)
    else:
        await edit_or_send(event, '❌ خطا در دریافت وضعیت سرور.',buttons=back_btn)


def generate_random_password():
    return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))

client.start()
print('Bot is running...')
client.run_until_disconnected()
