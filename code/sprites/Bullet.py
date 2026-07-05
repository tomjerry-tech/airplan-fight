import pygame
import math
from resource_manager import resource_manager as res


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, speed=5, vx=0, image_key="bullet", img_idx=0, target=None):
        super().__init__()
        img_list = res.get_image(image_key)
        self.image = img_list[img_idx]
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = y
        self.speed = speed
        self.vx = vx
        self.active = True
        self.target = target

    def update(self):
        if self.target and self.target.active:
            dx = self.target.rect.centerx - self.rect.centerx
            dy = self.target.rect.centery - self.rect.centery
            dist = math.hypot(dx, dy)
            if dist > 0:
                self.rect.x += dx / dist * self.speed + self.vx
                self.rect.y += dy / dist * self.speed
        else:
            self.rect.y -= self.speed
            self.rect.x += self.vx
        if self.rect.bottom < 0 or self.rect.top > 800:
            self.active = False
            self.kill()
