#!/usr/bin/env python3

import random
import math
import time
from PIL import Image, ImageDraw, ImageFont
import os
import sys
import numpy as np

# Increase recursion limit to avoid RecursionError on 128+ sized dungeons
sys.setrecursionlimit(10000)

# Configuration
dungeon_layout = {
  'Box': [[1,1,1],[1,0,1],[1,1,1]],
  'Cross': [[0,1,0],[1,1,1],[0,1,0]],
}
corridor_layout = {
  'Labyrinth': 0,
  'Bent': 50,
  'Straight': 100,
}
map_style = {
  'Standard': {
    'fill': (0,0,0),
    'open': (255,255,255),
    'open_grid': (204,204,204),
  },
}

# Cell bits
NOTHING = 0x00000000
BLOCKED = 0x00000001
ROOM = 0x00000002
CORRIDOR = 0x00000004
PERIMETER = 0x00000010
ENTRANCE = 0x00000020
ROOM_ID = 0x0000FFC0
ARCH = 0x00010000
DOOR = 0x00020000
LOCKED = 0x00040000
TRAPPED = 0x00080000
SECRET = 0x00100000
PORTC = 0x00200000
STAIR_DN = 0x00400000
STAIR_UP = 0x00800000
LABEL = 0xFF000000

OPENSPACE = ROOM | CORRIDOR
DOORSPACE = ARCH | DOOR | LOCKED | TRAPPED | SECRET | PORTC
ESPACE = ENTRANCE | DOORSPACE | 0xFF000000
STAIRS = STAIR_DN | STAIR_UP
BLOCK_ROOM = BLOCKED | ROOM
BLOCK_CORR = BLOCKED | PERIMETER | CORRIDOR
BLOCK_DOOR = BLOCKED | DOORSPACE

# Directions
di = {'north': -1, 'south': 1, 'west': 0, 'east': 0}
dj = {'north': 0, 'south': 0, 'west': -1, 'east': 1}
dj_dirs = sorted(dj.keys())

opposite = {
  'north': 'south',
  'south': 'north',
  'west': 'east',
  'east': 'west'
}

# Stairs
stair_end = {
  'north': {
    'walled': [[1,-1],[0,-1],[-1,-1],[-1,0],[-1,1],[0,1],[1,1]],
    'corridor': [[0,0],[1,0],[2,0]],
    'stair': [0,0],
    'next': [1,0],
  },
  'south': {
    'walled': [[-1,-1],[0,-1],[1,-1],[1,0],[1,1],[0,1],[-1,1]],
    'corridor': [[0,0],[-1,0],[-2,0]],
    'stair': [0,0],
    'next': [-1,0],
  },
  'west': {
    'walled': [[-1,1],[-1,0],[-1,-1],[0,-1],[1,-1],[1,0],[1,1]],
    'corridor': [[0,0],[0,1],[0,2]],
    'stair': [0,0],
    'next': [0,1],
  },
  'east': {
    'walled': [[-1,-1],[-1,0],[-1,1],[0,1],[1,1],[1,0],[1,-1]],
    'corridor': [[0,0],[0,-1],[0,-2]],
    'stair': [0,0],
    'next': [0,-1],
  },
}

# Cleaning
close_end = {
  'north': {
    'walled': [[0,-1],[1,-1],[1,0],[1,1],[0,1]],
    'close': [[0,0]],
    'recurse': [-1,0],
  },
  'south': {
    'walled': [[0,-1],[-1,-1],[-1,0],[-1,1],[0,1]],
    'close': [[0,0]],
    'recurse': [1,0],
  },
  'west': {
    'walled': [[-1,0],[-1,1],[0,1],[1,1],[1,0]],
    'close': [[0,0]],
    'recurse': [0,-1],
  },
  'east': {
    'walled': [[-1,0],[-1,-1],[0,-1],[1,-1],[1,0]],
    'close': [[0,0]],
    'recurse': [0,1],
  },
}

# Color chain
color_chain = {
  'door': 'fill',
  'label': 'fill',
  'stair': 'wall',
  'wall': 'fill',
  'fill': 'black',
}

