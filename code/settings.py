# 游戏总体宽度和高度
import os
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 700

# 游戏帧率
FPS = 60

# 获取当前目录、图片目录、音效目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(CURRENT_DIR,"assets",'images')
SOUNDS_DIR = os.path.join(CURRENT_DIR, "assets",'sounds')
