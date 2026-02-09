import arcade
from pathlib import Path
from arcade import Camera2D
from arcade.particles import FadeParticle, Emitter, EmitMaintainCount, EmitBurst
import math
import random
from PIL import Image, ImageOps
import csv
import os

# Частицы
spark_tex = [
    arcade.make_soft_circle_texture(6, arcade.color.WHITE, 210),
    arcade.make_soft_circle_texture(4, arcade.color.LIGHT_GRAY, 170),
]


def make_trail(attached_sprite, maintain=38):
    return Emitter(
        center_xy=(attached_sprite.center_x, attached_sprite.center_y),
        emit_controller=EmitMaintainCount(maintain),
        particle_factory=lambda e: FadeParticle(
            filename_or_texture=random.choice(spark_tex),
            change_xy=arcade.math.rand_in_circle((0.0, 0.0), 1.1),
            lifetime=random.uniform(0.22, 0.42),
            start_alpha=190,
            end_alpha=0,
            scale=random.uniform(0.16, 0.28),
        ),
    )


explosion_tex = [
    arcade.make_soft_circle_texture(14, arcade.color.CANDY_APPLE_RED, 240),
    arcade.make_soft_circle_texture(12, arcade.color.ORANGE_RED, 220),
    arcade.make_soft_circle_texture(10, arcade.color.DARK_ORANGE, 200),
]


def make_explosion(center_x, center_y):
    return Emitter(
        center_xy=(center_x, center_y),
        emit_controller=EmitBurst(50),
        particle_factory=lambda e: FadeParticle(
            filename_or_texture=random.choice(explosion_tex),
            change_xy=arcade.math.rand_in_circle((0.0, 0.0), 5.0),
            lifetime=random.uniform(0.5, 0.8),
            start_alpha=230,
            end_alpha=0,
            scale=random.uniform(0.4, 0.7),
        ),
    )


# Константы
screen_width = 800
screen_height = 700
screen_title = "Celeste"
gravity = 0.9
move_speed = 1.6
jump_speed = 5.8
coyote_time = 0.08
jump_buffer = 0.12
max_jumps = 1
dash_duration = 0.12
dash_speed = 300.0
dash_post_impulse = 6
max_dashes = 1
camera_lerp = 0.12
max_stamina = 5.0
climb_speed = 0.85
wall_dash_stamina_cost = 2.0
sprite_scale = 0.35
map_scaling = 0.5
tile_size = 16 * map_scaling
STATS_FILE = "game_stats.csv"
WORLD_COLOR = arcade.color.SKY_BLUE  # ← ДОБАВЛЕНА КОНСТАНТА ФОНА


class StatsView(arcade.View):
    def __init__(self, menu_view):
        super().__init__()
        self.menu_view = menu_view
        self.title = arcade.Text("СТАТИСТИКА ИГРОКОВ", screen_width / 2, screen_height - 60,
                                 arcade.color.WHITE, 42, anchor_x="center", bold=True)
        self.back_button = [
            screen_width / 2 - 100, screen_width / 2 + 100, 40, 90,
            arcade.Text("Назад", screen_width / 2, 65, arcade.color.WHITE, 24, anchor_x="center", anchor_y="center"),
            self.go_back
        ]
        self.header_texts = [
            arcade.Text("Игрок", 150, screen_height - 120, arcade.color.CYAN, 18, bold=True),
            arcade.Text("Смерти", 400, screen_height - 120, arcade.color.RED, 18, bold=True, anchor_x="center"),
            arcade.Text("Фрукты", 650, screen_height - 120, arcade.color.GOLD, 18, bold=True, anchor_x="center"),
        ]
        self.player_rows = []
        self.load_stats_data()

    def load_stats_data(self):
        players = []
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        name = row.get("player_name", "").strip()
                        if name:
                            players.append({
                                "name": name,
                                "deaths": int(row.get("deaths", 0)),
                                "fruits": int(row.get("fruits_collected", 0))
                            })
            except:
                pass

        players.sort(key=lambda x: x["fruits"], reverse=True)
        self.player_rows = []
        y_start = screen_height - 170
        for i, player in enumerate(players[:15]):
            y = y_start - i * 45
            if y < 120:
                break
            name_color = (arcade.color.GOLD if player["fruits"] >= 10 else
                          arcade.color.LIME_GREEN if player["fruits"] >= 5 else
                          arcade.color.WHITE if player["fruits"] >= 2 else
                          arcade.color.ORANGE_RED)
            self.player_rows.append([
                arcade.Text(player["name"], 150, y, name_color, 16, anchor_x="left"),
                arcade.Text(str(player["deaths"]), 400, y, arcade.color.RED, 16, anchor_x="center"),
                arcade.Text(str(player["fruits"]), 650, y, arcade.color.GOLD, 16, anchor_x="center"),
            ])

    def go_back(self):
        self.window.show_view(self.menu_view)

    def on_draw(self):
        self.clear(arcade.color.BLACK)
        self.title.draw()
        for text in self.header_texts:
            text.draw()
        arcade.draw_line(50, screen_height - 135, screen_width - 50, screen_height - 135, arcade.color.GRAY, 2)
        # Отображаем только если есть данные
        for row in self.player_rows:
            for text in row:
                text.draw()
        left, right, bottom, top, text_obj, _ = self.back_button
        arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, arcade.color.DARK_GRAY)
        arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, arcade.color.WHITE, 2)
        text_obj.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        left, right, bottom, top, _, action = self.back_button
        if left < x < right and bottom < y < top:
            action()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            self.go_back()


