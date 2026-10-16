import pygame
import random
import math
import os
import asyncio

MAP_SCALE = 0.75

WIDTH = int(1080 * MAP_SCALE)
HEIGHT = int(1160 * MAP_SCALE)

PLAYER_SPEED = 2
TURN_SPEED = 4
PLAYER_RADIUS = 9

ENEMY_SPEED = 1.5
ENEMY_CHASE_SPEED = ENEMY_SPEED * 1.5
ENEMY_SIZE = 24

FLASHLIGHT_RANGE = 220
FLASHLIGHT_THRESHOLD = 0.70
VERITY_LIGHT_RADIUS = 75
HEARTBEAT_DISTANCE = 300

DETECTION_RANGE = FLASHLIGHT_RANGE
FOV_THRESHOLD = 0.5

HACK_TIME = 10 * 60
RESCUE_TIME = 5 * 60

INTERACT_RADIUS = 25
CATCH_RADIUS = 20

WALL_WIDTH = 3

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 40, 40)
GREEN = (40, 200, 70)
GRAY = (128, 128, 128)
YELLOW = (255, 200, 0)
CYAN = (0, 200, 220)
BLUE = (60, 120, 255)
ORANGE = (255, 140, 0)
DOOR_BROWN = (139, 90, 43)
DOOR_THICKNESS = 6

INDOOR_FLOOR = (215, 215, 215)
PATH_FLOOR = (225, 205, 160)
FOREST_FLOOR = (25, 75, 35)
DARKNESS = (0, 0, 0)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))




def scale(x):
    return x * MAP_SCALE


def scaled_point(x, y):
    return pygame.Vector2(scale(x), scale(y))


def scaled_rect(x, y, w, h):
    return pygame.Rect(scale(x), scale(y), scale(w), scale(h))


ROOMS = {
    "Small Shed": scaled_rect(158, 3, 57, 54),
    "White House": scaled_rect(234, 3, 275, 227),
    "Maze": scaled_rect(529, 3, 470, 227),
    "Garage": scaled_rect(534, 328, 299, 143),
    "Log": scaled_rect(931, 348, 116, 115),
    "Brown House": scaled_rect(535, 505, 424, 221),
    "Barn": scaled_rect(536, 811, 541, 303),
    "Shed": scaled_rect(265, 850, 126, 176),
}

ROOM_COLORS = {
    "Small Shed": (120, 100, 75),

    "White House": (210, 205, 185),

    "Maze": (90, 105, 115),

    "Garage": (105, 110, 120),

    "Log": (100, 70, 45),

    "Brown House": (135, 90, 55),

    "Barn": (145, 65, 55),

    "Shed": (105, 90, 70),
}

PATH_RECTS = [
    scaled_rect(28, 257, 1027, 48),
    scaled_rect(440, 305, 52, 835),
]

DOORWAYS = [
    ("Small Shed", "bottom", 166, 206),
    ("White House", "bottom", 340, 400),
    ("Maze", "bottom", 600, 660),
    ("Garage", "left", 370, 430),
    ("Log", "bottom", 960, 1010),
    ("Brown House", "left", 580, 640),
    ("Barn", "left", 930, 990),
    ("Shed", "right", 940, 990),
]

COMPUTER_SPOTS = [
    scaled_point(463, 82),
    scaled_point(743, 138),
    scaled_point(799, 405),
    scaled_point(1016, 383),
    scaled_point(701, 541),
    scaled_point(921, 537),
    scaled_point(753, 624),
    scaled_point(946, 840),
    scaled_point(715, 1085),
    scaled_point(363, 903),
]

TUBE_SPOTS = [
    scaled_point(186, 30),
    scaled_point(258, 27),
    scaled_point(975, 27),
    scaled_point(558, 448),
    scaled_point(953, 440),
    scaled_point(559, 702),
    scaled_point(1052, 1090),
    scaled_point(289, 1002),
    scaled_point(30, 1132),
    scaled_point(1052, 785),
]

EXIT_LINES = [
    (scaled_point(411, 1157), scaled_point(526, 1157)),
    (scaled_point(1077, 235), scaled_point(1077, 340)),
]

PLAYER_ONE_START = scaled_point(466, 1050)
PLAYER_TWO_START = scaled_point(466, 1100)
ENEMY_START = scaled_point(200, 500)


