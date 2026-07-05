import random
from pygame.sprite import Sprite
from resource_manager import resource_manager as res
from settings import SCREEN_HEIGHT


ITEM_TYPES = {
    "heal": {"img": "item_heal", "prob": 35},
    "shield": {"img": "item_shield", "prob": 15},
    "upgrade": {"img": "item_upgrade", "prob": 35},
    "track": {"img": "item_track", "prob": 15},
}

# 宝石配置：图片key, 分值, 掉落数量范围
GEM_CONFIG = {
    1: {"img": "gem1", "score": 1, "count": (1, 3)},
    2: {"img": "gem2", "score": 3, "count": (1, 2)},
    3: {"img": "gem3", "score": 5, "count": (1, 1)},
    4: {"img": "gem4", "score": 10, "count": (1, 1)},
}

# 敌机类型 → (宝石1概率, 宝石2概率, 宝石3概率, 宝石4概率)
ENEMY_GEM_DROP = {
    1: (0.6, 0.3, 0, 0),
    2: (0.4, 0.4, 0.15, 0.05),
    3: (0.2, 0.3, 0.4, 0.1),
    4: (0, 0.2, 0.4, 0.3),  # boss
}


class Item(Sprite):
    def __init__(self, x, y, item_type=None, gem_level=None):
        super().__init__()
        if item_type:
            self.item_type = item_type
            self.gem_level = gem_level
            if gem_level:
                self.image = res.get_image(GEM_CONFIG[gem_level]["img"])
            else:
                self.image = res.get_image(ITEM_TYPES[item_type]["img"])
        else:
            types = list(ITEM_TYPES.keys())
            weights = [ITEM_TYPES[t]["prob"] for t in types]
            self.item_type = random.choices(types, weights=weights, k=1)[0]
            self.image = res.get_image(ITEM_TYPES[self.item_type]["img"])
            self.gem_level = None

        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.speed = 2
        self.active = True

    def update(self, hero=None):
        self.rect.y += self.speed
        # 磁力吸附：离英雄100像素内自动吸过去
        if hero and hero.active and self.gem_level:
            dx = hero.rect.centerx - self.rect.centerx
            dy = hero.rect.centery - self.rect.centery
            dist = (dx*dx + dy*dy) ** 0.5
            if dist < 120 and dist > 0:
                self.rect.x += dx / dist * 4
                self.rect.y += dy / dist * 4
        if self.rect.top > SCREEN_HEIGHT:
            self.active = False
            self.kill()

    def apply(self, hero, game):
        if self.gem_level:
            cfg = GEM_CONFIG[self.gem_level]
            game.score += cfg["score"]
            res.play_sound("crystal")
        elif self.item_type == "heal":
            hero.heal(3)
            res.play_sound("life")
        elif self.item_type == "shield":
            hero.invincible = True
            hero.invincible_timer = 0
            res.play_sound("shield")
        elif self.item_type == "upgrade":
            dur = 480 + (120 if game.score >= 200 else 0)
            if game.upgrade_level < 3:
                game.upgrade_level += 1
                res.play_sound("upgrade")
                if game.upgrade_level >= 3:
                    game.berserk_timer = dur
                    res.play_sound("rush")
            else:
                game.berserk_timer = dur
                res.play_sound("rush")
        elif self.item_type == "track":
            game.track_timer = 600 + (300 if game.score >= 500 else 0)
            res.play_sound("rush")

    @staticmethod
    def spawn_gems(x, y, enemy_type):
        """根据敌机类型掉落宝石"""
        gems = []
        probs = ENEMY_GEM_DROP.get(enemy_type, (0.5, 0.3, 0.15, 0.05))
        for level, prob in enumerate(probs, 1):
            if prob > 0 and random.random() < prob:
                cfg = GEM_CONFIG[level]
                cmin, cmax = cfg["count"]
                count = random.randint(cmin, cmax)
                for _ in range(count):
                    ox = random.randint(-30, 30)
                    oy = random.randint(-20, 20)
                    gem = Item(x + ox, y + oy, item_type="gem", gem_level=level)
                    gem.speed = random.uniform(2, 4)  # 1.5倍速
                    gems.append(gem)
        return gems
