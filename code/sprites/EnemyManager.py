import random
from sprites.Enemy import Enemy
from sprites.Boss import Boss
from settings import SCREEN_WIDTH


class EnemyManager:
    def __init__(self):
        self.timer = 0
        self.interval = 0
        self.boss_triggered = False
        self.boss_active = False
        self._boss_threshold = 40

    def reset(self):
        self.timer = 0
        self.interval = 0
        self.boss_triggered = False
        self.boss_active = False
        self._boss_threshold = 40

    def get_tier(self, score):
        if score < 200: return 0
        if score < 500: return 1
        if score < 1000: return 2
        if score < 2000: return 3
        if score < 5000: return 4
        return 5

    def update(self, score):
        self.timer += 1
        tier = self.get_tier(score)

        if self.boss_active:
            return []

        if not self.boss_active:
            if self.boss_triggered:
                if score >= self._boss_threshold:
                    self.boss_triggered = False
            if not self.boss_triggered and score >= self._boss_threshold:
                self.boss_triggered = True
                self.boss_active = True
                return "WARNING"

        if self.timer < self.interval:
            return []
        self.timer = 0
        interval_table = [
            (70, 135),
            (54, 112),
            (42, 88),
            (32, 68),
            (24, 52),
            (18, 42),
        ]
        self.interval = random.randint(*interval_table[tier])

        # 敌机权重
        weight_table = [
            [80, 20, 0],    # 0-200
            [55, 35, 10],   # 200-500
            [30, 40, 30],   # 500-1000
            [15, 35, 50],   # 1000-2000
            [5, 25, 70],    # 2000-5000
            [0, 15, 85],    # 5000+
        ][tier]
        enemy_type = random.choices([1, 2, 3], weights=weight_table, k=1)[0]

        # 速度倍率
        speed_table = [1.0, 1.3, 1.5, 1.8, 2.0, 2.5]
        speed_mult = speed_table[tier]

        enemies = []
        spawn_count = [1, 1, 2, 2, 3, 3][tier]
        for _ in range(spawn_count):
            if enemy_type == 1:
                enemies.append(Enemy(random.randint(20, SCREEN_WIDTH - 57), -20, 1, speed_mult))
            elif enemy_type == 2:
                enemies.append(Enemy(random.randint(30, SCREEN_WIDTH - 69), -30, 2, speed_mult))
            else:
                enemies.append(Enemy(random.randint(50, SCREEN_WIDTH - 169), -50, 3, speed_mult * 0.7))
        return enemies

    def spawn_boss(self, score):
        hp = 80 + (self._boss_threshold // 1000) * 40
        boss = Boss(hp=hp)
        boss.active_score = score
        boss.boss_round = self._boss_threshold // 1000 + 1  # 轮次：1,2,3...
        return boss

    def on_boss_defeated(self):
        self.boss_active = False
        self.boss_triggered = True
        self._boss_threshold += 1000

    @staticmethod
    def get_hero_berserk_duration(score):
        base = 480
        if score >= 200: base += 120  # +2s
        return base

    @staticmethod
    def get_hero_track_duration(score):
        base = 600
        if score >= 500: base += 300  # +5s
        return base

    @staticmethod
    def get_bullet_damage(score):
        return 2 if score >= 1000 else 1

    @staticmethod
    def get_auto_shield(score):
        return score >= 5000

    @staticmethod
    def get_item_drop_rate(score):
        if score < 200: return 0.30
        if score < 500: return 0.25
        if score < 1000: return 0.20
        if score < 2000: return 0.15
        if score < 5000: return 0.10
        return 0.05