class Computer:
    def __init__(self, position):
        self.position = pygame.Vector2(position)
        self.size = scale(26)
        self.progress = 0
        self.solved = False
        self.active_hackers = 0
        self.error_timer = 0
        self.error_triggered = False

    def draw(self, screen):
        x = int(self.position.x)
        y = int(self.position.y)

        # Overall monitor dimensions
        monitor_w = int(scale(40))
        monitor_h = int(scale(28))

        monitor_rect = pygame.Rect(
            x - monitor_w // 2,
            y - monitor_h // 2,
            monitor_w,
            monitor_h
        )

        # Outer monitor casing
        pygame.draw.rect(
            screen,
            (35, 35, 40),
            monitor_rect,
            border_radius=3
        )

        # Inner screen
        screen_rect = monitor_rect.inflate(-6, -6)

        if self.solved:
            screen_color = GREEN
        elif self.error_timer > 0:
            screen_color = RED
        else:
            screen_color = BLUE

        pygame.draw.rect(
            screen,
            screen_color,
            screen_rect,
            border_radius=2
        )

        # Monitor stand
        stand_top = monitor_rect.bottom

        pygame.draw.line(
            screen,
            (50, 50, 55),
            (x, stand_top),
            (x, stand_top + int(scale(8))),
            3
        )

        # Keyboard / base
        keyboard = pygame.Rect(
            x - int(scale(18)),
            stand_top + int(scale(7)),
            int(scale(36)),
            int(scale(7))
        )

        pygame.draw.rect(
            screen,
            (65, 65, 70),
            keyboard,
            border_radius=2
        )

        pygame.draw.rect(
            screen,
            BLACK,
            keyboard,
            1,
            border_radius=2
        )


    def update(self, players):
        if self.error_timer > 0:
            self.error_timer -= 1

        if self.solved:
            self.active_hackers = 0

            for player in players:
                if player.hacking_computer is self:
                    player.stop_hacking()

            return

        self.active_hackers = 0

        for player in players:
            if player.hacking_computer is not self:
                continue

            # Player stopped hacking by leaving the computer
            if (
                player.state != "FREE"
                or player.position.distance_to(self.position) >= INTERACT_RADIUS
            ):
                player.stop_hacking()
                continue

            self.active_hackers += 1

            # Run that player's skill-check timer
            player.update_skill_check()

        # Hacking automatically continues while nearby
        if self.active_hackers > 0:
            self.progress += self.active_hackers

            if self.progress >= HACK_TIME:
                self.progress = HACK_TIME
                self.solved = True


class Tube:
    def __init__(self, position):
        self.position = pygame.Vector2(position)
        self.radius = scale(16)
        self.trapped_player = None
        self.rescue_progress = 0

    def draw(self, screen):
        x = int(self.position.x)
        y = int(self.position.y)

        tube_w = int(scale(30))
        tube_h = int(scale(50))

        left = x - tube_w // 2
        top = y - tube_h // 2

        # Main tube interior
        inner_rect = pygame.Rect(
            left,
            top,
            tube_w,
            tube_h
        )

        # Interior
        pygame.draw.rect(
            screen,
            (64, 224, 208),
            inner_rect,
            border_radius=tube_w // 2
        )

        # Color changes during rescue
        if self.rescue_progress > 0:
            glow_colors = [
                (0, 255, 255),
                (255, 255, 255),
                (70, 180, 255)
            ]

            tube_color = random.choice(glow_colors)

        else:
            tube_color = CYAN

        # Glass outline
        pygame.draw.rect(
            screen,
            tube_color,
            inner_rect,
            3,
            border_radius=tube_w // 2
        )

        # Top metal cap
        top_cap = pygame.Rect(
            left - 2,
            top - 3,
            tube_w + 4,
            7
        )

        pygame.draw.rect(
            screen,
            (80, 90, 95),
            top_cap,
            border_radius=3
        )

        pygame.draw.rect(
            screen,
            BLACK,
            top_cap,
            1,
            border_radius=3
        )

        # Bottom metal cap
        bottom_cap = pygame.Rect(
            left - 2,
            top + tube_h - 4,
            tube_w + 4,
            7
        )

        pygame.draw.rect(
            screen,
            (80, 90, 95),
            bottom_cap,
            border_radius=3
        )

        pygame.draw.rect(
            screen,
            BLACK,
            bottom_cap,
            1,
            border_radius=3
        )


        # Rescue progress bar
        if self.rescue_progress > 0:
            bar_w = tube_w + 8

            bar_rect = pygame.Rect(
                x - bar_w // 2,
                bottom_cap.bottom + 4,
                bar_w,
                4
            )

            pygame.draw.rect(
                screen,
                (40, 40, 40),
                bar_rect
            )

            progress_ratio = min(
                self.rescue_progress / RESCUE_TIME,
                1
            )

            fill_rect = pygame.Rect(
                bar_rect.x,
                bar_rect.y,
                int(bar_rect.width * progress_ratio),
                bar_rect.height
            )

            pygame.draw.rect(
                screen,
                CYAN,
                fill_rect
            )

    def update(self, players, keys):
        if self.trapped_player is None:
            self.rescue_progress = 0
            return
        rescuing = False
        for player in players:
            if player is not self.trapped_player and player.state == "FREE" and keys[player.interact_key] and player.position.distance_to(self.position) < INTERACT_RADIUS:
                rescuing = True
        if rescuing:
            self.rescue_progress += 1
            if self.rescue_progress >= RESCUE_TIME:
                self.trapped_player.state = "FREE"
                self.trapped_player = None
                self.rescue_progress = 0
        else:
            self.rescue_progress = 0


