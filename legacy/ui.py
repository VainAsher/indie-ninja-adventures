
import pygame
from settings import FONT, FONT_BIG, COLOR_TEXT, COLOR_BTN_BG, COLOR_BTN_BG_HOVER, COLOR_HUD_BG, HUD_HEIGHT

class Button:
    def __init__(self, label, on_click):
        self.label = label
        self.on_click = on_click
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.hover = False

    def layout(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.on_click()

    def draw(self, surf):
        bg = COLOR_BTN_BG_HOVER if self.hover else COLOR_BTN_BG
        pygame.draw.rect(surf, bg, self.rect, border_radius=8)
        txt = FONT.render(self.label, True, COLOR_TEXT)
        tr = txt.get_rect(center=self.rect.center)
        surf.blit(txt, tr)

class TextInput:
    def __init__(self, prompt, initial=""):
        self.prompt = prompt
        self.text = str(initial)
        self.active = True

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.active = False
            else:
                ch = event.unicode
                if ch.isprintable():
                    self.text += ch

    def draw(self, surf, rect):
        pygame.draw.rect(surf, (30, 30, 50), rect, border_radius=10)
        pygame.draw.rect(surf, (90, 90, 140), rect, 2, border_radius=10)
        p = FONT.render(self.prompt, True, COLOR_TEXT)
        t = FONT_BIG.render(self.text or " ", True, COLOR_TEXT)
        surf.blit(p, (rect.x + 16, rect.y + 12))
        surf.blit(t, (rect.x + 16, rect.y + 12 + p.get_height() + 8))

def draw_hud(surf, text_left, text_right):
    bar = pygame.Rect(0, 0, surf.get_width(), HUD_HEIGHT)
    pygame.draw.rect(surf, COLOR_HUD_BG, bar)
    l = FONT.render(text_left, True, COLOR_TEXT)
    r = FONT.render(text_right, True, COLOR_TEXT)
    surf.blit(l, (12, (HUD_HEIGHT - l.get_height()) // 2))
    rr = r.get_rect(topright=(surf.get_width() - 12, (HUD_HEIGHT - r.get_height()) // 2))
    surf.blit(r, rr)
