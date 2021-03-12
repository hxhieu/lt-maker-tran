import math, random

from app.constants import WINWIDTH, WINHEIGHT, TILEWIDTH, TILEHEIGHT
from app.engine.sprites import SPRITES

from app.engine import engine, image_mods
from app.engine.game_state import game

class ParticleSystem():
    def __init__(self, nid, particle, abundance, bounds, size, blend=None):
        width, height = size
        self.nid = nid
        self.particle = particle
        self.abundance = int(abundance * width * height)
        self.particles = []

        self.remove_me_flag = False

        self.lx, self.ux, self.ly, self.uy = bounds
        self.blend = blend
    
    def save(self):
        return self.nid

    def update(self):
        for particle in self.particles:
            particle.update()

        # Remove particles that have left the map
        self.particles = [p for p in self.particles if not p.remove_me_flag]

        if len(self.particles) < self.abundance:
            xpos = random.randint(self.lx, self.ux)
            ypos = random.randint(self.ly, self.uy)
            new_particle = self.particle((xpos, ypos))
            self.particles.append(new_particle)

        if self.abundance <= 0 and not self.particles:
            self.remove_me_flag = True

    def prefill(self):
        for _ in range(300):
            self.update()

    def draw(self, surf, offset_x=0, offset_y=0):
        if self.blend:
            engine.blit(surf, self.blend, (offset_x, offset_y), None, engine.BLEND_RGB_ADD)
        for particle in self.particles:
            particle.draw(surf, offset_x, offset_y)

class Particle():
    sprite = None

    def __init__(self, pos):
        self.x, self.y = pos
        self.remove_me_flag = False

    def update(self):
        raise NotImplementedError

    def draw(self, surf, offset_x=0, offset_y=0):
        # Most particles do not obey camera offset
        surf.blit(self.sprite, (self.x, self.y))

class Raindrop(Particle):
    sprite = SPRITES.get('particle_raindrop')
    speed = 2

    def update(self):
        self.x += self.speed
        self.y += self.speed * 4
        if game.tilemap and (self.x > game.tilemap.width * TILEWIDTH or self.y > game.tilemap.height * TILEHEIGHT):
            self.remove_me_flag = True

class Sand(Particle):
    sprite = SPRITES.get('particle_sand')
    speed = 6

    def update(self):
        self.x += self.speed * 2
        self.y -= self.speed
        if game.tilemap and (self.x > game.tilemap.width * TILEWIDTH or self.y < -32):
            self.remove_me_flag = True