class Exit:
    def __init__(self, start, end):
        self.start = pygame.Vector2(start)
        self.end = pygame.Vector2(end)
        self.is_open = False

    def intersects(self, line_start, line_end):
        return Wall.intersects(self, line_start, line_end)

    def draw(self, screen):
        if self.is_open:
            color = YELLOW
        else:
            color = GRAY
        pygame.draw.line(screen, color, self.start, self.end, 6)


class Player:
    def __init__(self, position, color, forward_key, back_key, left_key, right_key, interact_key):
        self.position = pygame.Vector2(position)
        self.color = color
        self.angle = -90
        self.radius = PLAYER_RADIUS
        self.state = "FREE"

        self.forward_key = forward_key
        self.back_key = back_key
        self.left_key = left_key
        self.right_key = right_key
        self.interact_key = interact_key

        # Hacking state
        self.hacking_computer = None

        # Skill check state
        self.skill_check_active = False
        self.skill_timer = 0
        self.skill_marker = 0.0
        self.skill_speed = 0.018

        self.skill_zone_start = 0.0
        self.skill_zone_end = 0.0

    def move(self, walls):
        if self.state == "TRAPPED":
            return
            
        keys = pygame.key.get_pressed()
        velocity = pygame.Vector2(0, 0)

        if keys[self.left_key]:
            velocity.x = -PLAYER_SPEED
        if keys[self.right_key]:
            velocity.x = PLAYER_SPEED
        if keys[self.forward_key]:
            velocity.y = -PLAYER_SPEED
        if keys[self.back_key]:
            velocity.y = PLAYER_SPEED

        if velocity.length() > 0:
            velocity = velocity.normalize() * PLAYER_SPEED
            self.angle = pygame.Vector2(1, 0).angle_to(velocity)

        next_pos_x = pygame.Vector2(self.position.x + velocity.x, self.position.y)
        hit_wall_x = False
        for wall in walls:
            if wall.intersects(self.position, next_pos_x):
                hit_wall_x = True
                break
        if not hit_wall_x:
            self.position.x = next_pos_x.x

        next_pos_y = pygame.Vector2(self.position.x, self.position.y + velocity.y)
        hit_wall_y = False
        for wall in walls:
            if wall.intersects(self.position, next_pos_y):
                hit_wall_y = True
                break
        if not hit_wall_y:
            self.position.y = next_pos_y.y

    def draw(self, screen):
        if self.state == "ESCAPED":
            return
        front = self.position + pygame.Vector2(14, 0).rotate(self.angle)
        left = self.position + pygame.Vector2(-9, -8).rotate(self.angle)
        right = self.position + pygame.Vector2(-9, 8).rotate(self.angle)
        pygame.draw.polygon(screen, self.color, [front, left, right])
        pygame.draw.polygon(screen, BLACK, [front, left, right], 1)

    def start_hacking(self, computer):
        self.hacking_computer = computer
        self.schedule_skill_check()


    def stop_hacking(self):
        self.hacking_computer = None
        self.skill_check_active = False
        self.skill_marker = 0.0
        self.skill_timer = 0


    def schedule_skill_check(self):
        # Wait 2–4 seconds before next skill check
        self.skill_timer = random.randint(120, 240)

        self.skill_check_active = False
        self.skill_marker = 0.0

        # Random success zone
        self.skill_zone_start = random.uniform(0.55, 0.75)
        self.skill_zone_end = self.skill_zone_start + 0.15


    def update_skill_check(self):
        if self.hacking_computer is None:
            return

        if not self.skill_check_active:
            self.skill_timer -= 1

            if self.skill_timer <= 0:
                self.skill_check_active = True
                self.skill_marker = 0.0
                skill_check_sound.play()

        else:
            self.skill_marker += self.skill_speed

            # Marker reached the end without player pressing
            if self.skill_marker > 1.0:
                self.fail_skill_check()


    def resolve_skill_check(self):
        if not self.skill_check_active:
            return

        if self.skill_zone_start <= self.skill_marker <= self.skill_zone_end:
            # Success
            self.schedule_skill_check()

        else:
            # Player pressed too early / too late
            self.fail_skill_check()


    def fail_skill_check(self):
        computer = self.hacking_computer

        if computer is not None:
            # Lose about one second of hacking progress
            computer.progress = max(0, computer.progress - 60)

            # Computer flashes red
            computer.error_timer = 45
            computer.error_triggered = True
            error_sound.play()

        self.schedule_skill_check()


