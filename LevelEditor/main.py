#tilesheet https://erayzesen.itch.io/pixel-platformer
#background https://sanctumpixel.itch.io/forest-lite-pixel-art-tileset

import os
import pygame
import button
import csv
import numpy as np
import tensorflow as tf
import warnings

pygame.init()

clock = pygame.time.Clock()
FPS = 60

#game window
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 640
LOWER_MARGIN = 100
SIDE_MARGIN = 400

screen = pygame.display.set_mode((SCREEN_WIDTH + SIDE_MARGIN, SCREEN_HEIGHT + LOWER_MARGIN))
pygame.display.set_caption('Level Editor')

#define game variables
ROWS = 18
COLS = 18
TILE_TYPES = 18
tile_size = 20
current_tile = 0
level = 0
prev_level = 0
scroll_left = False
scroll_right = False
scroll_up = False
scroll_down = False
scroll = [0, 0]
scroll_speed = 1

#save location
SAVE_FOLDER = 'levels'

#store tiles in a list
img_list = []
unscaled_img_list = []
for x in range (TILE_TYPES):
  img = pygame.image.load(f'img/tile/dungeon/{x}.png').convert_alpha()
  unscaled_img_list.append(img)
  img = pygame.transform.scale(img, (tile_size, tile_size))
  img_list.append(img)

save_img = pygame.transform.scale(pygame.image.load('img/save_btn.png').convert_alpha(), (100, 25))
load_img = pygame.transform.scale(pygame.image.load('img/load_btn.png').convert_alpha(), (100, 25))
generate_img = pygame.transform.scale(pygame.image.load('img/generate_btn.png').convert_alpha(), (100, 25))

#define colours
BG = (35, 35, 35)
GREEN = (144, 201, 120)
WHITE = (255, 255, 255)
RED = (200, 25, 25)

#define font
font = pygame.font.SysFont('Futura', 30)

#create empty tile list
world_data = []
for row in range(ROWS):
  r = [0] * COLS
  world_data.append(r)

#function for outputting text onto the screen
def draw_text(text, font, text_col, x, y):
  img = font.render(text, True, text_col)
  screen.blit(img, (x, y))


#function for drawing background
def draw_bg():
  screen.fill(BG)

#draw grid
def draw_grid():
  #vertical lines
  for c in range(COLS + 1):
    pygame.draw.line(screen, WHITE, (c * tile_size - scroll[0], 0), (c * tile_size - scroll[0], SCREEN_HEIGHT))
  #horizontal lines
  for c in range(ROWS + 1):
    pygame.draw.line(screen, WHITE, (0, c * tile_size - scroll[1]), (SCREEN_WIDTH, c * tile_size - scroll[1]))


#function for drawing the world tiles
def draw_world():
  for y, row in enumerate(world_data):
    for x, tile in enumerate(row):
      if tile >= 0:
        screen.blit(img_list[tile], (x * tile_size - scroll[0], y * tile_size - scroll[1]))


def save_data(level, world_data):
  save_path = os.path.join(SAVE_FOLDER, f'level{level}_data.csv')
  with open(save_path, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile, delimiter=',')
    for row in world_data:
      writer.writerow(row)

def load_data(level):
  load_path = os.path.join(SAVE_FOLDER, f'level{level}_data.csv')

  new_data = []
  for row in range(ROWS):
    r = [0] * COLS
    new_data.append(r)

  if not os.path.exists(load_path):
    return new_data
  
  with open(load_path, newline='') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    for x, row in enumerate(reader):
      for y, tile in enumerate(row):
        if x < ROWS and y < COLS:
          new_data[x][y] = int(tile)

  return new_data

# Initialize TensorFlow and suppress warnings
tf.get_logger().setLevel('ERROR')
warnings.filterwarnings('ignore')

# Define model path
GENERATOR_MODEL_PATH = os.path.join("models", "generator.h5")

# Load the generator model
generator = tf.keras.models.load_model(GENERATOR_MODEL_PATH)

# Define function to generate a new level
def generate_new_level():
    GENERATED_LEVEL_SIZE = 16
    NC = 4

    # Generate random noise
    noise = tf.random.normal(generator.input_shape[1:])
    noise = tf.expand_dims(noise, axis=0)

    # Generate image
    generated_level = generator(noise, training=False)
    generated_level = generated_level.numpy().reshape(GENERATED_LEVEL_SIZE, GENERATED_LEVEL_SIZE, NC).argmax(axis=2)
    generated_level = generated_level[:GENERATED_LEVEL_SIZE, :GENERATED_LEVEL_SIZE]

    generated_level[generated_level == 1] = 7
    generated_level[generated_level == 2] = 10
    generated_level[generated_level == 3] = 12

    # Add surrounding walls
    generated_level = np.pad(generated_level, 1, mode='constant', constant_values=7)

    return generated_level.tolist()

# Load first level
world_data = load_data(level)


