# 资源管理器
# 资源管理类
import pygame
import os
from settings import IMAGES_DIR, SOUNDS_DIR, SCREEN_WIDTH, SCREEN_HEIGHT


class SilentSound:
    def play(self, loops=0):
        return None

    def stop(self):
        return None


class ResourceManager:
    # 单例模式
    def __new__(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
        return cls._instance
    #初始化
    def __init__(self):
        #初始化声音
        pygame.mixer.init()
        self.images={} #图片
        self.sounds={}
        self.fonts={}#字体集
        self.audio_enabled = True


    def load_all_resources(self):
        #加载图片
        self.images["background"] = self.load_image("cloudy.jpg",(SCREEN_WIDTH,SCREEN_HEIGHT))
        self.images["bg_scroll"] = self.load_image("bg_scroll.png", (SCREEN_WIDTH, 1130))
        self.images["bg_bonus"] = self.load_image("bg_bonus.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.images["hero"] = [self.load_image("待机1.png", (75, 90)),
                      self.load_image("待机2.png", (75, 90)),
                      self.load_image("待机3.png", (75, 90))]
        self.images["bullet"] = [self.load_image("子弹1.png", (30, 60)),
                                 self.load_image("子弹2.png", (30, 60)),
                                 self.load_image("子弹3.png", (30, 60)),
                                 self.load_image("子弹4.png", (30, 60))]
        self.images["enemy1"] = self.load_image("enemy1.png", (57, 43))
        self.images["enemy2"] = self.load_image("enemy2.png", (69, 99))
        self.images["enemy3_n"] = [self.load_image("enemy3_n1.png", (169, 258)),
                                    self.load_image("enemy3_n2.png", (169, 258))]
        # 敌机死亡动画
        self.images["enemy1_down"] = [self.load_image(f"enemy1_down{i}.png", (57, 51)) for i in range(1, 5)]
        self.images["enemy2_down"] = [self.load_image(f"enemy2_down{i}.png", (69, 95)) for i in range(1, 5)]
        self.images["enemy3_down"] = [self.load_image(f"enemy3_down{i}.png", (169, 261)) for i in range(1, 7)]
        # 敌机受伤图
        self.images["enemy2_hit"] = self.load_image("enemy2_hit.png", (69, 99))
        self.images["enemy3_hit"] = self.load_image("enemy3_hit.png", (169, 258))
        # Boss素材
        self.images["boss_idle"] = [self.load_image("boss_idle0.png", (180, 241)),
                                     self.load_image("boss_idle1.png", (180, 241)),
                                     self.load_image("boss_idle2.png", (180, 241)),
                                     self.load_image("boss_idle3.png", (180, 241))]
        self.images["boss_death"] = [self.load_image("boss_death0.png", (180, 219)),
                                      self.load_image("boss_death1.png", (180, 219)),
                                      self.load_image("boss_death2.png", (180, 219))]
        self.images["boss_cloak"] = [self.load_image("boss_cloak0.png", (180, 242)),
                                      self.load_image("boss_cloak1.png", (180, 242)),
                                      self.load_image("boss_cloak2.png", (180, 242))]
        self.images["boss_warning"] = self.load_image("boss1-ef.png", (120, 80))
        self.images["enemy_bullet"] = [self.load_image("boss_bullet.png", (25, 26))]
        # 道具贴图
        self.images["item_heal"] = self.load_image("回血.png", (35, 35))
        self.images["item_shield"] = self.load_image("护盾.png", (35, 35))
        self.images["item_upgrade"] = self.load_image("升级.png", (35, 35))
        self.images["item_track"] = self.load_image("辐射.png", (35, 35))
        # 宝石贴图
        self.images["gem1"] = self.load_image("宝石.png", (30, 30))
        self.images["gem2"] = self.load_image("宝石2.png", (33, 33))
        self.images["gem3"] = self.load_image("宝石3.png", (38, 38))
        self.images["gem4"] = self.load_image("宝石4.png", (42, 42))
        self.sounds["bgm_boss"] = self.load_sound("bgm_boss.ogg")
        self.sounds["warning"] = self.load_sound("warning.ogg")
        self.sounds["boom_l"] = self.load_sound("boom_l.ogg")
        self.sounds["crystal"] = self.load_sound("crystal.ogg")
        self.sounds["shield"] = self.load_sound("shield.ogg")
        self.sounds["powerup"] = self.load_sound("powerup.ogg")
        self.sounds["life"] = self.load_sound("life.ogg")
        self.sounds["upgrade"] = self.load_sound("upgrade.wav")
        self.sounds["rush"] = self.load_sound("rush.ogg")
        self.sounds["yahou"] = self.load_sound("yahou.wav")
        self.sounds["menu_bgm"] = self.load_sound("menu_bgm.ogg")
        self.images["damaged"] = [self.load_image("受伤1.png", (75, 90)),
                                  self.load_image("受伤2.png", (75, 90)),
                                  self.load_image("受伤3.png", (75, 90))]
        self.images["death"] = [self.load_image("死亡1.png", (75, 90)),
                                self.load_image("死亡2.png", (75, 90)),
                                self.load_image("死亡3.png", (75, 90))]
        #加载音效
        self.sounds["background"]=self.load_sound("game_music.wav")
        self.sounds["bullet"]=self.load_sound("bullet.wav")#子弹音效
        self.sounds["bomb"]=self.load_sound("use_bomb.wav")#爆炸声
        #加载页面
        self.images["start"]=self.load_image("start.png",(300,41))
        self.images["restart"]=self.load_image("again.png",(300,41))
        self.images["start_bg1"] = self.load_image("start1.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.images["start_bg2"] = self.load_image("start2.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.images["start_ui"] = self.load_image("start_ui.png", (300, 100))
        self.images["speaker_on"] = self.load_image("turn.png", (55, 49))
        self.images["speaker_off"] = self.load_image("turn_off.png", (55, 49))
        self.images["pause_btn"] = self.load_image("pause_nor.png", (40, 30))
        self.images["resume_btn"] = self.load_image("resume_nor.png", (40, 30))
        #加载字体
        font1 = self.load_font("C:/Windows/Fonts/simhei.ttf", 32)
        self.fonts["score"]=font1 #得分字体
        self.fonts["health"]=font1 #生命值字体


    # 加载字体
    def load_font(self,filename,size):
        font=pygame.font.Font(filename,size)
        return font
    #获取字体
    def get_font(self,key):
        return self.fonts[key]
        #加载音效
    def load_sound(self,filename):
        sound = pygame.mixer.Sound(os.path.join(SOUNDS_DIR,filename))
        sound.set_volume(1.0 if self.audio_enabled else 0.0)
        return sound
    #获取音效
    def get_sound(self,key):
        return self.sounds.get(key, SilentSound())
    #播放音效
    def play_sound(self,key):
        if not self.audio_enabled:
            return
        sound = self.sounds.get(key)
        if sound:
            sound.play()
    def set_audio_enabled(self, enabled):
        self.audio_enabled = bool(enabled)
        volume = 1.0 if self.audio_enabled else 0.0
        for sound in self.sounds.values():
            if hasattr(sound, "set_volume"):
                sound.set_volume(volume)
            if not self.audio_enabled and hasattr(sound, "stop"):
                sound.stop()
    def is_audio_enabled(self):
        return self.audio_enabled
    #加载图片
    def load_image(self, filename, size=None):
        img = pygame.image.load(os.path.join(IMAGES_DIR, filename))
        if size:
            img = pygame.transform.scale(img, size)
        return img

    #获取图片
    def get_image(self, key):
        return self.images[key]
#创建资源管理实例
resource_manager = ResourceManager()