class Enemy:
    def __init__(self, position):
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(0, 0)
        self.angle = 0
        self.radius = ENEMY_SIZE / 2
        self.state = "PATROL"
        self.wander_timer = 0
        self.wander_interval = 0
        self.investigate_target = None
        self.investigate_timer = 0



        happy = pygame.image.load(
            os.path.join(BASE_DIR, "verity happy.png")
        ).convert_alpha()

        angry = pygame.image.load(
            os.path.join(BASE_DIR, "verity angry.png")
        ).convert_alpha()

        self.happy_image = pygame.transform.smoothscale(happy, (ENEMY_SIZE, ENEMY_SIZE))
        self.angry_image = pygame.transform.smoothscale(angry, (ENEMY_SIZE, ENEMY_SIZE))
        self.image = self.happy_image
        self.wander()

    def forward_vector(self):
        return pygame.Vector2(1, 0).rotate(self.angle)
    
    def can_see(self, player, walls):
        to_player = player.position - self.position
        distance = to_player.length()

        sight_range = DETECTION_RANGE
        if is_dark(player.position):
            sight_range = DETECTION_RANGE / 2
        if distance > sight_range:
            return False

        # Dot product: 1 = straight ahead, 0 = off to the side, -1 = behind
        if distance > 0:
            facing = self.forward_vector()
            if facing.dot(to_player.normalize()) < FOV_THRESHOLD:
                return False

        return not line_hits_wall(self.position, player.position, walls)

    def wander(self):
        if random.random() < 0.2:
            self.velocity = pygame.Vector2(0, 0)
        else:
            base_vector = pygame.Vector2(ENEMY_SPEED, 0)
            random_angle = random.uniform(0, 360)
            self.velocity = base_vector.rotate(random_angle)

        self.wander_timer = 0
        self.wander_interval = random.randint(40, 150)

    def chase(self, player):
        direction = player.position - self.position
        
        if direction.length() > 0:
            self.velocity = direction.normalize() * ENEMY_CHASE_SPEED

    def move(self, players, walls):
        visible = [
            p for p in players
            if p.state == "FREE" and self.can_see(p, walls)
        ]

        # Highest priority: player is actually visible
        if visible:
            target = min(
                visible,
                key=lambda p: self.position.distance_to(p.position)
            )

            self.state = "CHASE"
            self.image = self.angry_image
            self.chase(target)

        # Second priority: investigate a failed computer
        elif self.investigate_target is not None:
            self.state = "INVESTIGATE"
            self.image = self.angry_image

            direction = self.investigate_target - self.position
            self.investigate_timer -= 1

            # Give up if Verity reaches the computer
            # OR has investigated for 3 seconds
            if direction.length() <= 10 or self.investigate_timer <= 0:
                self.investigate_target = None
                self.investigate_timer = 0
                self.wander()

            else:
                self.velocity = direction.normalize() * ENEMY_SPEED

        # Otherwise wander normally
        else:
            self.state = "PATROL"
            self.image = self.happy_image

            self.wander_timer += 1

            if self.wander_timer >= self.wander_interval:
                self.wander()

        if self.velocity.length() > 0:
            self.angle = pygame.math.Vector2(1, 0).angle_to(self.velocity)

        next_position = self.position + self.velocity
        
        collision = False
        for wall in walls:
            if wall.intersects(self.position, next_position):
                collision = True
                break
                
        if collision:
            # Don't get permanently stuck trying to investigate
            if self.state == "INVESTIGATE":
                self.investigate_target = None
                self.investigate_timer = 0

            self.wander()

        else:
            self.position = next_position

    def investigate(self, position):
        self.investigate_target = pygame.Vector2(position)
        self.investigate_timer = 3 * 60



    def draw(self, screen):
        rotated_image = pygame.transform.rotate(self.image, -self.angle)
        rect = rotated_image.get_rect(center=self.position)

        screen.blit(rotated_image, rect)

        forward = self.forward_vector()
        line_end = self.position + forward * 10

        pygame.draw.line(
            screen,
            BLACK,
            self.position,
            line_end,
            2
        )

