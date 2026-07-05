import pygame
import random
import math
from pygame.sprite import Sprite
from resource_manager import resource_manager as res
from settings import SCREEN_WIDTH, SCREEN_HEIGHT


class BossBullet(Sprite):
    def __init__(self, x, y, vx, vy, size=1.0):
        super().__init__()
        self.image = res.get_image("enemy_bullet")[0]
        if size != 1.0:
            w = int(self.image.get_width() * size)
            h = int(self.image.get_height() * size)
            self.image = pygame.transform.scale(self.image, (w, h))
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.vx = vx
        self.vy = vy
        self.active = True

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        if (self.rect.top > SCREEN_HEIGHT or self.rect.bottom < 0 or
            self.rect.right < 0 or self.rect.left > SCREEN_WIDTH):
            self.active = False
            self.kill()

    def hit(self):
        self.active = False
        self.kill()
        return 0


class Boss(Sprite):
    """紫晶突击机 Boss-01"""
    def __init__(self, hp=50):
        super().__init__()
        self.enemy_type = 4
        self.active_score = 0  # 当前分数，解锁技能用
        self.boss_round = 1    # Boss轮次，影响频率和伤害
        self.max_hp = hp
        self.hp = hp
        self.idle_images = res.get_image("boss_idle")
        self.death_images = res.get_image("boss_death")
        self.image = self.idle_images[0]
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.top = -200
        self.active = True
        self.dying = False
        self.arrived = False
        self.phase = 1
        self._tick = 0
        self._frame_idx = 0
        self.hero = None

        # 攻击计时器
        self._track_timer = 0      # 追踪射击
        self._fan_timer = 0        # 扇形散射
        self._spiral_timer = 0     # 螺旋弹幕（二阶段）
        self._burst_timer = 0      # 追踪爆裂弹（二阶段）
        self._teleport_timer = 0   # 瞬移
        self._drift_dir = 1
        self._shake_timer = 0
        self._invincible_timer = 0
        self._death_frame_idx = 0
        # 隐形技能
        self.cloak_images = res.get_image("boss_cloak")
        self._cloak_timer = 0       # 技能冷却
        self._cloak_state = 0       # 0=正常, 1=隐形动画, 2=隐身中
        self._cloak_phase_tick = 0

    def update(self):
        self._tick += 1
        if self.dying:
            self._play_death()
            return
        if not self.arrived:
            self._enter_screen()
            return

        # 阶段切换无敌计时 + 闪烁
        if self._invincible_timer > 0:
            self._invincible_timer -= 1
            # 每4帧切换透明度
            if self._invincible_timer % 8 < 4:
                self.image.set_alpha(120)
            else:
                self.image.set_alpha(255)
        elif self._cloak_state == 0:
            self.image.set_alpha(255)  # 恢复正常
        # 检测阶段切换
        if self.hp <= self.max_hp // 2 and self.phase == 1:
            self.phase = 2
            self._shake_timer = 20
            self._invincible_timer = 300  # 5秒无敌

        if self._shake_timer > 0:
            self._shake_timer -= 1

        # 追踪英雄
        if self.hero and self.hero.active:
            tx = self.hero.rect.centerx
            self.rect.centerx += (tx - self.rect.centerx) * 0.015

        # 左右漂移
        self.rect.x += self._drift_dir * 0.8
        if self.rect.left < 30 or self.rect.right > SCREEN_WIDTH - 30:
            self._drift_dir *= -1

        # 帧动画（隐形时跳过）
        if self._cloak_state == 0:
            if self._tick % 8 == 0:
                self._frame_idx = (self._frame_idx + 1) % len(self.idle_images)
                self.image = self.idle_images[self._frame_idx]

        # 隐形技能（每10秒发动）
        self._cloak_timer += 1
        if self._cloak_timer >= 600 and self._cloak_state == 0:
            self._cloak_state = 1
            self._cloak_timer = 0
            self._cloak_phase_tick = 0
        if self._cloak_state == 1:
            self._cloak_phase_tick += 1
            # 3帧在1秒内播完（每帧约20帧）
            frame_idx = min(self._cloak_phase_tick // 20, 2)
            self.image = self.cloak_images[frame_idx]
            if self._cloak_phase_tick >= 60:
                self._cloak_state = 2
                self._cloak_phase_tick = 0
        elif self._cloak_state == 2:
            self._cloak_phase_tick += 1
            self.image.set_alpha(0)
            if self._cloak_phase_tick >= 60:
                self._cloak_state = 0
                self._cloak_phase_tick = 0
                self.image.set_alpha(255)
                self.image = self.idle_images[self._frame_idx]
                # 瞬移到新位置
                self.rect.centerx = random.randint(60, SCREEN_WIDTH - 60)
                self.rect.top = random.randint(40, 200)

        # 计时器
        self._track_timer += 1
        self._fan_timer += 1
        if self.phase == 2:
            self._spiral_timer += 1
            self._burst_timer += 1

    def _enter_screen(self):
        if self.rect.top < 80:
            self.rect.y += 2
        else:
            self.rect.top = 80
            self.arrived = True

    def shoot(self):
        """返回子弹列表"""
        bullets = []
        cx, cy = self.rect.centerx, self.rect.bottom - 20
        speed_mul = 1.4 if self.phase == 2 else 1.0
        # 频率：二阶段+30%，每轮Boss额外+10%
        freq_mul = (0.7 if self.phase == 2 else 1.0) * max(0.4, 1.0 - (self.boss_round - 1) * 0.1)
        # 子弹伤害：每轮+1
        bullet_damage = self.boss_round

        # 追踪射击：每72帧（1.2秒）3发
        track_interval = int(72 * freq_mul)
        if self._track_timer >= track_interval:
            self._track_timer = 0
            spd = int(3 * speed_mul)
            for i in range(3):
                ox = (i - 1) * 15
                if self.hero and self.hero.active:
                    dx = self.hero.rect.centerx - (cx + ox)
                    dy = self.hero.rect.centery - cy
                    dist = math.hypot(dx, dy)
                    if dist > 0:
                        vx = dx / dist * spd
                        vy = dy / dist * spd
                    else:
                        vx, vy = 0, spd
                else:
                    vx, vy = 0, spd
                bullets.append(BossBullet(cx + ox, cy, vx, vy))

        # 扇形散射：每240帧（4秒）9发，60°
        fan_interval = int(240 * freq_mul)
        if self._fan_timer >= fan_interval:
            self._fan_timer = 0
            spd = int(2.5 * speed_mul)
            for i in range(9):
                angle = math.radians(150 + i * 7.5)  # 60° spread, downward (150°-210° in math coords)
                vx = math.cos(angle) * spd
                vy = math.sin(angle) * spd
                bullets.append(BossBullet(cx, cy, vx, vy))

        # 二阶段专属
        if self.phase == 2:
            # 螺旋弹幕（500分解锁）
            if self.active_score >= 500 and self._spiral_timer >= 180:
                self._spiral_timer = 0
                # 持续3秒的螺旋：一次性发射多层
                for layer in range(4):  # 4层
                    for i in range(12):
                        angle = math.radians(i * 30 + layer * 30)
                        vx = math.cos(angle) * 3
                        vy = math.sin(angle) * 3
                        bullets.append(BossBullet(cx, cy, vx, vy))

            # 追踪爆裂弹（1000分解锁）
            if self.active_score >= 1000 and self._burst_timer >= 300:
                self._burst_timer = 0
                # 大球追踪玩家
                if self.hero and self.hero.active:
                    tx, ty = self.hero.rect.centerx, self.hero.rect.centery
                    dx = tx - cx
                    dy = ty - cy
                    dist = math.hypot(dx, dy)
                    vx = dx / dist * 2
                    vy = dy / dist * 2
                else:
                    vx, vy = 0, 2
                # 大球
                burst = BossBullet(cx, cy, vx, vy, size=2.5)
                burst._is_burst = True
                burst._cx = cx
                burst._cy = cy
                bullets.append(burst)


        return bullets

    def _play_death(self):
        if self._tick % 15 == 0:  # 慢速死亡动画
            if self._death_frame_idx < len(self.death_images) - 1:
                self._death_frame_idx += 1
                self.image = self.death_images[self._death_frame_idx]
            else:
                self.active = False

    def hit(self, damage=1):
        if self.dying or not self.arrived:
            return 0
        # 阶段切换时完全无敌
        if self._invincible_timer > 0:
            return 0
        # 二阶段常驻30%减伤
        if self.phase == 2:
            damage = max(1, int(damage * 0.7))
        self.hp -= damage
        if self.hp <= self.max_hp // 2 and self.phase == 1:
            self.phase = 2
            self._shake_timer = 20
            self._invincible_timer = 300  # 5秒无敌
            return 10
        if self.hp <= 0:
            self.dying = True
            self._cloak_state = 0
            self.image.set_alpha(255)
            self._death_frame_idx = 0
            self.image = self.death_images[0]
            res.play_sound("boom_l")
            return 100
        return 0

    @property
    def hp_ratio(self):
        return max(0, self.hp / self.max_hp)

    @property
    def shaking(self):
        return self._shake_timer > 0
