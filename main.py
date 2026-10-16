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

FLASHLIGHT_RANGE = 150
FLASHLIGHT_THRESHOLD = 0.85

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
FOREST_FLOOR = (40, 110, 50)
DARKNESS = (0, 0, 0)


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

    def draw(self, screen):
        rect = pygame.Rect(0, 0, self.size, self.size)
        rect.center = self.position
        if self.solved:
            color = GREEN
        elif self.progress > 0:
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        else:
            color = RED
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, BLACK, rect, 2)

    def update(self, players, keys):
        if self.solved:
            return
        hacking = False
        for player in players:
            if player.state == "FREE" and keys[player.interact_key] and player.position.distance_to(self.position) < INTERACT_RADIUS:
                hacking = True
        if hacking:
            self.progress += 1
            if self.progress >= HACK_TIME:
                self.solved = True
        else:
            self.progress = 0


class Tube:
    def __init__(self, position):
        self.position = pygame.Vector2(position)
        self.radius = scale(16)
        self.trapped_player = None
        self.rescue_progress = 0

    def draw(self, screen):
        if self.rescue_progress > 0:
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        else:
            color = CYAN
        pygame.draw.circle(screen, color, self.position, self.radius, 3)

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


class Enemy:
    def __init__(self, position):
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(0, 0)
        self.angle = 0
        self.radius = ENEMY_SIZE / 2
        self.state = "PATROL"
        self.wander_timer = 0
        self.wander_interval = 0

        folder = os.path.dirname(os.path.abspath(__file__))
        happy = pygame.image.load(os.path.join(folder, "verity happy.png")).convert_alpha()
        angry = pygame.image.load(os.path.join(folder, "verity angry.png")).convert_alpha()
        self.happy_image = pygame.transform.smoothscale(happy, (ENEMY_SIZE, ENEMY_SIZE))
        self.angry_image = pygame.transform.smoothscale(angry, (ENEMY_SIZE, ENEMY_SIZE))
        self.image = self.happy_image
        self.wander()

    def forward_vector(self):
            
        forward_direction = pygame.math.Vector2(1, 0).rotate(self.angle)
        forward_vector = forward_direction * 10
        target_point = self.position + forward_vector
        return target_point
    
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
            facing = pygame.Vector2(1, 0).rotate(self.angle)
            if facing.dot(to_player.normalize()) < FOV_THRESHOLD:
                return False

        return not line_hits_wall(self.position, player.position, walls)

    def wander(self):
        if random.random() < 0.2:
            self.velocity = pygame.math.Vector2(0, 0)
        else:
            base_vector = pygame.math.Vector2(ENEMY_SPEED, 0)
            random_angle = random.uniform(0, 360)
            self.velocity = base_vector.rotate(random_angle)
        self.wander_timer = random.randint(40, 150)
        self.wander_interval = random.randint(40, 150)

    def chase(self, player):
        direction = player.position - self.position
        
        if direction.length() > 0:
            self.velocity = direction.normalize() * ENEMY_CHASE_SPEED

    def move(self, players, walls):
        visible = [p for p in players if p.state == "FREE" and self.can_see(p, walls)]
        if visible:
            target = min(visible, key=lambda p: self.position.distance_to(p.position))
            self.state = "CHASE"
            self.image = self.angry_image
            self.chase(target)
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
            self.wander() 
        else:
            self.position = next_position



    def draw(self, screen):
        rotated_image = pygame.transform.rotate(self.image, -self.angle)
        rect = rotated_image.get_rect(center=self.position)
        
        screen.blit(rotated_image, rect)
        
        # Draw the forward sight line
        pygame.draw.line(screen, (0, 0, 0), self.position, self.forward_vector(), 2)

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
game_doors = build_doors()

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
    darkness_layer.fill((0, 0, 0, 235))
    for name in ROOMS:
        pygame.draw.rect(darkness_layer, (0, 0, 0, 0), ROOMS[name])
    for rect in PATH_RECTS:
        pygame.draw.rect(darkness_layer, (0, 0, 0, 0), rect)
    for player in players:
        if player.state == "FREE":
            pygame.draw.polygon(darkness_layer, (0, 0, 0, 0), flashlight_shape(player))
    screen.blit(darkness_layer, (0, 0))