#create buttons
save_button = button.Button(SCREEN_WIDTH // 2, SCREEN_HEIGHT + LOWER_MARGIN - 50, save_img, 1)
load_button = button.Button(SCREEN_WIDTH // 2 + 200, SCREEN_HEIGHT + LOWER_MARGIN - 50, load_img, 1)
generate_button = button.Button(SCREEN_WIDTH // 2 + 400, SCREEN_HEIGHT + LOWER_MARGIN - 50, generate_img, 1)
#make a button list
button_list = []
button_col = 0
button_row = 0
for i in range(len(img_list)):
  tile_button = button.Button(SCREEN_WIDTH + (50 * button_col) + 25, 50 * button_row + 25, img_list[i], 1)
  button_list.append(tile_button)
  button_col += 1
  if button_col == 7:
    button_col = 0
    button_row += 1
button_list.extend([save_button, load_button, generate_button])


run = True
while run:

  clock.tick(FPS)

  draw_bg()
  draw_grid()
  draw_world()

  #draw bottom panel
  pygame.draw.rect(screen, BG, (0, SCREEN_HEIGHT, SCREEN_WIDTH + SIDE_MARGIN, SCREEN_HEIGHT + LOWER_MARGIN))

  draw_text(f'Level: {level}', font, WHITE, 10, SCREEN_HEIGHT + LOWER_MARGIN - 90)
  draw_text('Press UP or DOWN to change level', font, WHITE, 10, SCREEN_HEIGHT + LOWER_MARGIN - 60)
  if os.path.exists(f'level{level}_data.csv'):
    draw_text('File already exists, be careful when saving!', font, WHITE, 400, SCREEN_HEIGHT + LOWER_MARGIN - 80)

  #save and load data
  if save_button.draw(screen):
    #save level data
    save_data(level, world_data)

  if load_button.draw(screen):
    #load in level data
    #reset scroll back to the start of the level
    scroll = [0, 0]
    save_trigger = 0
    load_path = os.path.join(SAVE_FOLDER, f'level{level}_data.csv')
    
    world_data = load_data(level)

  if generate_button.draw(screen):
    # Generate a new level
    world_data = generate_new_level()

  #draw tile panel and tiles
  pygame.draw.rect(screen, GREEN, (SCREEN_WIDTH, 0, SIDE_MARGIN, SCREEN_HEIGHT))
  #choose a tile
  button_count = 0
  for button_count, i in enumerate(button_list):
    if i.draw(screen):
      current_tile = button_count

  #highlight the selected tile
  pygame.draw.rect(screen, RED, button_list[current_tile].rect, 3)

  #scroll the map
  if scroll_left == True and scroll[0] > 0:
    scroll[0] -= 5 * scroll_speed
    if scroll[0] < 0:
      scroll[0] = 0
  if scroll_right == True and scroll[0] < (COLS * tile_size) - SCREEN_WIDTH:
    scroll[0] += 5 * scroll_speed
    if scroll[0] > (COLS * tile_size) - SCREEN_WIDTH:
      scroll[0] = (COLS * tile_size) - SCREEN_WIDTH
  if scroll_up == True and scroll[1] > 0:
    scroll[1] -= 5 * scroll_speed
    if scroll[1] < 0:
      scroll[1] = 0
  if scroll_down == True and scroll[1] < (ROWS * tile_size) - SCREEN_HEIGHT:
    scroll[1] += 5 * scroll_speed
    if scroll[1] > (ROWS * tile_size) - SCREEN_HEIGHT:
      scroll[1] = (ROWS * tile_size) - SCREEN_HEIGHT

  #add new tiles to the screen
  #get mouse position
  pos = pygame.mouse.get_pos()
  x = (pos[0] + scroll[0]) // tile_size
  y = (pos[1] + scroll[1]) // tile_size

  #check that the coordinates are within the tile area
  if x < ROWS and y < COLS and pos[0] < SCREEN_WIDTH and pos[1] < SCREEN_HEIGHT:
    #update tile value
    if pygame.mouse.get_pressed()[0] == 1:
      if world_data[y][x] != current_tile:
        world_data[y][x] = current_tile
    if pygame.mouse.get_pressed()[2] == 1:
      world_data[y][x] = 0
    if pygame.mouse.get_pressed()[1] == 1 and x < COLS and y < ROWS:
      current_tile = world_data[y][x]

  #event handler
  for event in pygame.event.get():
    if event.type == pygame.QUIT:
      run = False
    #keyboard presses
    if event.type == pygame.KEYDOWN:
      if event.key == pygame.K_UP:
        save_data(level, world_data)
        level += 1
        world_data = load_data(level)
        save_trigger = 0
      if event.key == pygame.K_DOWN and level > 0:
        save_data(level, world_data)
        level -= 1
        world_data = load_data(level)
        save_trigger = 0
      if event.key == pygame.K_a:
        scroll_left = True
      if event.key == pygame.K_d:
        scroll_right = True
      if event.key == pygame.K_w:
        scroll_up = True
      if event.key == pygame.K_s:
        scroll_down = True
      if event.key == pygame.K_LSHIFT:
        scroll_speed = 5

    if event.type == pygame.KEYUP:
      if event.key == pygame.K_a:
        scroll_left = False
      if event.key == pygame.K_d:
        scroll_right = False
      if event.key == pygame.K_w:
        scroll_up = False
      if event.key == pygame.K_s:
        scroll_down = False
      if event.key == pygame.K_LSHIFT:
        scroll_speed = 1

    if event.type == pygame.MOUSEWHEEL:
      if event.y > 0:  # Scroll up
          tile_size = min(100, tile_size + 5)  # Cap at 100
      elif event.y < 0:  # Scroll down
          tile_size = max(5, tile_size - 5)  # Cap at 5
      img_list = [ pygame.transform.scale(img, (tile_size, tile_size)) for img in unscaled_img_list ]

  pygame.display.update()

pygame.quit()