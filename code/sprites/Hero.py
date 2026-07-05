import pygame
from pygame.sprite import Sprite

from settings import SCREEN_WIDTH, SCREEN_HEIGHT
from resource_manager import resource_manager as res

# 英雄游戏精灵
class Hero(Sprite):
    # 初始化
    def __init__(self):
        super().__init__()
        self.images=res.get_image('hero')
        self.damaged_images=res.get_image('damaged')
        self.death_images=res.get_image('death')
        self.image=self.images[0]
        self.image_index=0
        self._tick = 0
        self.is_dying=False
        # 初始化英雄的位置
        self.rect=self.image.get_rect()
        self.rect.centerx=SCREEN_WIDTH//2
        self.rect.centery=SCREEN_HEIGHT-100
        #速度
        self.speed=5
        #生命
        self.max_hp = 10
        self.live = 10
        self.active=True
        #无敌状态
        self.invincible=False
        self.invincible_timer=0

    # 更新英雄动画帧
    def update(self):
        self._tick += 1
        if self.is_dying:
            if self.image_index < len(self.death_images) - 1:
                if self._tick % 8 == 0:
                    self.image_index += 1
                    self.image = self.death_images[self.image_index]
            else:
                if self._tick % 30 == 0:
                    self.active = False
        elif self.invincible:
            self.invincible_timer += 1
            if self.invincible_timer >= 60:
                self.invincible = False
                self.invincible_timer = 0
            if self._tick % 4 == 0:
                self.image_index = (self.image_index + 1) % len(self.damaged_images)
                self.image = self.damaged_images[self.image_index]
        else:
            if self._tick % 15 == 0:
                self.image_index = (self.image_index + 1) % len(self.images)
                self.image = self.images[self.image_index]

    # 开始死亡
    def die(self):
        self.is_dying = True
        self.image_index = 0
        self.image = self.death_images[0]

    #移动飞机
    def move(self,direction):
        dx,dy=direction[0],direction[1]
        if dx !=0 and dy !=0:
            dx *=0.7071
            dy *=0.7071
        self.rect.move_ip(dx*self.speed,dy*self.speed)
        self.rect.clamp_ip(0,0,SCREEN_WIDTH,SCREEN_HEIGHT)

    def shoot(self):
        from .Bullet import Bullet
        bullet = Bullet(self.rect.centerx, self.rect.top)
        return bullet

    # 英雄被击中
    def hit(self):
        if self.invincible:
            return
        # 设置无敌状态
        self.invincible=True
        #扣除生命值
        self.live-=1
        # 播放音效
        res.play_sound("bomb")

    @property
    def hp_ratio(self):
        return max(0, self.live / self.max_hp)

    def heal(self, amount=3):
        self.live = min(self.max_hp, self.live + amount)