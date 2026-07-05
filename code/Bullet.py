# 子弹类sprites/Bullet.py
import pygame
from resource_manager import resource_manager as res
from sprites import Hero

# 子弹类
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = res.get_image('bullet.png')[0]
        # 子弹的位置
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = y  # 子弹的底部在飞机的顶部
        self.speed = 5
        # 精灵的存活状态
        self.active = True
    # 更新子弹的位置
    def update(self):
        self.rect.y += self.speed
        # 检查子弹是否超出屏幕
        if self.rect.y < 0:
            self.active = False