"""
Simple particle helpers for Phase 5 visual feedback.
"""

import random
from dataclasses import dataclass

import pygame


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    size: int
    color: tuple[int, int, int]


class ParticleSystem:
    def __init__(self):
        self.particles: list[Particle] = []
        self.enabled = True

    def emit_dust(self, x: float, y: float, count: int = 8):
        if not self.enabled:
            return
        for _ in range(count):
            speed = random.uniform(40, 90)
            angle = random.uniform(-0.8, 0.8)
            vx = speed * angle
            vy = -abs(speed) * 0.4
            size = random.randint(2, 4)
            life = random.uniform(0.25, 0.5)
            self.particles.append(Particle(x, y, vx, vy, life, size, (200, 200, 200)))

    def emit_dash(self, x: float, y: float, direction: int):
        if not self.enabled:
            return
        for _ in range(12):
            speed = random.uniform(120, 200)
            vx = speed * direction * random.uniform(0.6, 1.0)
            vy = random.uniform(-50, 50)
            size = random.randint(2, 3)
            life = random.uniform(0.15, 0.35)
            self.particles.append(Particle(x, y, vx, vy, life, size, (255, 120, 255)))

    def emit_attack_warning(self, x: float, y: float, count: int = 6):
        """
        Emit warning particles during enemy attack windup.

        Red particles that pulse outward from enemy position.
        """
        if not self.enabled:
            return
        import math

        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(20, 40)
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)
            size = random.randint(2, 4)
            life = random.uniform(0.2, 0.4)
            # Red warning color
            self.particles.append(Particle(x, y, vx, vy, life, size, (255, 80, 80)))

    def emit_attack_impact(self, x: float, y: float, count: int = 12):
        """
        Emit impact particles during enemy attack active phase.

        Bright flash particles indicating the strike.
        """
        if not self.enabled:
            return
        import math

        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(60, 120)
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)
            size = random.randint(3, 5)
            life = random.uniform(0.15, 0.3)
            # Bright yellow/white flash
            self.particles.append(Particle(x, y, vx, vy, life, size, (255, 255, 120)))

    def update(self, dt: float):
        if not self.enabled:
            self.particles.clear()
            return
        # In-place removal: swap dead particle with last, pop — avoids list rebuild
        i = 0
        while i < len(self.particles):
            p = self.particles[i]
            p.life -= dt
            if p.life <= 0:
                self.particles[i] = self.particles[-1]
                self.particles.pop()
            else:
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.vy += 300 * dt
                i += 1

    def draw(self, surface: pygame.Surface, camera, color_override=None):
        if not self.enabled:
            return
        for p in self.particles:
            rect = pygame.Rect(int(p.x), int(p.y), p.size, p.size)
            screen_rect = camera.apply(rect)
            pygame.draw.rect(surface, color_override or p.color, screen_rect)