class Wall:
    def __init__(self, start_pos, end_pos, color=(100, 100, 100), thickness=3):
        self.start = pygame.Vector2(start_pos)
        self.end = pygame.Vector2(end_pos)
        self.color = color
        self.thickness = thickness

    def intersects(self, line_start, line_end):
        """Returns True if the line segment (line_start -> line_end) crosses this wall."""
        def ccw(A, B, C):
            return (C.y - A.y) * (B.x - A.x) > (B.y - A.y) * (C.x - A.x)
        
        A, B = self.start, self.end
        C, D = pygame.Vector2(line_start), pygame.Vector2(line_end)
        
        return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

    def draw(self, screen):
        # Draw the wall as a line on the screen
        pygame.draw.line(screen, self.color, self.start, self.end, self.thickness)

def build_walls():
    walls = []

    top_left = scaled_point(3, 3)
    top_right = scaled_point(1077, 3)
    bottom_left = scaled_point(3, 1157)
    bottom_right = scaled_point(1077, 1157)
    walls.append(Wall(top_left, top_right))
    walls.append(Wall(top_left, bottom_left))
    walls.append(Wall(bottom_left, EXIT_LINES[0][0]))
    walls.append(Wall(EXIT_LINES[0][1], bottom_right))
    walls.append(Wall(top_right, EXIT_LINES[1][0]))
    walls.append(Wall(EXIT_LINES[1][1], bottom_right))

    for name in ROOMS:
        rect = ROOMS[name]
        sides = {
            "top": (pygame.Vector2(rect.topleft), pygame.Vector2(rect.topright)),
            "bottom": (pygame.Vector2(rect.bottomleft), pygame.Vector2(rect.bottomright)),
            "left": (pygame.Vector2(rect.topleft), pygame.Vector2(rect.bottomleft)),
            "right": (pygame.Vector2(rect.topright), pygame.Vector2(rect.bottomright)),
        }
        for side in sides:
            start, end = sides[side]
            gap = None
            for door in DOORWAYS:
                if door[0] == name and door[1] == side:
                    gap = door
            if gap is None:
                walls.append(Wall(start, end))
            elif side == "top" or side == "bottom":
                walls.append(Wall(start, (scale(gap[2]), start.y)))
                walls.append(Wall((scale(gap[3]), start.y), end))
            else:
                walls.append(Wall(start, (start.x, scale(gap[2]))))
                walls.append(Wall((start.x, scale(gap[3])), end))

    return walls

def build_doors():
    doors = []
    for name, side, gap_start, gap_end in DOORWAYS:
        rect = ROOMS[name]
        if side == "top":
            start, end = (scale(gap_start), rect.top), (scale(gap_end), rect.top)
        elif side == "bottom":
            start, end = (scale(gap_start), rect.bottom), (scale(gap_end), rect.bottom)
        elif side == "left":
            start, end = (rect.left, scale(gap_start)), (rect.left, scale(gap_end))
        else:
            start, end = (rect.right, scale(gap_start)), (rect.right, scale(gap_end))
        doors.append(Wall(start, end, DOOR_BROWN, DOOR_THICKNESS))
    return doors

game_walls = build_walls()
door_markers = build_doors()

def is_dark(position):
    for name in ROOMS:
        if ROOMS[name].collidepoint(position):
            return False
    for rect in PATH_RECTS:
        if rect.collidepoint(position):
            return False
    return True


def line_hits_wall(a, b, walls):
    for wall in walls:
        if wall.intersects(a, b):
            return True
    return False


def beam_end(start, direction):
    end = start + direction * FLASHLIGHT_RANGE
    walls_in_the_way = [wall for wall in game_walls if wall.intersects(start, end)]
    for distance in range(0, FLASHLIGHT_RANGE, 5):
        if line_hits_wall(start, start + direction * (distance + 5), walls_in_the_way):
            return start + direction * distance
    return end


def flashlight_shape(player):
    half_width = math.degrees(math.acos(FLASHLIGHT_THRESHOLD))
    points = [player.position]
    for i in range(21):
        angle = player.angle - half_width + (half_width * 2) * i / 20
        direction = pygame.Vector2(1, 0).rotate(angle)
        points.append(beam_end(player.position, direction))
    return points

