import sys
import os
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw

if sys.platform == 'darwin':
    try:
        import AppKit
        # 隱藏 Mac Dock 上的圖示 (NSApplicationActivationPolicyAccessory = 1)
        AppKit.NSApp.setActivationPolicy_(1)
    except Exception as e:
        print("Error hiding dock icon:", e)

def create_image():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    icon_path = os.path.join(base_dir, 'assets', 'tray_icon.png')
    if os.path.exists(icon_path):
        try:
            return Image.open(icon_path)
        except:
            pass
    image = Image.new('RGB', (64, 64), color=(59, 130, 246))
    dc = ImageDraw.Draw(image)
    dc.rectangle((16, 16, 48, 48), fill=(255, 255, 255))
    return image

def on_show(icon, item):
    base_dir = os.path.dirname(os.path.dirname(__file__))
    flag_path = os.path.join(base_dir, 'show_window.flag')
    try:
        with open(flag_path, 'w') as f:
            f.write('show')
    except:
        pass

def on_quit(icon, item):
    icon.stop()
    base_dir = os.path.dirname(os.path.dirname(__file__))
    flag_path = os.path.join(base_dir, 'quit_app.flag')
    try:
        with open(flag_path, 'w') as f:
            f.write('quit')
    except:
        pass

if __name__ == '__main__':
    menu = (
        item('開啟', on_show, default=True),
        item('結束應用程式', on_quit)
    )
    icon = pystray.Icon("SIS", create_image(), "標準檢驗追蹤系統", menu)
    icon.run()