class MainMenu(arcade.View):
    def __init__(self, game_view):
        super().__init__()
        self.game_view = game_view
        self.player_name = "player1"
        self.input_active = False
        self.cursor_visible = True
        self.cursor_timer = 0.0
        self.title = arcade.Text("CELESTE", screen_width / 2, screen_height - 100,
                                 arcade.color.WHITE, 64, anchor_x="center", bold=True)
        self.name_prompt = arcade.Text("Имя игрока:", screen_width / 2 - 190, screen_height / 2 + 40,
                                       arcade.color.LIGHT_GRAY, 20, anchor_x="left")
        self.name_display = arcade.Text("", screen_width / 2 - 180, screen_height / 2 - 5,
                                        arcade.color.WHITE, 32, anchor_x="left")
        self.buttons = []
        button_configs = [("Выйти", 220, arcade.close_window),
                          ("Статистика", 140, self.show_stats),
                          ("Начать игру", 60, self.start_game)]
        for text, y_offset, action in button_configs:
            y_center = screen_height / 2 - y_offset
            btn_text = arcade.Text(text, screen_width / 2, y_center,
                                   arcade.color.WHITE, 24, anchor_x="center", anchor_y="center")
            self.buttons.append([
                screen_width / 2 - 125, screen_width / 2 + 125,
                y_center - 30, y_center + 30, btn_text, action
            ])

    def show_stats(self):
        self.window.show_view(StatsView(self))

    def on_draw(self):
        self.clear(arcade.color.BLACK)
        self.title.draw()
        arcade.draw_lrbt_rectangle_outline(
            screen_width / 2 - 200, screen_width / 2 + 200,
            screen_height / 2 - 15, screen_height / 2 + 35,
            arcade.color.LIME_GREEN if self.input_active else arcade.color.GRAY, 3
        )
        self.name_prompt.draw()
        display_text = self.player_name + ("|" if self.cursor_visible and self.input_active else "")
        self.name_display.text = display_text
        self.name_display.draw()
        for btn in self.buttons:
            left, right, bottom, top, text_obj, _ = btn
            arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, arcade.color.DARK_GRAY)
            arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, arcade.color.WHITE, 2)
            text_obj.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        for btn in self.buttons:
            left, right, bottom, top, _, action = btn
            if left < x < right and bottom < y < top:
                action()
                return
        self.input_active = (screen_width / 2 - 200 < x < screen_width / 2 + 200 and
                             screen_height / 2 - 15 < y < screen_height / 2 + 35)

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            arcade.close_window()
        elif key in (arcade.key.RETURN, arcade.key.ENTER):
            self.start_game()
        elif key == arcade.key.TAB:
            self.input_active = not self.input_active
        elif key == arcade.key.S:
            self.show_stats()

    def on_text(self, text):
        if self.input_active and len(self.player_name) < 15:
            self.player_name += text

    def on_text_motion(self, motion):
        if self.input_active:
            if motion == arcade.key.MOTION_BACKSPACE:
                self.player_name = self.player_name[:-1]
            elif motion == arcade.key.MOTION_DELETE:
                self.player_name = ""

    def start_game(self):
        if not self.player_name.strip():
            self.player_name = "player1"
        self.game_view.set_player_name(self.player_name.strip())
        self.game_view.setup()
        self.window.show_view(self.game_view)

    def on_update(self, delta_time):
        self.cursor_timer += delta_time
        if self.cursor_timer >= 0.5:
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = 0.0