def draw_darkness(screen):
    darkness_layer.fill((0, 0, 0, 255))

    for player in players:
        if player.state != "FREE":
            continue

        # DIM LIGHT INSIDE BUILDINGS
        for name, room in ROOMS.items():
            if room.collidepoint(player.position):
                pygame.draw.rect(
                    darkness_layer,
                    (0, 0, 0, 115),
                    room
                )

        # SMALL AMBIENT PLAYER LIGHT
        pygame.draw.circle(
            darkness_layer,
            (0, 0, 0, 80),
            (int(player.position.x), int(player.position.y)),
            45
        )

        # FULL FLASHLIGHT VISIBILITY
        pygame.draw.polygon(
            darkness_layer,
            (0, 0, 0, 0),
            flashlight_shape(player)
        )

    # VERITY RED LIGHT
    center = (
        int(enemy.position.x),
        int(enemy.position.y)
    )

    pygame.draw.circle(
        darkness_layer,
        (255, 0, 30, 110),
        center,
        VERITY_LIGHT_RADIUS
    )

    screen.blit(darkness_layer, (0, 0))




def nearest_tube(position, tubes):
    empty_tubes = [tube for tube in tubes if tube.trapped_player is None]
    if not empty_tubes:
        return None
    return min(empty_tubes, key=lambda tube: tube.position.distance_to(position))


def draw_floor(screen):
    # Forest
    screen.fill(FOREST_FLOOR)

    # Paths
    for rect in PATH_RECTS:
        pygame.draw.rect(
            screen,
            PATH_FLOOR,
            rect
        )

    # Individual room colors
    for name, rect in ROOMS.items():
        pygame.draw.rect(
            screen,
            ROOM_COLORS[name],
            rect
        )


pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flee the Facility 2D")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 24)
darkness_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

# media
jumpscare_image = pygame.image.load(
    os.path.join(BASE_DIR, "verity angry.png")
).convert_alpha()

win_image = pygame.image.load(
    os.path.join(BASE_DIR, "win screen.png")
).convert()

win_image = pygame.transform.smoothscale(
    win_image,
    (WIDTH, HEIGHT)
)

scream_sound = pygame.mixer.Sound(
    os.path.join(
        BASE_DIR,
        "five-nights-at-freddys-full-scream-sound_2.ogg"
    )
)

hacking_sound = pygame.mixer.Sound(
    os.path.join(BASE_DIR, "hacking.ogg")
)

skill_check_sound = pygame.mixer.Sound(
    os.path.join(BASE_DIR, "skill_check.ogg")
)

error_sound = pygame.mixer.Sound(
    os.path.join(BASE_DIR, "error.ogg")
)

heartbeat_sound = pygame.mixer.Sound(
    os.path.join(BASE_DIR, "heartbeat.ogg")
)

escape_sound = pygame.mixer.Sound(
    os.path.join(BASE_DIR, "escape.ogg")
)

pygame.mixer.music.load(
    os.path.join(BASE_DIR, "background.ogg")
)

pygame.mixer.music.set_volume(0.30)

hacking_channel = pygame.mixer.Channel(1)
heartbeat_channel = pygame.mixer.Channel(2)

hacking_channel.set_volume(0.4)
heartbeat_channel.set_volume(0.0)

menu_image = pygame.image.load(
    os.path.join(BASE_DIR, "menu.png")
).convert()

JUMPSCARE_GROW_TIME = 30  # frames for verity to fill the screen
SCREAM_TIME = int(scream_sound.get_length() * 60)  # frames the scream lasts
WIN_TIME = 5 * 60  # 5 seconds



def reset_game():
    global computers, tubes, exits, player_one, player_two, players, enemy, game_state, timer
    scream_sound.stop()
    pygame.mixer.music.unpause()
    computers = [Computer(spot) for spot in COMPUTER_SPOTS]
    tubes = [Tube(spot) for spot in TUBE_SPOTS]
    exits = [Exit(line[0], line[1]) for line in EXIT_LINES]
    player_one = Player(PLAYER_ONE_START, BLUE, pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d, pygame.K_e)
    player_two = Player(PLAYER_TWO_START, ORANGE, pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_p)
    players = [player_one, player_two]
    enemy = Enemy(ENEMY_START)
    game_state = "PLAYING"
    timer = 0


