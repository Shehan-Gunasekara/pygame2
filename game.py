import pygame
from pygame import mixer
import csv

import requests
import constants
from character import Character
from weapon import Weapon
from items import Item
from world import World
from button import Button
import os
from db_helper import DB_Helper

import numpy as np
import tensorflow as tf
import warnings
# tf.get_logger().setLevel('ERROR')
# warnings.filterwarnings('ignore')

db_helper = DB_Helper()

mixer.init()
pygame.init()

screen = pygame.display.set_mode((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
pygame.display.set_caption("Dungeon Crawler")

#define model
generator = tf.keras.models.load_model(os.path.join("models", "generator.h5"))

#create clock for maintaining frame rate
clock = pygame.time.Clock()

#define game variables
level = 1
start_game = False
pause_game = False
start_intro = False
screen_scroll = [0, 0]
difficulty_level = None

#define player movement variables
moving_left = False
moving_right = False
moving_up = False
moving_down = False

#define font
font = pygame.font.Font("assets/fonts/AtariClassic.ttf", 20)

#helper function to scale image
def scale_img(image, scale):
  w = image.get_width()
  h = image.get_height()
  return pygame.transform.scale(image, (w * scale, h * scale))

#load music and sounds
pygame.mixer.music.load("assets/audio/music.wav")
pygame.mixer.music.set_volume(0.3)
pygame.mixer.music.play(-1, 0.0, 5000)
shot_fx = pygame.mixer.Sound("assets/audio/arrow_shot.mp3")
shot_fx.set_volume(0.5)
hit_fx = pygame.mixer.Sound("assets/audio/arrow_hit.wav")
hit_fx.set_volume(0.5)
coin_fx = pygame.mixer.Sound("assets/audio/coin.wav")
coin_fx.set_volume(0.5)
heal_fx = pygame.mixer.Sound("assets/audio/heal.wav")
heal_fx.set_volume(0.5)

'''
Feedback and DB helper blocks start here.

'''

LEVEL_PREDICTION_API = "http://127.0.0.1:5111"

has_trigger_start_event = False

def start_new_game():
    global difficulty_level
    db_helper.init_game_session()
    user_data = db_helper.get_user_data()
    requests.get(f"{LEVEL_PREDICTION_API}/start_emotion_detection")
    if user_data:
      difficulty_level = user_data['difficulty']

def end_game():
    requests.get(f"{LEVEL_PREDICTION_API}/stop_emotion_detection")
    db_helper.end_game_session()

def earn_achievement(count):
    db_helper.update_achievements(count)  

def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + word + " "
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word + " "

    lines.append(current_line)  
    return lines


def get_feedback():
    print("coin_images length", len(coin_images))
    global difficulty_level
    feedback_text = ""
    collecting_feedback = True
    response_message = ""

    db_helper.end_game_session()
    # Stop video recording before feedback starts
    requests.get(f"{LEVEL_PREDICTION_API}/stop_emotion_detection")


    input_box_width = 400
    max_input_box_height = 150 
    min_input_box_height = 50 
    response_box_width = 400
    response_box_height = 50

    show_response = False

    while collecting_feedback:
        screen.fill((30, 30, 30)) 

        # Title (Centered)
        title_text = "How was the previous level?"
        title_width, _ = font.size(title_text)
        draw_text(title_text, font, constants.WHITE, (constants.SCREEN_WIDTH - title_width) // 2, 150)

        # Wrap text inside input box
        wrapped_lines = wrap_text(feedback_text, font, input_box_width - 20)
        input_box_height = min(min_input_box_height + len(wrapped_lines) * 20, max_input_box_height)

        input_box = pygame.Rect(constants.SCREEN_WIDTH // 2 - input_box_width // 2, 200, input_box_width, input_box_height)
        pygame.draw.rect(screen, (200, 200, 200), input_box, border_radius=10)

        # Draw wrapped text inside input box
        for i, line in enumerate(wrapped_lines):
            draw_text(line, font, constants.BLACK, input_box.x + 10, input_box.y + 10 + i * 20)

            

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and feedback_text.strip():  # Submit only if text exists
                    print("User Feedback:", feedback_text)

                    user_data = db_helper.get_user_data()
                    game_data = db_helper.get_game_data()
                    print(game_data)

                    current_level = level

                    request_data = {
                        "age": user_data["age"],
                        "gender": user_data["gender"],
                        "location": user_data["location"],
                        "difficulty": user_data["difficulty"],
                        "play_time": game_data.get("total_minutes", 0),
                        "sessions": max(game_data.get("total_sessions", 1), 1),  # Avoid division by zero
                        "achivements": game_data.get("total_achievements", 0),
                        "feedback": feedback_text
                    }
                    
                    print("game data----",game_data)

                    response = requests.post(f"{LEVEL_PREDICTION_API}/get-next-level-difficulty", json=request_data)
                    emotion_response(response.text)

                    collecting_feedback = False


                elif event.key == pygame.K_BACKSPACE:  # Remove last character
                    feedback_text = feedback_text[:-1]
                elif len(feedback_text) < 200:  # Limit text length
                    feedback_text += event.unicode  # Add typed character



def emotion_response(response):
  showing_response = True

  # show tasks based on difficulty levels
  tasks = {
        "easy": "Defeat 5 enemies!",
        "medium": "Collect 5 power-ups!",
        "hard": "Survive for 3 minutes without losing health!",
        "expert": "Complete the level without taking damage!"
    }

  difficulty_level = response.lower()  # Ensure lowercase comparison
  assigned_task = tasks.get(difficulty_level, "Proceed to the next challenge!")

  while showing_response:
      screen.fill((30, 30, 30))  

      title_text = f"We've changed"
      title_width, _ = font.size(title_text)
      draw_text(title_text, font, constants.WHITE, (constants.SCREEN_WIDTH - title_width) // 2, 150)

      title_text_line_2 = f"the dificulty level to:"
      title_width_line_2, l_ = font.size(title_text_line_2)
      draw_text(title_text_line_2, font, constants.WHITE, (constants.SCREEN_WIDTH - title_width_line_2) // 2, 200)

      title_text_line_3 = f"{response.upper()}"
      title_width_line_3, l_ = font.size(title_text_line_3)
      draw_text(title_text_line_3, font, constants.WHITE, (constants.SCREEN_WIDTH - title_width_line_3) // 2, 250)


      # Display assigned task
      task_text = f"Your next task: {assigned_task}"
      task_width, _ = font.size(task_text)
      draw_text(task_text, font, constants.WHITE, (constants.SCREEN_WIDTH - task_width) // 2, 300)

      pygame.display.flip()

      for event in pygame.event.get():
          if event.type == pygame.QUIT:
              pygame.quit()
              exit()
          elif event.type == pygame.KEYDOWN:
              if event.key == pygame.K_RETURN: 
                showing_response = False    
  # Start video recording after showing next level task
  requests.get(f"{LEVEL_PREDICTION_API}/start_emotion_detection")          



'''
Feedback and DB helper blocks end here.

'''    



#load button images
start_img = scale_img(pygame.image.load("assets/images/buttons/button_start.png").convert_alpha(), constants.BUTTON_SCALE)
exit_img = scale_img(pygame.image.load("assets/images/buttons/button_exit.png").convert_alpha(), constants.BUTTON_SCALE)
restart_img = scale_img(pygame.image.load("assets/images/buttons/button_restart.png").convert_alpha(), constants.BUTTON_SCALE)
resume_img = scale_img(pygame.image.load("assets/images/buttons/button_resume.png").convert_alpha(), constants.BUTTON_SCALE)

#load heart images
heart_empty = scale_img(pygame.image.load("assets/images/items/heart_empty.png").convert_alpha(), constants.ITEM_SCALE)
heart_half = scale_img(pygame.image.load("assets/images/items/heart_half.png").convert_alpha(), constants.ITEM_SCALE)
heart_full = scale_img(pygame.image.load("assets/images/items/heart_full.png").convert_alpha(), constants.ITEM_SCALE)

#load coin images
coin_images = []
for x in range(4):
  img = scale_img(pygame.image.load(f"assets/images/items/coin_f{x}.png").convert_alpha(), constants.ITEM_SCALE)
  coin_images.append(img)

#load potion image
red_potion = scale_img(pygame.image.load("assets/images/items/potion_red.png").convert_alpha(), constants.POTION_SCALE)

item_images = []
item_images.append(coin_images)
item_images.append(red_potion)

#load weapon images
bow_image = scale_img(pygame.image.load("assets/images/weapons/bow.png").convert_alpha(), constants.WEAPON_SCALE)
arrow_image = scale_img(pygame.image.load("assets/images/weapons/arrow.png").convert_alpha(), constants.WEAPON_SCALE)
fireball_image = scale_img(pygame.image.load("assets/images/weapons/fireball.png").convert_alpha(), constants.FIREBALL_SCALE)

#load tilemap images
tile_list = []
for x in range(constants.TILE_TYPES):
  tile_image = pygame.image.load(f"assets/images/tiles/{x}.png").convert_alpha()
  tile_image = pygame.transform.scale(tile_image, (constants.TILE_SIZE, constants.TILE_SIZE))
  tile_list.append(tile_image)

#load character images
mob_animations = []
mob_types = ["elf", "imp", "skeleton", "goblin", "muddy", "tiny_zombie", "big_demon"]

animation_types = ["idle", "run"]
for mob in mob_types:
  #load images
  animation_list = []
  for animation in animation_types:
    #reset temporary list of images
    temp_list = []
    for i in range(4):
      img = pygame.image.load(f"assets/images/characters/{mob}/{animation}/{i}.png").convert_alpha()
      img = scale_img(img, constants.SCALE)
      temp_list.append(img)
    animation_list.append(temp_list)
  mob_animations.append(animation_list)


#function for outputting text onto the screen
def draw_text(text, font, text_col, x, y):
  img = font.render(text, True, text_col)
  screen.blit(img, (x, y))

#function for displaying game info
def draw_info():
  pygame.draw.rect(screen, constants.PANEL, (0, 0, constants.SCREEN_WIDTH, 50))
  pygame.draw.line(screen, constants.WHITE, (0, 50), (constants.SCREEN_WIDTH, 50))
  #draw lives
  half_heart_drawn = False
  for i in range(5):
    if player.health >= ((i + 1) * 20):
      screen.blit(heart_full, (10 + i * 50, 0))
    elif (player.health % 20 > 0) and half_heart_drawn == False:
      screen.blit(heart_half, (10 + i * 50, 0))
      half_heart_drawn = True
    else:
      screen.blit(heart_empty, (10 + i * 50, 0))

  #level
  draw_text("LEVEL: " + str(level), font, constants.WHITE, constants.SCREEN_WIDTH / 2, 15)
  #show score
  draw_text(f"X{player.score}", font, constants.WHITE, constants.SCREEN_WIDTH - 100, 15)

#function to reset level
def reset_level():
  damage_text_group.empty()
  arrow_group.empty()
  item_group.empty()
  fireball_group.empty()

  #create empty tile list
  data = []
  for row in range(constants.ROWS):
    r = [-1] * constants.COLS
    data.append(r)

  return data

#damage text class
class DamageText(pygame.sprite.Sprite):
  def __init__(self, x, y, damage, color):
    pygame.sprite.Sprite.__init__(self)
    self.image = font.render(damage, True, color)
    self.rect = self.image.get_rect()
    self.rect.center = (x, y)
    self.counter = 0

  def update(self):
    #reposition based on screen scroll
    self.rect.x += screen_scroll[0]
    self.rect.y += screen_scroll[1]

    #move damage text up
    self.rect.y -= 1
    #delete the counter after a few seconds
    self.counter += 1
    if self.counter > 30:
      self.kill()

#class for handling screen fade
class ScreenFade():
  def __init__(self, direction, colour, speed):
    self.direction = direction
    self.colour = colour
    self.speed = speed
    self.fade_counter = 0

  def fade(self):
    fade_complete = False
    self.fade_counter += self.speed
    if self.direction == 1:#whole screen fade
      pygame.draw.rect(screen, self.colour, (0 - self.fade_counter, 0, constants.SCREEN_WIDTH // 2, constants.SCREEN_HEIGHT))
      pygame.draw.rect(screen, self.colour, (constants.SCREEN_WIDTH // 2 + self.fade_counter, 0, constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
      pygame.draw.rect(screen, self.colour, (0, 0 - self.fade_counter, constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT // 2))
      pygame.draw.rect(screen, self.colour, (0, constants.SCREEN_HEIGHT // 2 + self.fade_counter, constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    elif self.direction == 2:#vertical screen fade down
      pygame.draw.rect(screen, self.colour, (0, 0, constants.SCREEN_WIDTH, 0 + self.fade_counter))

    if self.fade_counter >= constants.SCREEN_WIDTH:
      fade_complete = True

    return fade_complete

def generate_new_level():
  #generate new level
  GENERATED_LEVEL_SIZE = 16
  NC = 4

  #generate random noise
  noise = tf.random.normal(generator.input_shape[1:])
  noise = tf.expand_dims(noise, axis=0)

  #generate image
  generated_level = generator(noise, training=False)

  generated_level = generated_level.numpy().reshape(GENERATED_LEVEL_SIZE, GENERATED_LEVEL_SIZE, NC).argmax(axis=2)
  generated_level = generated_level[:GENERATED_LEVEL_SIZE, :GENERATED_LEVEL_SIZE]

  generated_level[generated_level == 1] = 7
  generated_level[generated_level == 2] = 10
  generated_level[generated_level == 3] = 12

  #add player to a random floor tile
  player_tile = (0, 0)
  while generated_level[player_tile] != 7:
    player_tile = (np.random.randint(0, GENERATED_LEVEL_SIZE), np.random.randint(0, GENERATED_LEVEL_SIZE))
  
  generated_level[player_tile] = 11

  #add exit to a random floor tile
  exit_tile = (0, 0)
  while generated_level[exit_tile] != 7:
    exit_tile = (np.random.randint(0, GENERATED_LEVEL_SIZE), np.random.randint(0, GENERATED_LEVEL_SIZE))
  
  generated_level[exit_tile] = 8

  #add surrounding walls
  generated_level = np.pad(generated_level, 1, mode='constant', constant_values=7)

  return generated_level

#create empty tile list
world_data = []
for row in range(constants.ROWS):
  r = [-1] * constants.COLS
  world_data.append(r)

#load in level data and create world
# with open(f"levels/level{level}_data.csv", newline="") as csvfile:
#   reader = csv.reader(csvfile, delimiter = ",")
#   for x, row in enumerate(reader):
#     for y, tile in enumerate(row):
#       world_data[x][y] = int(tile)

# initial level
world_data = generate_new_level()

world = World()
world.process_data(world_data, tile_list, item_images, mob_animations)

#create player
player = world.player
#create player's weapon
bow = Weapon(bow_image, arrow_image)

#extract enemies from world data
enemy_list = world.character_list

#create sprite groups
damage_text_group = pygame.sprite.Group()
arrow_group = pygame.sprite.Group()
item_group = pygame.sprite.Group()
fireball_group = pygame.sprite.Group()

score_coin = Item(constants.SCREEN_WIDTH - 115, 23, 0, coin_images, True)
item_group.add(score_coin)
#add the items from the level data
for item in world.item_list:
  item_group.add(item)


#create screen fades
intro_fade = ScreenFade(1, constants.BLACK, 4)
death_fade = ScreenFade(2, constants.PINK, 4)

#create button
start_button = Button(constants.SCREEN_WIDTH // 2 - 145, constants.SCREEN_HEIGHT // 2 - 150, start_img)
exit_button = Button(constants.SCREEN_WIDTH // 2 - 110, constants.SCREEN_HEIGHT // 2 + 50, exit_img)
restart_button = Button(constants.SCREEN_WIDTH // 2 - 175, constants.SCREEN_HEIGHT // 2 - 50, restart_img)
resume_button = Button(constants.SCREEN_WIDTH // 2 - 175, constants.SCREEN_HEIGHT // 2 - 150, resume_img)

# todo : temporary level completion handling variable
level_complete = False

#main game loop
run = True
while run:

  #control frame rate
  clock.tick(constants.FPS)

  if start_game == False:
    screen.fill(constants.MENU_BG)
    if start_button.draw(screen):
      start_game = True
      start_intro = True
    if exit_button.draw(screen):
      run = False
  else:
    if not has_trigger_start_event:
      start_new_game()
      has_trigger_start_event = True
    if pause_game == True:
      has_trigger_start_event = False
      end_game()
      screen.fill(constants.MENU_BG)
      if resume_button.draw(screen):
        pause_game = False
      if exit_button.draw(screen):
        run = False
    else:
      screen.fill(constants.BG)

      if player.alive:
        #calculate player movement
        dx = 0
        dy = 0
        if moving_right == True:
          dx = constants.SPEED
        if moving_left == True:
          dx = -constants.SPEED
        if moving_up == True:
          dy = -constants.SPEED
        if moving_down == True:
          dy = constants.SPEED

        #move player
        # todo : removed level completion detection
        screen_scroll, _ = player.move(dx, dy, world.obstacle_tiles, world.exit_tile)

        #update all objects
        world.update(screen_scroll)
        for enemy in enemy_list:
          fireball = enemy.ai(player, world.obstacle_tiles, screen_scroll, fireball_image)
          if fireball:
            fireball_group.add(fireball)
          if enemy.alive:
            enemy.update()
        player.update()
        arrow = bow.update(player)
        if arrow:
          arrow_group.add(arrow)
          shot_fx.play()
        for arrow in arrow_group:
          damage, damage_pos = arrow.update(screen_scroll, world.obstacle_tiles, enemy_list)
          if damage:
            damage_text = DamageText(damage_pos.centerx, damage_pos.y, str(damage), constants.RED)
            damage_text_group.add(damage_text)
            hit_fx.play()
        damage_text_group.update()
        fireball_group.update(screen_scroll, player)
        item_group.update(screen_scroll, player, coin_fx, heal_fx)

      #draw player on screen
      world.draw(screen)
      for enemy in enemy_list:
        enemy.draw(screen)
      player.draw(screen)
      bow.draw(screen)
      for arrow in arrow_group:
        arrow.draw(screen)
      for fireball in fireball_group:
        fireball.draw(screen)
      damage_text_group.draw(screen)
      item_group.draw(screen)
      draw_info()
      score_coin.draw(screen)

      #check level complete
      if level_complete == True:

        level_complete = False

        start_intro = True
        get_feedback()
        level += 1
        world_data = reset_level()
        
        # #load in level data and create world
        # with open(f"levels/level{level}_data.csv", newline="") as csvfile:
        #   reader = csv.reader(csvfile, delimiter = ",")
        #   for x, row in enumerate(reader):
        #     for y, tile in enumerate(row):
        #       world_data[x][y] = int(tile)

        # new world data
        world_data = generate_new_level()

        world = World()
        world.process_data(world_data, tile_list, item_images, mob_animations)
        temp_hp = player.health
        temp_score = player.score
        player = world.player
        player.health = temp_hp
        player.score = temp_score
        enemy_list = world.character_list
        score_coin = Item(constants.SCREEN_WIDTH - 115, 23, 0, coin_images, True)
        item_group.add(score_coin)
        #add the items from the level data
        for item in world.item_list:
          item_group.add(item)


      #show intro
      if start_intro == True:
        if intro_fade.fade():
          start_intro = False
          intro_fade.fade_counter = 0

      #show death screen
      if player.alive == False:
        if death_fade.fade():
          if restart_button.draw(screen):
            death_fade.fade_counter = 0
            start_intro = True
            world_data = reset_level()
            #load in level data and create world
            with open(f"levels/level{level}_data.csv", newline="") as csvfile:
              reader = csv.reader(csvfile, delimiter = ",")
              for x, row in enumerate(reader):
                for y, tile in enumerate(row):
                  world_data[x][y] = int(tile)
            world = World()
            world.process_data(world_data, tile_list, item_images, mob_animations)
            temp_score = player.score
            player = world.player
            player.score = temp_score
            enemy_list = world.character_list
            score_coin = Item(constants.SCREEN_WIDTH - 115, 23, 0, coin_images, True)
            item_group.add(score_coin)
            #add the items from the level data
            for item in world.item_list:
              item_group.add(item)

  #event handler
  for event in pygame.event.get():
    if event.type == pygame.QUIT:
      run = False
    #take keyboard presses
    if event.type == pygame.KEYDOWN:
      if event.key == pygame.K_a:
        moving_left = True
      if event.key == pygame.K_d:
        moving_right = True
      if event.key == pygame.K_w:
        moving_up = True
      if event.key == pygame.K_s:
        moving_down = True
      if event.key == pygame.K_ESCAPE:
        pause_game = True
      if event.key == pygame.K_UP:
        level_complete = True

    #keyboard button released
    if event.type == pygame.KEYUP:
      if event.key == pygame.K_a:
        moving_left = False
      if event.key == pygame.K_d:
        moving_right = False
      if event.key == pygame.K_w:
        moving_up = False
      if event.key == pygame.K_s:
        moving_down = False

  pygame.display.update()


pygame.quit()