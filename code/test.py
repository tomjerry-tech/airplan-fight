import os
import random
import argparse
import subprocess
import sys
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
from resource_manager import resource_manager as res
from sprites import Hero
from sprites.Bullet import Bullet
from sprites.Enemy import Enemy
from sprites.EnemyManager import EnemyManager
from sprites.Boss import Boss
from sprites.Item import Item
from local_scores import submit_local_score


pygame.init()
print("success")
GAME_DURATION_SECONDS = 5 * 60
GAME_DURATION_TICKS = GAME_DURATION_SECONDS * FPS
BACK_BUTTON = pygame.Rect(SCREEN_WIDTH - 160, 8, 56, 30)


def format_time(ticks):
    seconds = max(0, ticks // FPS)
    return "{:02d}:{:02d}".format(seconds // 60, seconds % 60)


# 游戏状态
class GameState:
    START =0#游戏开始界面
    PLAYING=1#游戏进行
    PAUSED =2#游戏暂停
    GAME_OVER=3#游戏结束
    BOSS_WARNING=4#Boss警告
    BOSS_BATTLE=5#Boss战
    PAUSED=6#暂停
# 游戏类
class Game:
    def __init__(self, mode="single", player_name=None):
        self.mode = mode
        self.player_name = player_name
        self.shoot_timer =0
        self.shoot_interval =0
        self.print_timer = 0#jiade
        self.enemy_manager = EnemyManager()
        # 子弹精灵组
        self.bullet_sprites_group=pygame.sprite.Group()
        # 敌机精灵组
        self.enemy_sprites_group=pygame.sprite.Group()
        self.boss_bullet_group=pygame.sprite.Group()
        # 得分
        self.score = 0
        self.power_timer = 0
        self.upgrade_level = 0   # 升级等级 0-3
        self.berserk_timer = 0   # 暴走倒计时
        self.track_timer = 0     # 追踪弹倒计时
        self.auto_shield_timer = 0
        self.bg_offset = 0       # 背景滚动偏移
        self._start_anim = 0     # 0=待机 1=动画中
        self._start_timer = 0
        # 道具组
        self.item_sprites_group = pygame.sprite.Group()
        # Boss相关
        self.boss = None
        self.boss_warn_timer = 0
        self.score_saved = False
        self.score_save_result = None
        self.elapsed_ticks = 0
        self.duration_ticks = GAME_DURATION_TICKS if self.mode == "single" else None
        self.touch_control = False
        self.touch_target = None
        self.sound_enabled = True
        #初始状态
        self.state=GameState.START
    #重新开始游戏
    def restart(self):
        #清理所有精灵
        self.all_sprites_group.empty()
        self.bullet_sprites_group.empty()
        self.enemy_sprites_group.empty()
        self.boss_bullet_group.empty()
        self.item_sprites_group.empty()
        if self.hero:
            self.hero.kill()
        self.hero = Hero()
        self.all_sprites_group.add(self.hero)
        #重置状态
        self.score = 0
        self.boss = None
        self.boss_warn_timer = 0
        self.score_saved = False
        self.score_save_result = None
        self.elapsed_ticks = 0
        self.power_timer = 0
        self.upgrade_level = 0
        self.berserk_timer = 0
        self.track_timer = 0
        self.auto_shield_timer = 0
        self.touch_control = False
        self.touch_target = None
        res.set_audio_enabled(self.sound_enabled)
        self.bg_offset = 0
        self._start_anim = 0
        self._start_timer = 0
        self.state=GameState.PLAYING
        self.enemy_manager.reset()
    #控制玩家飞机移动
    def hero_control(self):
        if self.state not in (GameState.PLAYING, GameState.BOSS_BATTLE):
            return
        if self.touch_control and self.touch_target:
            target_x, target_y = self.touch_target
            dx = target_x - self.hero.rect.centerx
            dy = target_y - self.hero.rect.centery
            dist = max(1, (dx * dx + dy * dy) ** 0.5)
            if dist > self.hero.speed:
                self.hero.move([dx / dist, dy / dist])
            else:
                self.hero.rect.center = (target_x, target_y)
                self.hero.rect.clamp_ip(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
            return
        direction = [0, 0]
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            direction[0] = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            direction[0] = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            direction[1] = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            direction[1] = 1
        #移动飞机
        self.hero.move(direction)
    # 自动射击子弹
    def auto_shoot(self):
        if self.state not in (GameState.PLAYING, GameState.BOSS_BATTLE):
            return
        if self.berserk_timer > 0:
            self.berserk_timer -= 1
        if self.track_timer > 0:
            self.track_timer -= 1

        is_berserk = self.berserk_timer > 0
        is_track = self.track_timer > 0
        interval = 15 if is_berserk else 25 if is_track else 35
        self.shoot_timer += 1
        if self.shoot_timer < interval:
            return
        self.shoot_timer = 0

        from sprites.Bullet import Bullet
        # 追踪目标
        target = None
        if is_track:
            min_dist = 9999
            for e in self.enemy_sprites_group:
                if e.active and not getattr(e, 'dying', False):
                    d = abs(e.rect.centery - self.hero.rect.top)
                    if d < min_dist:
                        min_dist = d
                        target = e

        img_idx = 3 if is_track else 0  # 追踪用子弹4

        if is_berserk:
            # 暴走：5行扇形，叠加追踪
            for i in range(5):
                vx = (i - 2) * 6  # 更宽的扇形扩散
                b = Bullet(self.hero.rect.centerx, self.hero.rect.top,
                          speed=15, vx=vx, img_idx=img_idx, target=target)
                self.all_sprites_group.add(b)
                self.bullet_sprites_group.add(b)
        else:
            # 普通/升级，叠加追踪
            rows = min(self.upgrade_level + 1, 3)
            spd = 15 if is_track else 5
            for i in range(rows):
                spacing = 15 * (rows - 1)
                x = self.hero.rect.centerx - spacing // 2 + i * 15
                b = Bullet(x, self.hero.rect.top, speed=spd, img_idx=img_idx, target=target)
                self.all_sprites_group.add(b)
                self.bullet_sprites_group.add(b)
        res.play_sound("bullet")

    # 自动创建敌人精灵
    def create_enemy(self):
        enemies = self.enemy_manager.update(self.score)
        if enemies == "WARNING":
            return "WARNING"
        if isinstance(enemies, list) and enemies:
            for enemy in enemies:
                self.all_sprites_group.add(enemy)
                self.enemy_sprites_group.add(enemy)
    def spawn_enemy_bullets(self):
        for enemy in list(self.enemy_sprites_group):
            if isinstance(enemy, Enemy):
                for bullet in enemy.shoot():
                    self.all_sprites_group.add(bullet)
                    self.boss_bullet_group.add(bullet)
    #销毁所有游戏精灵
    def remove_inactive_sprites(self):
        for sprite in self.all_sprites_group:
            if not sprite.active:
                self.all_sprites_group.remove(sprite)
                if sprite in self.enemy_sprites_group:
                    self.enemy_sprites_group.remove(sprite)
                if sprite in self.bullet_sprites_group:
                    self.bullet_sprites_group.remove(sprite)
                # 正式销毁精灵
                sprite.kill()
    def check_collision(self):
        # 子弹和敌人碰撞
        collisions = pygame.sprite.groupcollide(self.bullet_sprites_group, self.enemy_sprites_group, False,False)
        if collisions:
            for bullet in collisions:
                bullet.active = False
                for enemy in collisions[bullet]:
                    enemy.hit()
                    # 击杀敌人掉落道具（得分全靠宝石）
                    from sprites.Enemy import Enemy as EC
                    if isinstance(enemy, EC):
                        etype = getattr(enemy, 'enemy_type', 1)
                        for gem in Item.spawn_gems(enemy.rect.centerx, enemy.rect.centery, etype):
                            self.all_sprites_group.add(gem)
                            self.item_sprites_group.add(gem)
                        drop_rate = EnemyManager.get_item_drop_rate(self.score)
                        if random.random() < drop_rate:
                            item = Item(enemy.rect.centerx, enemy.rect.centery)
                            self.all_sprites_group.add(item)
                            self.item_sprites_group.add(item)
    # 英雄与敌人碰撞
        if not  self.hero.invincible:
            for enemy in self.enemy_sprites_group:
                if enemy.active:
                    if pygame.sprite.collide_mask(self.hero,enemy):
                        self.hero.hit()
                        self.hit_enemy(enemy)
                        if self.hero.live <= 0:
                            self.state = GameState.GAME_OVER
                            self.hero.die()
                            self._stop_all_music()
                            self.save_local_score_once()
                        break
        # Boss子弹伤害英雄
        if not self.hero.invincible:
            for bb in self.boss_bullet_group:
                if bb.active and pygame.sprite.collide_mask(self.hero, bb):
                    self.hero.hit()
                    bb.kill()
                    if self.hero.live <= 0:
                        self.state = GameState.GAME_OVER
                        self.hero.die()
                        self._stop_all_music()
                        self.save_local_score_once()
                    break
        # 英雄收集道具
        for item in pygame.sprite.spritecollide(self.hero, self.item_sprites_group, False):
            item.apply(self.hero, self)
            item.kill()
    def hit_enemy(self,enemy):
        #敌人被集中
        score=enemy.hit()
        # 增加得分
        self.score+=score

    def hit_hero(self):
        self.hero.hit()
        if self.hero.live <= 0:
            self.state = GameState.GAME_OVER
            self.hero.active = False
            self.save_local_score_once()

    # Boss战相关
    def start_boss_battle(self):
        self.boss = self.enemy_manager.spawn_boss(self.score)
        self.boss.hero = self.hero  # Boss锁定英雄
        self.all_sprites_group.add(self.boss)
        self.enemy_sprites_group.add(self.boss)
        self.state = GameState.BOSS_BATTLE
        if self.sound_enabled:
            res.get_sound("bgm_boss").play(-1)

    def end_boss_battle(self):
        self.enemy_manager.on_boss_defeated()
        self.boss = None
        self.state = GameState.PLAYING
        if self.sound_enabled:
            res.get_sound("background").play(-1)

    def check_time_limit(self):
        if not self.duration_ticks:
            return
        if self.state not in (GameState.PLAYING, GameState.BOSS_BATTLE, GameState.BOSS_WARNING):
            return
        self.elapsed_ticks += 1
        if self.elapsed_ticks >= self.duration_ticks:
            self.state = GameState.GAME_OVER
            self._stop_all_music()
            self.save_local_score_once()

    def remaining_ticks(self):
        if not self.duration_ticks:
            return None
        return max(0, self.duration_ticks - self.elapsed_ticks)

    def draw_hp_bar(self, screen):
        if not self.boss or not self.boss.arrived:
            return
        ratio = self.boss.hp_ratio
        bar_w, bar_h = 250, 12
        x = (SCREEN_WIDTH - bar_w) // 2
        y = 5
        pygame.draw.rect(screen, (40, 40, 40), (x, y, bar_w, bar_h))
        pygame.draw.rect(screen, (220, 30, 30), (x, y, int(bar_w * ratio), bar_h))
        pygame.draw.rect(screen, (255, 255, 255), (x, y, bar_w, bar_h), 1)
        self.draw_text(screen, "紫晶突击机", res.get_font("health"), (200, 100, 255), (SCREEN_WIDTH // 2 - 40, 18))

    def draw_boss_warning(self, screen):
        if self.boss_warn_timer // 15 % 2 == 0:
            self.draw_text(screen, "WARNING", res.get_font("score"), (255, 0, 0), (SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT // 2))

    def _handle_pause_click(self, mx, my):
        # 按钮区域
        cy = SCREEN_HEIGHT // 2
        # 返回游戏
        if cy - 60 < my < cy - 20 and SCREEN_WIDTH // 2 - 80 < mx < SCREEN_WIDTH // 2 + 80:
            self.state = GameState.PLAYING if not self.boss else GameState.BOSS_BATTLE
        # 重新开始
        elif cy - 5 < my < cy + 35 and SCREEN_WIDTH // 2 - 80 < mx < SCREEN_WIDTH // 2 + 80:
            self.restart()
        # 返回主界面
        elif cy + 50 < my < cy + 90 and SCREEN_WIDTH // 2 - 80 < mx < SCREEN_WIDTH // 2 + 80:
            self.restart()
            self.state = GameState.START
            self._start_anim = 0
            self._start_timer = 0

    def draw_pause_menu(self, screen):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((20, 10, 40))
        screen.blit(overlay, (0, 0))

        title = res.get_font("score").render("暂 停", True, (200, 180, 255))
        screen.blit(title, (SCREEN_WIDTH // 2 - 40, SCREEN_HEIGHT // 2 - 130))

        cy = SCREEN_HEIGHT // 2
        btns = [("返回游戏", cy - 60), ("重新开始", cy - 5), ("返回主界面", cy + 50)]
        for text, y in btns:
            color = (150, 200, 255) if pygame.mouse.get_pos()[1] > y and pygame.mouse.get_pos()[1] < y + 40 else (100, 140, 200)
            pygame.draw.rect(screen, color, (SCREEN_WIDTH // 2 - 80, y, 160, 35), 2)
            t = res.get_font("health").render(text, True, color)
            screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, y + 5))

    def _play_menu_bgm(self):
        if not self.sound_enabled:
            return
        if not getattr(self, '_menu_bgm_playing', False):
            # 暂停游戏背景音乐
            res.get_sound("background").stop()
            self._menu_bgm = res.get_sound("menu_bgm")
            self._menu_bgm.play(-1)
            self._menu_bgm_playing = True
            return
            self._menu_bgm = pygame.mixer.Sound(r"C:\Users\bill\Desktop\期末实训\assets\sounds\menu_bgm.ogg")
            self._menu_bgm.play(-1)
            self._menu_bgm_playing = True

    def _stop_all_music(self):
        """停止所有音乐"""
        if getattr(self, '_menu_bgm_playing', False):
            self._menu_bgm.stop()
            self._menu_bgm_playing = False
        res.get_sound("background").stop()
        res.get_sound("bgm_boss").stop()

    def _stop_menu_bgm(self):
        if getattr(self, '_menu_bgm_playing', False):
            self._menu_bgm.stop()
            self._menu_bgm_playing = False
            if self.sound_enabled and self.state in (GameState.PLAYING, GameState.BOSS_BATTLE, GameState.BOSS_WARNING):
                res.get_sound("background").play(-1)

    def toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        res.set_audio_enabled(self.sound_enabled)
        self._menu_bgm_playing = False
        if not self.sound_enabled:
            return
        if self.state == GameState.START:
            self._play_menu_bgm()
        elif self.state == GameState.BOSS_BATTLE and self.boss:
            res.get_sound("bgm_boss").play(-1)
        elif self.state in (GameState.PLAYING, GameState.BOSS_WARNING, GameState.PAUSED):
            res.get_sound("background").play(-1)

    def draw_game_speaker(self, screen):
        if self.state in (GameState.PLAYING, GameState.BOSS_BATTLE, GameState.PAUSED):
            spk = res.get_image("speaker_on") if self.sound_enabled else res.get_image("speaker_off")
            screen.blit(spk, (SCREEN_WIDTH - 95, 6))

    def draw_gear_btn(self, screen):
        if self.state in (GameState.PLAYING, GameState.BOSS_BATTLE):
            btn = res.get_image("pause_btn")
            screen.blit(btn, (SCREEN_WIDTH - 45, 8))

    def draw_back_button(self, screen):
        if self.state in (GameState.PLAYING, GameState.BOSS_BATTLE, GameState.BOSS_WARNING, GameState.PAUSED):
            pygame.draw.rect(screen, (50, 58, 100), BACK_BUTTON, border_radius=6)
            pygame.draw.rect(screen, (230, 238, 255), BACK_BUTTON, width=2, border_radius=6)
            text = res.get_font("health").render("返回", True, (245, 248, 255))
            screen.blit(text, text.get_rect(center=BACK_BUTTON.center))

    def launch_main_menu(self):
        root = os.path.dirname(os.path.abspath(__file__))
        subprocess.Popen([sys.executable, os.path.join(root, "main_menu.py")], cwd=root)

    def draw_start_screen(self, screen):
        ui = res.get_image("start_ui")
        ui_rect = ui.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100))
        if self._start_anim == 0:
            # 待机：start1 + UI
            screen.blit(res.get_image("start_bg1"), (0, 0))
            screen.blit(ui, ui_rect)
        else:
            self._start_timer += 1
            if self._start_timer <= 15:
                # 点击反馈：UI下移+缩小模拟按下
                screen.blit(res.get_image("start_bg1"), (0, 0))
                pressed = pygame.transform.scale(res.get_image("start_ui"), (270, 90))
                pr = pressed.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 95))
                screen.blit(pressed, pr)
            elif self._start_timer <= 30:
                screen.blit(res.get_image("start_bg2"), (0, 0))
                screen.blit(ui, ui_rect)
            else:
                # 停留
                screen.blit(res.get_image("start_bg2"), (0, 0))
                screen.blit(ui, ui_rect)
                if self._start_timer >= 60:
                    self.state = GameState.PLAYING
                    self._start_anim = 0
                    self._start_timer = 0
        # 喇叭图标（背景之上）
        self.draw_mode_start_button(screen)
        spk_img = res.get_image("speaker_on") if self.sound_enabled else res.get_image("speaker_off")
        screen.blit(spk_img, (SCREEN_WIDTH - 50, 12))
        self.draw_mode_badge(screen)

    def draw_mode_start_button(self, screen):
        label = "开始单人模式" if self.mode == "single" else "开始无尽模式"
        font = res.get_font("score")
        text = font.render(label, True, (255, 245, 255))
        rect = pygame.Rect(86, SCREEN_HEIGHT - 132, 308, 72)
        pygame.draw.rect(screen, (255, 214, 232), rect, border_radius=18)
        pygame.draw.rect(screen, (236, 103, 181), rect, width=4, border_radius=18)
        screen.blit(text, text.get_rect(center=rect.center))

    def draw_mode_badge(self, screen):
        label = "单人模式  5分钟挑战" if self.mode == "single" else "无尽模式  无时间终点"
        font = res.get_font("health")
        text = font.render(label, True, (255, 245, 255))
        padding_x, padding_y = 18, 8
        rect = pygame.Rect(0, 0, text.get_width() + padding_x * 2, text.get_height() + padding_y * 2)
        rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 172)
        pygame.draw.rect(screen, (236, 103, 181), rect, border_radius=10)
        pygame.draw.rect(screen, (255, 250, 255), rect, width=2, border_radius=10)
        screen.blit(text, text.get_rect(center=rect.center))

    def draw_text(self,screen,text,font,color,pos):
        #渲染文本
        text_surface = font.render(text, True, color)
        # 获取文本地形
        text_rect = text_surface.get_rect()
        text_rect.left = pos[0]
        text_rect.top = pos[1]
        # 绘制文本到窗口
        screen.blit(text_surface, text_rect)

    def save_local_score_once(self):
        if self.score_saved:
            return self.score_save_result
        mode = "single" if self.mode == "single" else "endless"
        player_name = self.player_name or ("local_single" if mode == "single" else "local_end")
        self.score_save_result = submit_local_score(self.score, mode, player_name)
        self.score_saved = True
        return self.score_save_result

    # 游戏运行
    def run(self):
        pygame.init()
        # 初始化窗口
        screen=pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT))
        # 将当前屏幕保存到屏幕中
        self.screen=screen
        pygame.display.set_caption("飞机大战")
        #设置游戏帧率
        clock=pygame.time.Clock()
        res.load_all_resources()
        #创建英雄精灵
        self.hero=Hero()
        self.all_sprites_group=pygame.sprite.Group()
        self.all_sprites_group.add(self.hero)
        # 创建精灵
        # 游戏循环
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit() # 退出游戏
                    return
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    if self.state == GameState.START and self._start_anim == 0:
                        # 点击喇叭（切换）
                        if mx > SCREEN_WIDTH - 55 and mx < SCREEN_WIDTH - 5 and my > 5 and my < 50:
                            self.toggle_sound()
                        else:
                            self._start_anim = 1
                            self._start_timer = 0
                            res.play_sound("yahou")
                            continue
                            pygame.mixer.Sound(r"C:\Users\bill\Desktop\期末实训\assets\sounds\yahou.wav").play()
                    elif self.state == GameState.GAME_OVER:
                        if my > SCREEN_HEIGHT // 2 + 20 and my < SCREEN_HEIGHT // 2 + 60:
                            self.restart()
                            self.state = GameState.START
                            self._start_anim = 0
                            self._start_timer = 0
                        else:
                            self.restart()
                    elif self.state == GameState.PAUSED:
                        self._handle_pause_click(mx, my)
                    elif self.state in (GameState.PLAYING, GameState.BOSS_BATTLE):
                        if BACK_BUTTON.collidepoint(event.pos):
                            self._stop_all_music()
                            pygame.quit()
                            self.launch_main_menu()
                            return
                        # 点击喇叭
                        elif mx > SCREEN_WIDTH - 100 and mx < SCREEN_WIDTH - 50 and my < 45:
                            self.toggle_sound()
                        # 点击齿轮暂停
                        elif mx > SCREEN_WIDTH - 50 and my < 45:
                            self.state = GameState.PAUSED
                        else:
                            self.touch_control = True
                            self.touch_target = event.pos
                        #3
                if event.type == pygame.MOUSEMOTION and self.touch_control:
                    self.touch_target = event.pos
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.touch_control = False
                    self.touch_target = None
                if event.type == pygame.FINGERDOWN:
                    self.touch_control = True
                    self.touch_target = (int(event.x * SCREEN_WIDTH), int(event.y * SCREEN_HEIGHT))
                if event.type == pygame.FINGERMOTION and self.touch_control:
                    self.touch_target = (int(event.x * SCREEN_WIDTH), int(event.y * SCREEN_HEIGHT))
                if event.type == pygame.FINGERUP:
                    self.touch_control = False
                    self.touch_target = None
            # 5000分自动护盾
            if self.score >= 5000 and self.state in (GameState.PLAYING, GameState.BOSS_BATTLE):
                self.auto_shield_timer += 1
                if self.auto_shield_timer >= 1800:  # 每30秒
                    self.auto_shield_timer = 0
                    self.hero.invincible = True
                    self.hero.invincible_timer = 0
            #控制玩家移动
            self.hero_control()
            in_game = self.state in (GameState.PLAYING, GameState.BOSS_BATTLE, GameState.BOSS_WARNING)
            if in_game:
                self.check_time_limit()
                in_game = self.state in (GameState.PLAYING, GameState.BOSS_BATTLE, GameState.BOSS_WARNING)
            if in_game:
                # 更新精灵
                self.all_sprites_group.update()
                self.item_sprites_group.update(self.hero)
                # 自动射击
                self.auto_shoot()
                # 创建敌人/Boss处理
                if self.state == GameState.PLAYING:
                    result = self.create_enemy()
                    if result == "WARNING":
                        self.state = GameState.BOSS_WARNING
                        self.boss_warn_timer = 60
                        res.play_sound("warning")
                # Boss警告倒计时
                if self.state == GameState.BOSS_WARNING:
                    self.boss_warn_timer -= 1
                    if self.boss_warn_timer <= 0:
                        self.start_boss_battle()
                # 碰撞检测
                self.check_collision()
                # Boss射击
                if self.boss:
                    for bb in self.boss.shoot():
                        self.all_sprites_group.add(bb)
                        self.boss_bullet_group.add(bb)
                self.spawn_enemy_bullets()
                # Boss状态更新
                if self.boss and not self.boss.active:
                    self.end_boss_battle()
                # 清理
                self.remove_inactive_sprites()
            # 屏幕震动
            shake_x = shake_y = 0
            if self.boss and getattr(self.boss, 'shaking', False):
                shake_x = random.randint(-3, 3)
                shake_y = random.randint(-2, 2)
            # 滚动背景
            if self.state in (GameState.PLAYING, GameState.BOSS_WARNING, GameState.BOSS_BATTLE):
                self.bg_offset = (self.bg_offset + 1) % 1130
            bg = res.get_image("bg_scroll")
            screen.blit(bg, (shake_x, shake_y + self.bg_offset))
            screen.blit(bg, (shake_x, shake_y + self.bg_offset - 1130))
            # 精灵层
            self.all_sprites_group.draw(screen)
            # 开始/结束页面
            if self.state == GameState.START:
                self.draw_start_screen(screen)
            if self.state == GameState.GAME_OVER:
                screen.blit(res.get_image("restart"), (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 130))
                # 返回主界面按钮
                mx, my = pygame.mouse.get_pos()
                btn_rect = pygame.Rect(SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT // 2 + 20, 160, 40)
                hover = btn_rect.collidepoint(mx, my)
                color = (150, 200, 255) if hover else (100, 140, 200)
                pygame.draw.rect(screen, color, btn_rect, 2)
                t = res.get_font("health").render("返回主界面", True, color)
                screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, SCREEN_HEIGHT // 2 + 28))
            # Boss警告
            if self.state == GameState.BOSS_WARNING:
                self.draw_boss_warning(screen)
            # 齿轮按钮
            self.draw_game_speaker(screen)
            self.draw_gear_btn(screen)
            self.draw_back_button(screen)
            # 暂停菜单
            if self.state == GameState.PAUSED:
                self.draw_pause_menu(screen)
            # Boss血条
            if self.state == GameState.BOSS_BATTLE:
                self.draw_hp_bar(screen)
            # 得分（游戏中才显示）
            if self.state in (GameState.PLAYING, GameState.BOSS_BATTLE, GameState.BOSS_WARNING, GameState.PAUSED):
                self.draw_text(screen, f"得分:{self.score}", res.get_font("score"), (255, 255, 255), (20, 55))
                remaining = self.remaining_ticks()
                timer_text = "时间:{}".format(format_time(remaining)) if remaining is not None else "时间:无尽"
                self.draw_text(screen, timer_text, res.get_font("health"), (255, 255, 255), (20, 88))
            # 生命血条（游戏中才显示）
            if self.state in (GameState.PLAYING, GameState.BOSS_BATTLE, GameState.BOSS_WARNING, GameState.PAUSED):
                bar_w, bar_h = 150, 12
                bar_x, bar_y = 20, 35
                ratio = self.hero.hp_ratio
                pygame.draw.rect(screen, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h))
                if ratio > 0.5:
                    color = (int(255*(1-ratio)*2), 200, 30)
                elif ratio > 0.25:
                    color = (255, int(200*ratio*2), 30)
                else:
                    color = (220, 30, 30)
                pygame.draw.rect(screen, color, (bar_x, bar_y, int(bar_w * ratio), bar_h))
                pygame.draw.rect(screen, (180, 180, 180), (bar_x, bar_y, bar_w, bar_h), 1)
                self.draw_text(screen, "HP:{}/{}".format(self.hero.live, self.hero.max_hp), res.get_font("health"), (255, 255, 255), (20, 16))
            #刷新显示
            self.print_timer += 1  # ← 加这行
            if self.print_timer >= 60:  # ← 加这行
                self.print_timer = 0  # ← 加这行
                print(f"精灵数量: {len(self.all_sprites_group)}")  # ← 加这行
            pygame.display.flip()
            clock.tick(FPS)
    pass
#调用主函数
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["single", "endless"], default="single")
    parser.add_argument("--name")
    args = parser.parse_args()
    game = Game(mode=args.mode, player_name=args.name)
    game.run()