def draw_jumpscare(screen, frame):
    screen.fill(BLACK)
    # Grow from tiny to bigger than the screen over JUMPSCARE_GROW_TIME frames
    size = int(min(frame / JUMPSCARE_GROW_TIME, 1) * HEIGHT * 1.2) + 1
    image = pygame.transform.scale(jumpscare_image, (size, size))
    rect = image.get_rect(center=(WIDTH / 2, HEIGHT / 2))
    screen.blit(image, rect)


def update_exits():
    all_solved = all(computer.solved for computer in computers)
    someone_trapped = any(p.state == "TRAPPED" for p in players)
    for exit_door in exits:
        exit_door.is_open = all_solved and not someone_trapped


def player_walls():
    return game_walls + [exit_door for exit_door in exits if not exit_door.is_open]


async def show_menu():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                return True
        screen.fill(menu_image.get_at((0, 0)))  # match the images own background color
        screen.blit(menu_image, menu_image.get_rect(center=(WIDTH / 2, HEIGHT / 2)))
        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

def handle_hack_press(player, computers):
    if player.state != "FREE":
        return

    # Already hacking something
    if player.hacking_computer is not None:

        # E/P is now the skill-check button
        if player.skill_check_active:
            player.resolve_skill_check()

        return

    # Not currently hacking:
    # find unfinished computers within interaction range
    nearby_computers = [
        computer
        for computer in computers
        if (
            not computer.solved
            and player.position.distance_to(computer.position) < INTERACT_RADIUS
        )
    ]

    if nearby_computers:
        closest = min(
            nearby_computers,
            key=lambda computer:
                player.position.distance_to(computer.position)
        )

        player.start_hacking(closest)