class Smoke(Particle):
    sprite = SPRITES.get('particle_smoke')
    bottom_sprite = engine.subsurface(sprite, (3, 0, 3, 4))
    top_sprite = engine.subsurface(sprite, (0, 0, 3, 4))
    speed = 6

    def update(self):
        self.x += random.randint(self.speed//2, self.speed)
        self.y -= random.randint(self.speed//2, self.speed)
        if game.tilemap and (self.x > game.tilemap.width * TILEWIDTH or self.y < -32):
            self.remove_me_flag = True
        elif self.x > WINWIDTH:
            self.remove_me_flag = True
        elif self.y < -32:
            self.remove_me_flag = True

    def draw(self, surf, offset_x=0, offset_y=0):
        if self.y < WINHEIGHT//2:
            sprite = self.top_sprite
        else:
            sprite = self.bottom_sprite
        surf.blit(sprite, (self.x + offset_x, self.y + offset_y))

_fire_sprite = SPRITES.get('particle_fire')
class Fire(Particle):
    sprites = [engine.subsurface(_fire_sprite, (0, i*2, 3, 2)) for i in range(6)]

    def __init__(self, pos):
        super().__init__(pos)
        self.speed = random.randint(1, 4)
        self.sprite = self.sprites[-1]

    def update(self):
        self.x -= random.randint(0, self.speed)
        self.y -= random.randint(0, self.speed)
        if self.y > 112:
            self.sprite = self.sprites[-1]
        elif self.y > 104:
            self.sprite = self.sprites[-2]
        elif self.y > 88:
            self.sprite = self.sprites[-3]
        elif self.y > 80:
            self.sprite = self.sprites[-4]
        elif self.y > 72:
            self.sprite = self.sprites[-5]
        elif self.y > 64:
            self.sprite = self.sprites[-6]
        else:
            self.remove_me_flag = True

    def draw(self, surf, offset_x=0, offset_y=0):
        # Fire does obey camera offset
        surf.blit(self.sprite, (self.x + offset_x, self.y + offset_y))

class Snow(Particle):
    sprite = SPRITES.get('particle_snow')

    def __init__(self, pos):
        super().__init__(pos)
        self.sprite = engine.subsurface(self.sprite, (0, random.randint(0, 2) * 8, 8, 8))
        self.speed = random.choice([1.0, 1.5, 2.0, 2.5, 3.0])

    def update(self):
        self.x += self.speed
        self.y += self.speed
        if game.tilemap and (self.x > game.tilemap.width * TILEWIDTH or self.y > game.tilemap.height * TILEHEIGHT):
            self.remove_me_flag = True

class WarpFlower(Particle):
    sprite = SPRITES.get('particle_warp_flower')
    speed = 0
    angle = 0

    def __init__(self, pos, speed, angle):
        super().__init__(pos)
        self.speed = speed
        self.angle = angle

    def update(self):
        self.x += self.speed * math.cos(self.angle)
        self.y += self.speed * math.sin(self.angle)
        if game.tilemap and (self.x < 0 or self.y < 0 or self.x > game.tilemap.width * TILEWIDTH or self.y > game.tilemap.height * TILEHEIGHT):
            self.remove_me_flag = True

class LightMote(Particle):
    sprite = SPRITES.get('particle_light_mote')
    speed = 0.16

    def __init__(self, pos):
        super().__init__(pos)
        self.transparency = .75
        self.change_over_time = random.choice([0.01, 0.02, 0.03])
        self.transition = True

    def update(self):
        self.x += self.speed
        self.y += self.speed

        if self.transition:
            self.transparency -= self.change_over_time
            if self.transparency < 0.05:
                self.transition = False
        else:
            self.transparency += self.change_over_time
            if self.transparency >= 0.75:
                self.remove_me_flag = True
                self.transparency = 1.

    def draw(self, surf, offset_x=0, offset_y=0):
        sprite = image_mods.make_translucent(self.sprite, self.transparency)
        surf.blit(sprite, (self.x, self.y))

class DarkMote(LightMote):
    sprite = SPRITES.get('particle_dark_mote')
    speed = -0.16

def create_system(nid, width, height):
    twidth, theight = width * TILEWIDTH, height * TILEHEIGHT
    if nid == 'rain':
        creation_bounds = -theight // 4, twidth, -16, -8
        ps = ParticleSystem(nid, Raindrop, .1, creation_bounds, (width, height))
    elif nid == 'snow':
        creation_bounds = -theight, twidth, -16, -8
        ps = ParticleSystem(nid, Snow, .125, creation_bounds, (width, height))
    elif nid == 'sand':
        creation_bounds = -2 * theight, twidth, theight + 16, theight + 32
        ps = ParticleSystem(nid, Sand, .075, creation_bounds, (width, height))
    elif nid == 'smoke':
        creation_bounds = -theight, twidth, theight, theight + 16
        ps = ParticleSystem(nid, Smoke, .075, creation_bounds, (width, height))
    elif nid == 'light':
        creation_bounds = 0, twidth, 0, theight
        ps = ParticleSystem(nid, LightMote, .02, creation_bounds, (width, height))
    elif nid == 'dark':
        creation_bounds = 0, twidth, 0, theight
        ps = ParticleSystem(nid, DarkMote, .02, creation_bounds, (width, height))
    elif nid == 'fire':
        creation_bounds = 0, WINWIDTH + 64, WINHEIGHT, WINHEIGHT + 16
        blend = SPRITES.get('particle_bg_fire')
        ps = ParticleSystem(nid, Fire, .06, creation_bounds, (width, height), blend=blend)
    return ps