
import pygame
from settings import LOGICAL_W, LOGICAL_H, HUD_HEIGHT, WORLD_W, WORLD_H, TILE_SIZE

def get_camera_rect(player_rect: pygame.Rect) -> pygame.Rect:
    view_h = LOGICAL_H - HUD_HEIGHT
    cam_x = player_rect.centerx - LOGICAL_W // 2
    cam_y = player_rect.centery - view_h // 2

    max_x = WORLD_W * TILE_SIZE - LOGICAL_W
    max_y = WORLD_H * TILE_SIZE - view_h

    cam_x = max(0, min(cam_x, max_x))
    cam_y = max(0, min(cam_y, max_y))

    return pygame.Rect(cam_x, cam_y, LOGICAL_W, view_h)