def draw_hacking_ui(screen, players, font):
    row = 0

    for player_number, player in enumerate(players, start=1):
        computer = player.hacking_computer

        if computer is None:
            continue

        # Extra safety
        if player.position.distance_to(computer.position) >= INTERACT_RADIUS:
            continue

        bar_width = 360
        bar_height = 18

        x = (WIDTH - bar_width) // 2
        y = HEIGHT - 35 - row * 70

        progress_ratio = computer.progress / HACK_TIME

        # HACKING PROGRESS BAR

        progress_background = pygame.Rect(
            x,
            y,
            bar_width,
            bar_height
        )

        pygame.draw.rect(
            screen,
            (30, 30, 35),
            progress_background,
            border_radius=4
        )

        progress_fill = pygame.Rect(
            x,
            y,
            int(bar_width * progress_ratio),
            bar_height
        )

        pygame.draw.rect(
            screen,
            BLUE,
            progress_fill,
            border_radius=4
        )

        pygame.draw.rect(
            screen,
            WHITE,
            progress_background,
            2,
            border_radius=4
        )

        percent = int(progress_ratio * 100)

        hacking_text = font.render(
            f"P{player_number} HACKING: {percent}%",
            True,
            player.color
        )

        screen.blit(
            hacking_text,
            hacking_text.get_rect(
                center=(WIDTH // 2, y - 12)
            )
        )

        # SKILL CHECK

        if player.skill_check_active:
            skill_y = y - 40

            skill_background = pygame.Rect(
                x,
                skill_y,
                bar_width,
                12
            )

            pygame.draw.rect(
                screen,
                (40, 40, 40),
                skill_background,
                border_radius=3
            )

            # Success zone
            zone_x = x + int(
                bar_width * player.skill_zone_start
            )

            zone_width = int(
                bar_width
                * (
                    player.skill_zone_end
                    - player.skill_zone_start
                )
            )

            success_zone = pygame.Rect(
                zone_x,
                skill_y,
                zone_width,
                12
            )

            pygame.draw.rect(
                screen,
                GREEN,
                success_zone
            )

            # Moving marker
            marker_x = x + int(
                bar_width * player.skill_marker
            )

            pygame.draw.line(
                screen,
                WHITE,
                (marker_x, skill_y - 4),
                (marker_x, skill_y + 16),
                3
            )

            key_name = pygame.key.name(
                player.interact_key
            ).upper()

            prompt = font.render(
                f"PRESS {key_name}",
                True,
                WHITE
            )

            screen.blit(
                prompt,
                prompt.get_rect(
                    center=(WIDTH // 2, skill_y - 12)
                )
            )

        # ERROR MESSAGE

        elif computer.error_timer > 0:
            error_text = font.render(
                "ERROR!",
                True,
                RED
            )

            screen.blit(
                error_text,
                error_text.get_rect(
                    center=(WIDTH // 2, y - 35)
                )
            )

        row += 1

def update_hacking_sound():
    someone_hacking = any(
        player.hacking_computer is not None
        and player.state == "FREE"
        for player in players
    )

    if someone_hacking:
        if not hacking_channel.get_busy():
            hacking_channel.play(
                hacking_sound,
                loops=-1
            )

    else:
        hacking_channel.stop()

def update_heartbeat():
    free_players = [
        player
        for player in players
        if player.state == "FREE"
    ]

    if not free_players:
        heartbeat_channel.set_volume(0.0)
        return

    closest_distance = min(
        player.position.distance_to(enemy.position)
        for player in free_players
    )

    # 0 when far away, 1 when directly beside Verity
    volume = 1.0 - (
        closest_distance / HEARTBEAT_DISTANCE
    )

    volume = max(0.0, min(volume, 1.0))

    heartbeat_channel.set_volume(volume)

    if not heartbeat_channel.get_busy():
        heartbeat_channel.play(
            heartbeat_sound,
            loops=-1
        )

async def main():
    global game_state, timer
    reset_game()

    running = await show_menu()
    pygame.mixer.music.play(-1)

    while running:
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:

                if event.key == pygame.K_r:
                    reset_game()

                elif event.key == player_one.interact_key:
                    handle_hack_press(player_one, computers)

                elif event.key == player_two.interact_key:
                    handle_hack_press(player_two, computers)

        if game_state == "JUMPSCARE":
            hacking_channel.stop()
            heartbeat_channel.set_volume(0.0)
            pygame.mixer.music.pause()
            timer += 1
            draw_jumpscare(screen, timer)
            if timer == JUMPSCARE_GROW_TIME:
                scream_sound.play()
            if timer >= JUMPSCARE_GROW_TIME + SCREAM_TIME:
                reset_game()
            pygame.display.flip()
            clock.tick(60)
            await asyncio.sleep(0)
            continue

        if game_state == "WIN":
            hacking_channel.stop()
            heartbeat_channel.set_volume(0.0)
            pygame.mixer.music.pause()
            timer += 1
            screen.blit(win_image, (0, 0))
            if timer >= WIN_TIME:
                reset_game()
            pygame.display.flip()
            clock.tick(60)
            await asyncio.sleep(0)
            continue

        keys = pygame.key.get_pressed()

        for player in players:
            player.move(player_walls())
        for computer in computers:
            computer.update(players)
            
        update_hacking_sound()
        for computer in computers:
            if computer.error_triggered:
                enemy.investigate(computer.position)
                computer.error_triggered = False

        enemy.move(players, game_walls + exits)
        update_heartbeat()

        update_exits()
        for tube in tubes:
            tube.update(players, keys)

        for p in players:
            if p.state != "FREE":
                continue
            distance = enemy.position.distance_to(p.position)
            # If enemy collides with a player
            if distance < (enemy.radius + p.radius):
                target_tube = nearest_tube(p.position, tubes)
                if target_tube:
                    # Lock the player state and teleport them inside
                    p.stop_hacking()
                    p.state = "TRAPPED"
                    p.position = pygame.Vector2(target_tube.position)
                    target_tube.trapped_player = p
                    enemy.investigate_target = None
                    enemy.investigate_timer = 0
                    enemy.state = "PATROL"
                    enemy.wander()
                    break

        # A player escapes once they walk past the edge of the map through an open exit
        for p in players:
            if p.state == "FREE" and (p.position.x > scale(1077) or p.position.y > scale(1157)):
                p.stop_hacking()
                p.state = "ESCAPED"
                escape_sound.play()

        if all(p.state == "TRAPPED" for p in players):
            game_state = "JUMPSCARE"
            timer = 0
        if all(p.state == "ESCAPED" for p in players):
            game_state = "WIN"
            timer = 0

        draw_floor(screen)

        for computer in computers:
            computer.draw(screen)

        for tube in tubes:
            tube.draw(screen)

        enemy.draw(screen)

        for wall in game_walls:
            wall.draw(screen)

        for door in door_markers:
            door.draw(screen)

        for exit_door in exits:
            exit_door.draw(screen)

        draw_darkness(screen)
        for player in players:
            player.draw(screen)

        solved = 0
        for computer in computers:
            if computer.solved:
                solved += 1
        computers_text = font.render(f"Computers: {solved}/{len(computers)}", True, WHITE)
        state_text = font.render(f"Verity: {enemy.state}", True, WHITE)
        screen.blit(computers_text, (10, 240))
        screen.blit(state_text, (10, 260))
        draw_hacking_ui(screen, players, font)
        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

    pygame.quit()
asyncio.run(main())