class MyGame(arcade.View):
    def __init__(self):
        super().__init__()
        self.player_name = "player1"
        self.stats = {"deaths": 0, "fruits_collected": 0}
        self.fruit_sound = None

    def set_player_name(self, name):
        self.player_name = name or "player1"
        self.load_stats()

    def load_stats(self):
        self.stats = {"deaths": 0, "fruits_collected": 0}
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, 'r', encoding='utf-8') as f:
                    for row in csv.DictReader(f):
                        if row.get("player_name", "").strip() == self.player_name:
                            self.stats["deaths"] = int(row.get("deaths", 0))
                            self.stats["fruits_collected"] = int(row.get("fruits_collected", 0))
                            break
            except:
                pass
        else:
            self.save_stats()

    def save_stats(self):
        all_players = []
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, 'r', encoding='utf-8') as f:
                    all_players = [r for r in csv.DictReader(f) if r.get("player_name", "").strip()]
            except:
                pass
        for row in all_players:
            if row["player_name"] == self.player_name:
                row["deaths"] = str(self.stats["deaths"])
                row["fruits_collected"] = str(self.stats["fruits_collected"])
                break
        else:
            all_players.append({
                "player_name": self.player_name,
                "deaths": str(self.stats["deaths"]),
                "fruits_collected": str(self.stats["fruits_collected"])
            })
        try:
            with open(STATS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["player_name", "deaths", "fruits_collected"])
                writer.writeheader()
                writer.writerows(all_players)
        except:
            pass

    def setup(self):
        project_root = Path(__file__).parent

        # Загрузка текстур персонажа
        walk_image = Image.open(project_root / "Run (32x32).png").convert("RGBA")
        self.walk_textures_right = [
            arcade.Texture(image=walk_image.crop((i * 32, 0, i * 32 + 32, 32)))
            for i in range(4)
        ]
        self.walk_textures_left = [
            arcade.Texture(image=ImageOps.mirror(tex.image))
            for tex in self.walk_textures_right
        ]

        climb_image = Image.open(project_root / "Wall Jump (32x32).png").convert("RGBA")
        self.climb_textures = [
            arcade.Texture(image=climb_image.crop((i * 32, 0, i * 32 + 32, 32)))
            for i in range(5)
        ]
        self.climb_textures_mirrored = [
            arcade.Texture(image=ImageOps.mirror(tex.image))
            for tex in self.climb_textures
        ]

        # Загрузка карты
        map_path = project_root / "proj1.tmx"
        if not map_path.exists():
            map_path = project_root / "maps" / "proj1.tmx"

        self.tile_map = arcade.load_tilemap(map_path, scaling=map_scaling)
        self.scene = arcade.Scene.from_tilemap(self.tile_map)
        self.walls = self.scene['Platforms']

        # Слои карты
        self.spikes = self.scene['idle'] if 'idle' in self.scene else arcade.SpriteList()
        self.fruits = self.scene['fruits'] if 'fruits' in self.scene else arcade.SpriteList()

        # Игрок
        self.spawn_x = 6 * tile_size
        self.spawn_y = 13 * tile_size + (32 * sprite_scale) / 2
        self.player = arcade.Sprite(self.walk_textures_right[0], scale=sprite_scale)
        self.player.center_x = self.spawn_x
        self.player.center_y = self.spawn_y
        self.player_spritelist = arcade.SpriteList()
        self.player_spritelist.append(self.player)

        # Анимация
        self.walk_frame = self.climb_frame = 0
        self.animation_timer = 0.0
        self.animation_speed = 0.1
        self.facing_right = True

        # Управление
        self.left = self.right = self.up = self.down = False
        self.jump_pressed = self.dash_requested = self.climb_key = False

        # Состояние
        self.jump_buffer_timer = 0.0
        self.time_since_ground = 999.0
        self.jumps_left = max_jumps
        self.dashes_left = max_dashes
        self.dash_time_left = 0.0
        self.dash_dx = self.dash_dy = 1.0
        self.on_wall = False
        self.wall_side = 0
        self.stamina = max_stamina
        self.is_dead = False
        self.respawn_timer = 0.0
        self.explosion_emitter = None

        # Камеры
        self.world_camera = Camera2D()
        self.world_camera.zoom = 4.8
        self.gui_camera = Camera2D()

        # Физика
        self.engine = arcade.PhysicsEnginePlatformer(
            player_sprite=self.player,
            gravity_constant=gravity,
            walls=self.walls
        )
        self.was_dashing = False

        # Интерфейс
        self.stamina_text = arcade.Text("стамина: 5.0 сек", 10, self.height - 30,
                                        color=arcade.color.WHITE, font_size=16)
        self.dash_text = arcade.Text("рывок: готов", 10, self.height - 55,
                                     color=arcade.color.LIME_GREEN, font_size=16, bold=True)
        self.player_name_text = arcade.Text(f"игрок: {self.player_name}", 10, self.height - 80,
                                            color=arcade.color.CYAN, font_size=16, bold=True)

        # Частицы
        self.trail_emitter = make_trail(self.player, maintain=38)
        self.camera_offset_x = self.camera_offset_y = 0.0

        # Звук
        self.fruit_sound = arcade.load_sound(":resources:sounds/coin5.wav")

    def respawn_player(self):
        self.player.center_x = self.spawn_x
        self.player.center_y = self.spawn_y
        self.player.change_x = self.player.change_y = 0
        self.left = self.right = self.up = self.down = self.jump_pressed = self.climb_key = False
        self.stamina = max_stamina
        self.dashes_left = max_dashes
        self.jumps_left = max_jumps
        self.is_dead = False
        self.respawn_timer = 0.0

    def collect_fruit(self):
        for fruit in arcade.check_for_collision_with_list(self.player, self.fruits):
            fruit.remove_from_sprite_lists()
            self.stats["fruits_collected"] += 1
            self.save_stats()
            if self.fruit_sound:
                arcade.play_sound(self.fruit_sound, 0.2)

    def on_draw(self):
        self.clear(WORLD_COLOR)  # ← ПРИМЕНЕН ЦВЕТ ФОНА
        self.world_camera.use()
        self.scene.draw()
        self.player_spritelist.draw()
        if not self.is_dead and (abs(self.player.change_x) > 0.1 or self.dash_time_left > 0 or
                                 (self.on_wall and (self.up or self.down))):
            self.trail_emitter.draw()
        if self.explosion_emitter:
            self.explosion_emitter.draw()
        self.gui_camera.use()
        self.stamina_text.draw()
        self.dash_text.draw()
        self.player_name_text.draw()

    def is_next_to_wall(self):
        grounded = self.engine.can_jump(y_distance=2)
        if grounded:
            return False, 0

        # Надёжная проверка: минимальный сдвиг (1.2 пикселя) для обнаружения стены
        original_x = self.player.center_x

        # Проверка слева
        self.player.center_x = original_x - 1.2
        hit_left = len(arcade.check_for_collision_with_list(self.player, self.walls)) > 0
        self.player.center_x = original_x

        # Проверка справа
        self.player.center_x = original_x + 1.2
        hit_right = len(arcade.check_for_collision_with_list(self.player, self.walls)) > 0
        self.player.center_x = original_x

        if hit_left:
            return True, -1
        elif hit_right:
            return True, 1
        return False, 0

    def perform_dash(self):
        if self.dashes_left <= 0 or self.is_dead:
            return

        if self.on_wall:
            dx, dy = (1.0, 0.35) if self.wall_side == -1 else (-1.0, 0.35)
            self.stamina -= wall_dash_stamina_cost
            self.stamina = max(0.0, self.stamina)
        else:
            # Умная логика направления рывка с приоритизацией чистых направлений
            horizontal = 0
            vertical = 0

            # Приоритет 1: чисто вертикальные рывки (без горизонтали)
            if self.up and not (self.left or self.right):
                horizontal, vertical = 0, 1
            elif self.down and not (self.left or self.right):
                horizontal, vertical = 0, -1
            # Приоритет 2: чисто горизонтальные рывки (без вертикали)
            elif self.right and not (self.up or self.down):
                horizontal, vertical = 1, 0
            elif self.left and not (self.up or self.down):
                horizontal, vertical = -1, 0
            # Приоритет 3: диагонали или рывок без направления
            else:
                horizontal = (1 if self.right else -1 if self.left else (1 if self.facing_right else -1))
                vertical = (1 if self.up else -1 if self.down else 0)

            # Нормализация вектора
            length = math.hypot(horizontal, vertical)
            if length > 0:
                dx = horizontal / length
                dy = vertical / length
            else:
                dx, dy = 1.0 if self.facing_right else -1.0, 0.0

        self.dash_dx, self.dash_dy = dx, dy
        self.dash_time_left = dash_duration
        self.dashes_left = 0
        if self.on_wall:
            self.on_wall = False

    def on_update(self, delta_time):
        if self.is_dead:
            if self.explosion_emitter:
                self.explosion_emitter.update()
                if self.explosion_emitter.can_reap():
                    self.explosion_emitter = None
            self.respawn_timer += delta_time
            if self.respawn_timer >= 0.8:
                self.respawn_player()
            return

        self.collect_fruit()
        if arcade.check_for_collision_with_list(self.player, self.spikes):
            self.is_dead = True
            self.stats["deaths"] += 1
            self.save_stats()
            self.left = self.right = self.up = self.down = self.jump_pressed = self.climb_key = False
            self.explosion_emitter = make_explosion(self.player.center_x, self.player.center_y)
            return

        grounded = self.engine.can_jump(y_distance=6)
        if grounded:
            self.time_since_ground = 0
            self.jumps_left = max_jumps
            self.dashes_left = max_dashes
            self.stamina = max_stamina
            self.on_wall = False
        else:
            self.time_since_ground += delta_time

        next_to_wall, side = self.is_next_to_wall()
        if self.climb_key and next_to_wall and self.stamina > 0 and not grounded:
            self.on_wall = True
            self.wall_side = side

            # Прижимаем игрока к стене для плавного лазания
            if self.wall_side == -1:  # слева
                for wall in arcade.check_for_collision_with_list(self.player, self.walls):
                    if wall.right < self.player.center_x and wall.right > self.player.left - 5:
                        self.player.left = wall.right + 0.5
                        break
            else:  # справа
                for wall in arcade.check_for_collision_with_list(self.player, self.walls):
                    if wall.left > self.player.center_x and wall.left < self.player.right + 5:
                        self.player.right = wall.left - 0.5
                        break
        else:
            if not self.climb_key or self.stamina <= 0 or not next_to_wall:
                self.on_wall = False

        if self.on_wall:
            self.player.change_y = 0
            if self.up:
                self.player.center_y += climb_speed
                self.stamina -= delta_time * 1.0
            elif self.down:
                self.player.center_y -= climb_speed
                self.stamina -= delta_time * 0.7
            else:
                self.stamina -= delta_time * 0.4

            # Коррекция позиции при коллизии сверху/снизу
            collisions = arcade.check_for_collision_with_list(self.player, self.walls)
            if collisions:
                if self.up:
                    while arcade.check_for_collision_with_list(self.player, self.walls) and self.player.center_y > 0:
                        self.player.center_y -= 0.5
                elif self.down:
                    while arcade.check_for_collision_with_list(self.player, self.walls):
                        self.player.center_y += 0.5
            self.stamina = max(0.0, self.stamina)
        elif grounded:
            self.stamina = min(max_stamina, self.stamina + delta_time * 2.5)

        if not (self.dash_time_left > 0 and self.on_wall):
            self.player.change_x = -move_speed if (self.left and not self.right) else (
                move_speed if (self.right and not self.left) else 0)
        else:
            self.player.change_x = 0

        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= delta_time
        if (self.jump_pressed or self.jump_buffer_timer > 0) and (grounded or self.time_since_ground <= coyote_time):
            self.engine.jump(jump_speed)
            self.jump_buffer_timer = 0

        if self.dash_requested:
            self.perform_dash()
            self.dash_requested = False

        if self.dash_time_left > 0:
            self.dash_time_left -= delta_time
            if self.dash_time_left < 0:
                self.dash_time_left = 0
            step = dash_speed * delta_time
            orig_x, orig_y = self.player.center_x, self.player.center_y
            self.player.center_x += self.dash_dx * step
            self.player.center_y += self.dash_dy * step
            if arcade.check_for_collision_with_list(self.player, self.walls):
                self.player.center_x = orig_x
                if arcade.check_for_collision_with_list(self.player, self.walls):
                    self.player.center_y = orig_y
                    if arcade.check_for_collision_with_list(self.player, self.walls):
                        self.dash_time_left = 0

        if self.dash_time_left <= 0 and self.was_dashing:
            self.player.change_x = self.dash_dx * dash_post_impulse
            self.player.change_y = self.dash_dy * dash_post_impulse
        self.was_dashing = self.dash_time_left > 0

        if not self.on_wall and self.dash_time_left <= 0:
            self.engine.update()

        # Анимация
        moving_horizontally = (self.left or self.right) and not self.on_wall and self.dash_time_left <= 0 and abs(
            self.player.change_x) > 0.1
        if self.on_wall and self.climb_textures:
            self.animation_timer += delta_time
            if self.animation_timer >= self.animation_speed:
                self.animation_timer = 0
                self.climb_frame = (self.climb_frame + 1) % len(self.climb_textures)
            self.player.texture = self.climb_textures_mirrored[self.climb_frame] if self.wall_side == -1 else \
                self.climb_textures[self.climb_frame]
        elif moving_horizontally:
            self.animation_timer += delta_time
            if self.animation_timer >= self.animation_speed:
                self.animation_timer = 0
                self.walk_frame = (self.walk_frame + 1) % len(self.walk_textures_right)
            self.player.texture = self.walk_textures_right[self.walk_frame] if self.right else self.walk_textures_left[
                self.walk_frame]
            self.facing_right = self.right or (not self.left and self.facing_right)
        else:
            self.walk_frame = 0
            self.player.texture = self.walk_textures_right[0] if self.facing_right else self.walk_textures_left[0]

        # Интерфейс — ИСПРАВЛЕНО: надпись зависит ТОЛЬКО от количества рывков
        self.stamina_text.text = f"стамина: {self.stamina:.1f} сек"
        if self.dashes_left > 0 and not self.is_dead:
            self.dash_text.text = "рывок: готов"
            self.dash_text.color = arcade.color.LIME_GREEN
        else:
            self.dash_text.text = "рывок: недоступен"
            self.dash_text.color = arcade.color.DARK_RED
        self.player_name_text.text = f"игрок: {self.player_name}"

        # Камера
        target_offset_x = self.player.change_x * 0.15
        target_offset_y = self.player.change_y * 0.12
        self.camera_offset_x += (target_offset_x - self.camera_offset_x) * 0.35
        self.camera_offset_y += (target_offset_y - self.camera_offset_y) * 0.35
        target_x = self.player.center_x - self.camera_offset_x
        target_y = self.player.center_y - self.camera_offset_y
        cx, cy = self.world_camera.position
        smooth_x = cx + (target_x - cx) * camera_lerp
        smooth_y = cy + (target_y - cy) * camera_lerp
        map_width = 800 * map_scaling
        map_height = 800 * map_scaling
        half_w = self.width / (2 * self.world_camera.zoom)
        half_h = self.height / (2 * self.world_camera.zoom)
        cam_x = max(half_w, min(map_width - half_w, smooth_x))
        cam_y = max(half_h, min(map_height - half_h, smooth_y))
        self.world_camera.position = (cam_x, cam_y)
        self.gui_camera.position = (self.width / 2, self.height / 2)

        # Частицы
        self.trail_emitter.center_x = self.player.center_x
        self.trail_emitter.center_y = self.player.center_y - self.player.height * 0.48
        self.trail_emitter.update()

    def on_key_press(self, key, modifiers):
        if self.is_dead:
            return
        if key in (arcade.key.LEFT, arcade.key.A):
            self.left = True
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self.right = True
        elif key in (arcade.key.UP, arcade.key.W):
            self.up = True
        elif key in (arcade.key.DOWN, arcade.key.S):
            self.down = True
        elif key == arcade.key.SPACE:
            self.jump_pressed = True
            self.jump_buffer_timer = jump_buffer
        elif key == arcade.key.X:
            self.dash_requested = True
        elif key == arcade.key.C:
            self.climb_key = True
        elif key == arcade.key.ESCAPE:
            menu_view = MainMenu(self)
            menu_view.player_name = self.player_name
            self.window.show_view(menu_view)

    def on_key_release(self, key, modifiers):
        if self.is_dead:
            return
        if key in (arcade.key.LEFT, arcade.key.A):
            self.left = False
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self.right = False
        elif key in (arcade.key.UP, arcade.key.W):
            self.up = False
        elif key in (arcade.key.DOWN, arcade.key.S):
            self.down = False
        elif key == arcade.key.SPACE:
            self.jump_pressed = False
            if self.player.change_y > 0:
                self.player.change_y *= 0.45
        elif key == arcade.key.C:
            self.climb_key = False


def main():
    window = arcade.Window(screen_width, screen_height, screen_title)
    game_view = MyGame()
    menu_view = MainMenu(game_view)
    window.show_view(menu_view)
    arcade.run()


if __name__ == "__main__":
    main()