def nearest_tube(position, tubes):
    empty_tubes = [tube for tube in tubes if tube.trapped_player is None]
    if not empty_tubes:
        return None
    return min(empty_tubes, key=lambda tube: tube.position.distance_to(position))


def draw_floor(screen):
    screen.fill(FOREST_FLOOR)
    for rect in PATH_RECTS:
        pygame.draw.rect(screen, PATH_FLOOR, rect)
    for name in ROOMS:
        pygame.draw.rect(screen, INDOOR_FLOOR, ROOMS[name])


pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flee the Facility 2D")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 24)
darkness_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

# media
jumpscare_image = pygame.image.load("verity angry.png").convert_alpha()
win_image = pygame.image.load("win screen.png").convert()
win_image = pygame.transform.smoothscale(win_image, (WIDTH, HEIGHT))
scream_sound = pygame.mixer.Sound("five-nights-at-freddys-full-scream-sound_2.mp3")
menu_image = pygame.image.load("menu.png").convert()
menu_fit = min(WIDTH / menu_image.get_width(), HEIGHT / menu_image.get_height())
menu_image = pygame.transform.smoothscale(
    menu_image, (int(menu_image.get_width() * menu_fit), int(menu_image.get_height() * menu_fit))
)

JUMPSCARE_GROW_TIME = 30  # frames for verity to fill the screen
SCREAM_TIME = int(scream_sound.get_length() * 60)  # frames the scream lasts
WIN_TIME = 5 * 60  # 5 seconds


def reset_game():
    global computers, tubes, exits, player_one, player_two, players, enemy, game_state, timer
    scream_sound.stop()
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
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                return True
        screen.fill(menu_image.get_at((0, 0)))  # match the images own background color
        screen.blit(menu_image, menu_image.get_rect(center=(WIDTH / 2, HEIGHT / 2)))
        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

async def main():
    reset_game()

    running = show_menu()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                reset_game()

        if game_state == "JUMPSCARE":
            timer += 1
            draw_jumpscare(screen, timer)
            if timer == JUMPSCARE_GROW_TIME:
                scream_sound.play()
            if timer >= JUMPSCARE_GROW_TIME + SCREAM_TIME:
                reset_game()
            pygame.display.flip()
            clock.tick(60)
            continue

        if game_state == "WIN":
            timer += 1
            screen.blit(win_image, (0, 0))
            if timer >= WIN_TIME:
                reset_game()
            pygame.display.flip()
            clock.tick(60)
            continue

        keys = pygame.key.get_pressed()

        for player in players:
            player.move(player_walls())
        enemy.move(players, game_walls + exits)
        for computer in computers:
            computer.update(players, keys)
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
                    p.state = "TRAPPED"
                    p.position = pygame.Vector2(target_tube.position)
                    target_tube.trapped_player = p
                    enemy.state = "PATROL"
                    enemy.wander()
                    break

        # A player escapes once they walk past the edge of the map through an open exit
        for p in players:
            if p.state == "FREE" and (p.position.x > scale(1077) or p.position.y > scale(1157)):
                p.state = "ESCAPED"

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

        draw_darkness(screen)
        for wall in game_walls:
            wall.draw(screen)
        for door in game_doors:
            door.draw(screen)
        for exit_door in exits:
            exit_door.draw(screen)
        for player in players:
            player.draw(screen)

        solved = 0
        for computer in computers:
            if computer.solved:
                solved += 1
        computers_text = font.render(f"Computers: {solved}/{len(computers)}", True, WHITE)
        state_text = font.render(f"Enemy: {enemy.state}", True, WHITE)
        screen.blit(computers_text, (10, 240))
        screen.blit(state_text, (10, 260))

        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

    pygame.quit()
asyncio.run(main())