def get_opts():
  opts = {
    'seed': int(time.time()),
    'n_rows': 32,          # must be an odd number
    'n_cols': 32,          # must be an odd number
    'dungeon_layout': 'None', # Box, Cross, Round
    'room_min': 4,         # minimum room size
    'room_max': 4,         # maximum room size
    'room_size': 4,     # Optional fixed room size or None
    'room_layout': 'Packed', # Packed, Scattered
    'corridor_layout': 'Labyrinth', # Labyrinth, Bent, Straight
    'remove_deadends': 100, # percentage
    'add_stairs': 2,       # number of stairs
    'map_style': 'Standard', # Standard
    'cell_size': 18,       # pixels
  }
  return opts

def create_dungeon(opts):
  dungeon = opts.copy()
  dungeon['n_i'] = dungeon['n_rows'] // 2
  dungeon['n_j'] = dungeon['n_cols'] // 2
  dungeon['n_rows'] = dungeon['n_i'] * 2
  dungeon['n_cols'] = dungeon['n_j'] * 2
  dungeon['max_row'] = dungeon['n_rows'] - 1
  dungeon['max_col'] = dungeon['n_cols'] - 1
  dungeon['n_rooms'] = 0

  maximum = dungeon['room_max']
  minimum = dungeon['room_min']
  dungeon['room_base'] = (minimum + 1) // 2
  dungeon['room_radix'] = ((maximum - minimum) // 2) + 1
  if dungeon['room_size']:
    dungeon['room_radix'] = 0
    dungeon['room_base'] = dungeon['room_size']

  dungeon = init_cells(dungeon)
  dungeon = emplace_rooms(dungeon)
  dungeon = open_rooms(dungeon)
  dungeon = label_rooms(dungeon)
  dungeon = corridors(dungeon)
  if dungeon.get('add_stairs'):
    dungeon = emplace_stairs(dungeon)
  dungeon = clean_dungeon(dungeon)

  return dungeon

def init_cells(dungeon):
  dungeon['cell'] = [[NOTHING for _ in range(dungeon['n_cols'] +1)] for _ in range(dungeon['n_rows'] +1)]
  random.seed(dungeon['seed'])

  mask = dungeon_layout.get(dungeon['dungeon_layout'])
  if mask:
    dungeon = mask_cells(dungeon, mask)
  elif dungeon['dungeon_layout'] == 'Round':
    dungeon = round_mask(dungeon)
  return dungeon

def mask_cells(dungeon, mask):
  r_x = len(mask) / (dungeon['n_rows'] +1)
  c_x = len(mask[0]) / (dungeon['n_cols'] +1)
  cell = dungeon['cell']

  for r in range(dungeon['n_rows'] +1):
    for c in range(dungeon['n_cols'] +1):
      if not mask[int(r * r_x)][int(c * c_x)]:
        cell[r][c] = BLOCKED
  return dungeon

def round_mask(dungeon):
  center_r = dungeon['n_rows'] // 2
  center_c = dungeon['n_cols'] // 2
  cell = dungeon['cell']

  for r in range(dungeon['n_rows'] +1):
    for c in range(dungeon['n_cols'] +1):
      d = math.sqrt((r - center_r) ** 2 + (c - center_c) ** 2)
      if d > center_c:
        cell[r][c] = BLOCKED
  return dungeon

def emplace_rooms(dungeon):
  if dungeon['room_layout'] == 'Packed':
    dungeon = pack_rooms(dungeon)
  else:
    dungeon = scatter_rooms(dungeon)
  return dungeon

def pack_rooms(dungeon):
  cell = dungeon['cell']
  for i in range(dungeon['n_i']):
    r = (i * 2) + 1
    for j in range(dungeon['n_j']):
      c = (j * 2) + 1
      if cell[r][c] & ROOM:
        continue
      if (i == 0 or j == 0) and random.randint(0,1):
        continue
      proto = {'i': i, 'j': j}
      dungeon = emplace_room(dungeon, proto)
  return dungeon

def scatter_rooms(dungeon):
  n_rooms = alloc_rooms(dungeon)
  for _ in range(n_rooms):
    dungeon = emplace_room(dungeon)
  return dungeon

def alloc_rooms(dungeon):
  dungeon_area = dungeon['n_cols'] * dungeon['n_rows']
  room_area = dungeon['room_max'] **2
  n_rooms = dungeon_area // room_area
  return n_rooms

def emplace_room(dungeon, proto=None):
  if dungeon.get('n_rooms',0) == 999:
    return dungeon
  cell = dungeon['cell']

  proto = set_room(dungeon, proto) if proto else set_room(dungeon, {})
  r1 = (proto['i'] * 2) +1
  c1 = (proto['j'] * 2) +1
  r2 = ((proto['i'] + proto['height']) *2) -1
  c2 = ((proto['j'] + proto['width']) *2) -1

  if r1 <1 or r2 > dungeon['max_row'] or c1 <1 or c2 > dungeon['max_col']:
    return dungeon

  hit = sound_room(dungeon, r1, c1, r2, c2)
  if isinstance(hit, dict) and hit.get('blocked'):
    return dungeon
  if len(hit) >0:
    return dungeon

  room_id = dungeon.get('n_rooms',0) +1
  dungeon['n_rooms'] = room_id
  dungeon['last_room_id'] = room_id

  for r in range(r1, r2+1):
    for c in range(c1, c2+1):
      if cell[r][c] & ENTRANCE:
        cell[r][c] &= ~ESPACE
      elif cell[r][c] & PERIMETER:
        cell[r][c] &= ~PERIMETER
      cell[r][c] |= ROOM | (room_id <<6)

  height = (r2 - r1 +1) *10
  width = (c2 - c1 +1) *10
  room_data = {
    'id': room_id, 'row': r1, 'col': c1,
    'north': r1, 'south': r2, 'west': c1, 'east': c2,
    'height': height, 'width': width, 'area': height * width
  }
  dungeon.setdefault('room', {})[room_id] = room_data

  for r in range(r1 -1, r2 +2):
    if not (cell[r][c1 -1] & (ROOM | ENTRANCE)):
      cell[r][c1 -1] |= PERIMETER
    if not (cell[r][c2 +1] & (ROOM | ENTRANCE)):
      cell[r][c2 +1] |= PERIMETER
  for c in range(c1 -1, c2 +2):
    if not (cell[r1 -1][c] & (ROOM | ENTRANCE)):
      cell[r1 -1][c] |= PERIMETER
    if not (cell[r2 +1][c] & (ROOM | ENTRANCE)):
      cell[r2 +1][c] |= PERIMETER

  return dungeon

def set_room(dungeon, proto):
  base = dungeon['room_base']
  radix = dungeon['room_radix']
  if dungeon.get('room_size'):
    proto['height'] = dungeon['room_size']
    proto['width'] = dungeon['room_size']
  else:
    if 'height' not in proto:
      if 'i' in proto:
        a = dungeon['n_i'] - base - proto['i']
        a = max(a,0)
        r = min(a, radix)
        proto['height'] = random.randint(0, r) + base
      else:
        proto['height'] = random.randint(0, radix) + base
    if 'width' not in proto:
      if 'j' in proto:
        a = dungeon['n_j'] - base - proto['j']
        a = max(a,0)
        r = min(a, radix)
        proto['width'] = random.randint(0, r) + base
      else:
        proto['width'] = random.randint(0, radix) + base
  if 'i' not in proto:
    proto['i'] = random.randint(0, dungeon['n_i'] - proto['height'])
  if 'j' not in proto:
    proto['j'] = random.randint(0, dungeon['n_j'] - proto['width'])
  return proto

def sound_room(dungeon, r1, c1, r2, c2):
  cell = dungeon['cell']
  hit = {}
  for r in range(r1, r2+1):
    for c in range(c1, c2+1):
      if cell[r][c] & BLOCKED:
        return {'blocked':1}
      if cell[r][c] & ROOM:
        id_ = (cell[r][c] & ROOM_ID) >>6
        hit[id_] = hit.get(id_,0) +1
  return hit

def open_rooms(dungeon):
  for id_ in range(1, dungeon.get('n_rooms',0)+1):
    dungeon = open_room(dungeon, dungeon['room'][id_])
  dungeon.pop('connect',None)
  return dungeon

def open_room(dungeon, room):
  list_ = door_sills(dungeon, room)
  if not list_:
    return dungeon
  n_opens = alloc_opens(dungeon, room)
  cell = dungeon['cell']
  for _ in range(n_opens):
    if not list_:
      break
    sill = list_.pop(random.randint(0, len(list_)-1))
    door_r = sill['door_r']
    door_c = sill['door_c']
    door_cell = cell[door_r][door_c]
    if door_cell & DOORSPACE:
      continue
    out_id = sill.get('out_id')
    if out_id:
      connect = tuple(sorted([room['id'], out_id]))
      if dungeon.get('connect', {}).get(connect):
        continue
      dungeon.setdefault('connect', {})[connect] =1
    open_r = sill['sill_r']
    open_c = sill['sill_c']
    open_dir = sill['dir']

    for x in range(3):
      r = open_r + di[open_dir] *x
      c = open_c + dj[open_dir] *x
      cell[r][c] &= ~PERIMETER
      cell[r][c] |= ENTRANCE

    door_type_ = door_type()
    door = {'row': door_r, 'col': door_c}

    if door_type_ == ARCH:
      cell[door_r][door_c] |= ARCH
      door['key'] = 'arch'
      door['type'] = 'Archway'
    elif door_type_ == DOOR:
      cell[door_r][door_c] |= DOOR
      cell[door_r][door_c] |= (ord('o') <<24)
      door['key'] = 'open'
      door['type'] = 'Unlocked Door'
    elif door_type_ == LOCKED:
      cell[door_r][door_c] |= LOCKED
      cell[door_r][door_c] |= (ord('x') <<24)
      door['key'] = 'lock'
      door['type'] = 'Locked Door'
    elif door_type_ == TRAPPED:
      cell[door_r][door_c] |= TRAPPED
      cell[door_r][door_c] |= (ord('t') <<24)
      door['key'] = 'trap'
      door['type'] = 'Trapped Door'
    elif door_type_ == SECRET:
      cell[door_r][door_c] |= SECRET
      cell[door_r][door_c] |= (ord('s') <<24)
      door['key'] = 'secret'
      door['type'] = 'Secret Door'
    elif door_type_ == PORTC:
      cell[door_r][door_c] |= PORTC
      cell[door_r][door_c] |= (ord('#') <<24)
      door['key'] = 'portc'
      door['type'] = 'Portcullis'
    
    if out_id:
      door['out_id'] = out_id
    room.setdefault('door', {}).setdefault(open_dir, []).append(door)
    dungeon.setdefault('door', []).append(door)
  return dungeon

def alloc_opens(dungeon, room):
  room_h = ((room['south'] - room['north']) //2 ) +1
  room_w = ((room['east'] - room['west']) //2 ) +1
  flumph = int(math.sqrt(room_w * room_h))
  n_opens = flumph + random.randint(0, flumph-1)
  return n_opens

def door_sills(dungeon, room):
  cell = dungeon['cell']
  sills = []
  if room['north'] >=3:
    for c in range(room['west'], room['east']+1, 2):
      sill = check_sill(cell, room, room['north'], c, 'north')
      if sill:
        sills.append(sill)
  if room['south'] <= (dungeon['n_rows'] -3):
    for c in range(room['west'], room['east']+1, 2):
      sill = check_sill(cell, room, room['south'], c, 'south')
      if sill:
        sills.append(sill)
  if room['west'] >=3:
    for r in range(room['north'], room['south']+1,2):
      sill = check_sill(cell, room, r, room['west'], 'west')
      if sill:
        sills.append(sill)
  if room['east'] <= (dungeon['n_cols'] -3):
    for r in range(room['north'], room['south']+1,2):
      sill = check_sill(cell, room, r, room['east'], 'east')
      if sill:
        sills.append(sill)
  random.shuffle(sills)
  return sills

def check_sill(cell, room, sill_r, sill_c, dir_):
  door_r = sill_r + di[dir_]
  door_c = sill_c + dj[dir_]
  door_cell = cell[door_r][door_c]
  if not (door_cell & PERIMETER):
    return None
  if door_cell & BLOCK_DOOR:
    return None
  out_r = door_r + di[dir_]
  out_c = door_c + dj[dir_]
  if out_r <0 or out_r > len(cell)-1 or out_c <0 or out_c > len(cell[0])-1:
    return None
  out_cell = cell[out_r][out_c]
  if out_cell & BLOCKED:
    return None
  out_id = None
  if out_cell & ROOM:
    out_id = (out_cell & ROOM_ID) >>6
    if out_id == room['id']:
      return None
  return {
    'sill_r': sill_r,
    'sill_c': sill_c,
    'dir': dir_,
    'door_r': door_r,
    'door_c': door_c,
    'out_id': out_id,
  }

def shuffle(lst):
  random.shuffle(lst)
  return lst

def door_type():
  i = random.randint(0,109)
  if i <15:
    return ARCH
  elif i <60:
    return DOOR
  elif i <75:
    return LOCKED
  elif i <90:
    return TRAPPED
  elif i <100:
    return SECRET
  else:
    return PORTC

def label_rooms(dungeon):
  cell = dungeon['cell']
  for id_ in range(1, dungeon.get('n_rooms',0)+1):
    room = dungeon['room'][id_]
    label = str(room['id'])
    length = len(label)
    label_r = (room['north'] + room['south']) //2
    label_c = (room['west'] + room['east'] - length) //2 +1
    for c in range(length):
      char = label[c]
      cell[label_r][label_c +c] |= (ord(char) <<24)
  return dungeon

def corridors(dungeon):
  cell = dungeon['cell']
  for i in range(1, dungeon['n_i']):
    r = (i *2) +1
    for j in range(1, dungeon['n_j']):
      c = (j *2) +1
      if cell[r][c] & CORRIDOR:
        continue
      dungeon = tunnel(dungeon, i, j)
  return dungeon

def tunnel(dungeon, i, j, last_dir=None):
  dirs = tunnel_dirs(dungeon, last_dir)
  for dir_ in dirs:
    if open_tunnel(dungeon, i, j, dir_):
      next_i = i + di[dir_]
      next_j = j + dj[dir_]
      dungeon = tunnel(dungeon, next_i, next_j, dir_)
  return dungeon

def tunnel_dirs(dungeon, last_dir):
  p = corridor_layout.get(dungeon['corridor_layout'],0)
  dirs = dj_dirs.copy()
  random.shuffle(dirs)
  if last_dir and p:
    if random.randint(0,99) < p:
      dirs.insert(0, last_dir)
  return dirs

def open_tunnel(dungeon, i, j, dir_):
  this_r = (i *2) +1
  this_c = (j *2) +1
  next_r = ((i + di[dir_]) *2) +1
  next_c = ((j + dj[dir_]) *2) +1
  mid_r = (this_r + next_r) //2
  mid_c = (this_c + next_c) //2

  if not sound_tunnel(dungeon, mid_r, mid_c, next_r, next_c):
    return False
  delve_tunnel(dungeon, this_r, this_c, next_r, next_c)
  return True

def sound_tunnel(dungeon, mid_r, mid_c, next_r, next_c):
  if next_r <0 or next_r > dungeon['n_rows'] or next_c <0 or next_c > dungeon['n_cols']:
    return False
  cell = dungeon['cell']
  r1, r2 = sorted([mid_r, next_r])
  c1, c2 = sorted([mid_c, next_c])
  for r in range(r1, r2+1):
    for c in range(c1, c2+1):
      if cell[r][c] & BLOCK_CORR:
        return False
  return True

def delve_tunnel(dungeon, this_r, this_c, next_r, next_c):
  cell = dungeon['cell']
  r1, r2 = sorted([this_r, next_r])
  c1, c2 = sorted([this_c, next_c])
  for r in range(r1, r2+1):
    for c in range(c1, c2+1):
      cell[r][c] &= ~ENTRANCE
      cell[r][c] |= CORRIDOR

def emplace_stairs(dungeon):
  n = dungeon.get('add_stairs',0)
  if n <=0:
    return dungeon
  list_ = stair_ends(dungeon)
  if not list_:
    return dungeon
  cell = dungeon['cell']
  for _ in range(n):
    if not list_:
      break
    stair = list_.pop(random.randint(0, len(list_)-1))
    r = stair['row']
    c = stair['col']
    type_ = 0 if _ <2 else random.randint(0,1)
    if type_ ==0:
      cell[r][c] |= STAIR_DN
      cell[r][c] |= (ord('d') <<24)
      stair['key'] = 'down'
    else:
      cell[r][c] |= STAIR_UP
      cell[r][c] |= (ord('u') <<24)
      stair['key'] = 'up'
    dungeon.setdefault('stair',[]).append(stair)
  return dungeon

def stair_ends(dungeon):
  cell = dungeon['cell']
  list_ = []
  for i in range(dungeon['n_i']):
    r = (i *2) +1
    for j in range(dungeon['n_j']):
      c = (j *2) +1
      if cell[r][c] != CORRIDOR:
        continue
      if cell[r][c] & STAIRS:
        continue
      for dir_, checks in stair_end.items():
        if check_tunnel(cell, r, c, checks):
          end = {'row': r, 'col': c}
          end['next_row'] = end['row'] + checks['next'][0]
          end['next_col'] = end['col'] + checks['next'][1]
          list_.append(end)
          break
  return list_

def check_tunnel(cell, r, c, checks):
  corridor = checks.get('corridor',[])
  for p in corridor:
    if cell[r +p[0]][c +p[1]] != CORRIDOR:
      return False
  walled = checks.get('walled',[])
  for p in walled:
    if cell[r +p[0]][c +p[1]] & OPENSPACE:
      return False
  return True

def clean_dungeon(dungeon):
  if dungeon.get('remove_deadends'):
    dungeon = remove_deadends(dungeon)
  dungeon = fix_doors(dungeon)
  dungeon = empty_blocks(dungeon)
  return dungeon

def remove_deadends(dungeon):
  p = dungeon['remove_deadends']
  return collapse_tunnels(dungeon, p, close_end)

def collapse_tunnels(dungeon, p, xc):
  all_ = (p ==100)
  cell = dungeon['cell']
  for i in range(dungeon['n_i']):
    r = (i *2) +1
    for j in range(dungeon['n_j']):
      c = (j *2) +1
      if not (cell[r][c] & OPENSPACE):
        continue
      if cell[r][c] & STAIRS:
        continue
      if not all_ and random.randint(0,99) >= p:
        continue
      dungeon = collapse(dungeon, r, c, xc)
  return dungeon

def collapse(dungeon, r, c, xc):
  cell = dungeon['cell']
  if not (cell[r][c] & OPENSPACE):
    return dungeon
  for dir_, checks in xc.items():
    if check_tunnel(cell, r, c, checks):
      for p in checks.get('close',[]):
        cell[r +p[0]][c +p[1]] = NOTHING
      open_ = checks.get('close')
      if 'open' in checks:
        cell[r +checks['open'][0]][c +checks['open'][1]] |= CORRIDOR
      recurse = checks.get('recurse')
      if recurse:
        dungeon = collapse(dungeon, r +recurse[0], c +recurse[1], xc)
  return dungeon

def fix_doors(dungeon):
  # cell = dungeon['cell']
  # fixed = {}
  # for room in dungeon.get('room', {}).values():
  #   for dir_, doors in list(room.get('door', {}).items()):
  #     shiny = []
  #     for door in doors:
  #       door_r = door['row']
  #       door_c = door['col']
  #       door_cell = cell[door_r][door_c]
  #       if not (door_cell & OPENSPACE):
  #         continue
  #       if fixed.get((door_r, door_c)):
  #         shiny.append(door)
  #       else:
  #         out_id = door.get('out_id')
  #         if out_id:
  #           out_dir = opposite[dir_]
  #           dungeon['room'][out_id]['door'].setdefault(out_dir, []).append(door)
  #         shiny.append(door)
  #         fixed[(door_r, door_c)] =1
  #     if shiny:
  #       room['door'][dir_] = shiny
  #       dungeon['door'] = dungeon.get('door',[]) + shiny
  #     else:
  #       room['door'].pop(dir_, None)
  return dungeon

def empty_blocks(dungeon):
  cell = dungeon['cell']
  for r in range(dungeon['n_rows'] +1):
    for c in range(dungeon['n_cols'] +1):
      if cell[r][c] & BLOCKED:
        cell[r][c] = NOTHING
  return dungeon

def image_dungeon(dungeon):
  image = scale_dungeon(dungeon)
  ih = Image.new('RGB', (image['width'], image['height']), map_style[image['map_style']]['fill'])
  draw = ImageDraw.Draw(ih)

  # Fill open spaces
  for r in range(dungeon['n_rows'] +1):
    for c in range(dungeon['n_cols'] +1):
      if dungeon['cell'][r][c] & OPENSPACE:
        x1 = c * image['cell_size']
        y1 = r * image['cell_size']
        x2 = x1 + image['cell_size']
        y2 = y1 + image['cell_size']
        draw.rectangle([x1, y1, x2, y2], fill=map_style[image['map_style']]['open'])

  # Draw walls, doors, labels, stairs as needed
  # ... (Implement drawing logic similar to Perl code)

  os.makedirs('dungeon_images', exist_ok=True)
  file_path = os.path.join("dungeon_images", f"{dungeon['seed']}.gif")
  ih.save(file_path)
  return file_path

def scale_dungeon(dungeon):
  image = {
    'cell_size': dungeon['cell_size'],
    'map_style': dungeon['map_style'],
  }
  image['width'] = (dungeon['n_cols'] +1) * image['cell_size'] +1
  image['height'] = (dungeon['n_rows'] +1) * image['cell_size'] +1

  if image['cell_size'] >16:
    image['font'] = ImageFont.load_default()  # Replace with appropriate large font
  elif image['cell_size'] >12:
    image['font'] = ImageFont.load_default()  # Replace with appropriate small font
  else:
    image['font'] = ImageFont.load_default()  # Replace with appropriate tiny font

  return image

def main():
  opts = get_opts()
  dungeon = create_dungeon(opts)

  dungeon_np = dungeon_to_numpy(dungeon)
  print(dungeon_np.shape)

  unique, counts = np.unique(dungeon_np, return_counts=True)
  print(list(zip(unique, counts)))

  # # Enlarge the numpy array so the room size goes from 4 to 16
  # scale_factor = 4
  # enlarged_dungeon_np = np.repeat(np.repeat(dungeon_np, scale_factor, axis=0), scale_factor, axis=1)
  # print(enlarged_dungeon_np.shape)

  # unique, counts = np.unique(enlarged_dungeon_np, return_counts=True)
  # print(list(zip(unique, counts)))

  # dungeon_np = enlarged_dungeon_np

  os.makedirs('dungeon_texts', exist_ok=True)
  file_path = os.path.join("dungeon_texts", f"{opts['seed']}.txt")
  np.savetxt(file_path, dungeon_np, fmt='%d', delimiter=',')
  print(f"Dungeon data saved as {file_path}")

  image_file = image_dungeon(dungeon)
  # print(f"Dungeon image saved as {image_file}")

def dungeon_to_numpy(dungeon):
  grid = np.zeros((dungeon['n_rows'] + 1, dungeon['n_cols'] + 1), dtype=int)
  for r in range(dungeon['n_rows'] + 1):
    for c in range(dungeon['n_cols'] + 1):
      cell = dungeon['cell'][r][c]
      if cell & STAIRS:
        grid[r][c] = 2
      elif cell & (BLOCKED | PERIMETER):
        grid[r][c] = 1
      else:
        grid[r][c] = 0
  return grid

main()

