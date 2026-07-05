import pygame
import random
from resource_manager import resource_manager as res
from settings import SCREEN_HEIGHT


ENEMY_TYPES = {
    1: {"image": "enemy1", "hp": 2, "speed_range": (1, 3), "score": 1,
        "death_anim": "enemy1_down", "death_fps": 8, "hit_img": None},
    2: {"image": "enemy2", "hp": 5, "speed_range": (1, 2), "score": 3,
        "death_anim": "enemy2_down", "death_fps": 8, "hit_img": "enemy2_hit"},
    3: {"image": "enemy3_n", "hp": 9, "speed_range": (1, 2), "score": 5,
        "death_anim": "enemy3_down", "death_fps": 10, "hit_img": "enemy3_hit"},
}


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, enemy_type=1, speed_mult=1.0):
        super().__init__()
        cfg = ENEMY_TYPES[enemy_type]
        self.enemy_type = enemy_type
        self.max_hp = cfg["hp"]
        self.hp = cfg["hp"]
        self.score_value = cfg["score"]
        self.death_fps = cfg["death_fps"]
        self.hit_timer = 0

        img_data = res.get_image(cfg["image"])
        if isinstance(img_data, list):
            self.idle_images = img_data
        else:
            self.idle_images = [img_data]
        self.image = self.idle_images[0]
        self.death_images = res.get_image(cfg["death_anim"])
        if cfg["hit_img"]:
            self.hit_image = res.get_image(cfg["hit_img"])
        else:
            self.hit_image = None

        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

        spd_min, spd_max = cfg["speed_range"]
        self.speed = random.uniform(spd_min, spd_max) * speed_mult
        self.active = True
        self.dying = False
        self.image_index = 0
        self._tick = 0
        self._shoot_timer = random.randint(0, 90)

    def update(self):
        self._tick += 1

        if self.dying:
            if self.image_index < len(self.death_images) - 1:
                if self._tick % self.death_fps == 0:
                    self.image_index += 1
                    self.image = self.death_images[self.image_index]
            else:
                if self._tick % 20 == 0:
                    self.active = False
            return

        if self.hit_timer > 0:
            self.hit_timer -= 1
            if self.hit_timer == 0:
                self.image = self.idle_images[0]

        self.rect.y += self.speed
        if self.rect.top > SCREEN_HEIGHT:
            self.active = False

    def hit(self):
        if self.dying:
            return 0
        self.hp -= 1
        if self.hp <= 0:
            self.dying = True
            self.image_index = 0
            self.image = self.death_images[0]
            res.play_sound("bomb")
            return self.score_value
        else:
            self.hit_timer = 5
            if self.hit_image:
                self.image = self.hit_image
            return 0

    def shoot(self):
        if self.dying or not self.active or self.enemy_type == 1:
            return []
        if self.rect.top < 20:
            return []
        self._shoot_timer += 1
        interval = 150 if self.enemy_type == 2 else 110
        if self._shoot_timer < interval:
            return []
        self._shoot_timer = 0
        from sprites.Boss import BossBullet

        if self.enemy_type == 2:
            return [BossBullet(self.rect.centerx, self.rect.bottom, 0, 4)]
        return [
            BossBullet(self.rect.centerx, self.rect.bottom, -1.6, 4),
            BossBullet(self.rect.centerx, self.rect.bottom, 0, 4.4),
            BossBullet(self.rect.centerx, self.rect.bottom, 1.6, 4),
        ]
