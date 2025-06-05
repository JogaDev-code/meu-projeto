from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Ellipse, Color, InstructionGroup
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.properties import NumericProperty, ListProperty, StringProperty
import random
import math

# ===== CONSTANTES GLOBAIS =====
CITY_RADIUS = 25
AA_BASE_RADIUS = 20
MISSILE_RADIUS_ENEMY = 10
MISSILE_RADIUS_INTERCEPTOR = 4.5
BASE_EXPLOSION_RANGE = 40         # Explosão "normal"
INTERCEPTOR_EXPLOSION_RANGE = 60    # Explosão do interceptor
BOMB_EXPLOSION_RANGE = 80           # Explosão da bomba
INTERCEPTOR_LIFETIME = 6.0
FIRE_COOLDOWN_TIME = 0.5
ENEMY_SPAWN_INTERVAL = 2.0
INITIAL_ENEMY_SPEED = 2
WARNING_DISTANCE = 80

# Intervalos para power-ups, níveis, avião e bomb drop
POWERUP_SPAWN_INTERVAL = 15.0       # Spawn de power-ups
LEVEL_INTERVAL = 30.0               # Tempo para aumentar o nível
SLOW_MOTION_DURATION = 5.0          # Duração do slow motion
AIRPLANE_SPAWN_INTERVAL = 20.0      # Intervalo para o avião
BOMB_DROP_INTERVAL = 3.0            # Tempo para o avião soltar bomb

# ===== ENTIDADES DO JOGO =====
class City(Widget):
    pos = ListProperty([0, 0])
    lives = NumericProperty(3)
    def __init__(self, pos, **kwargs):
        super().__init__(**kwargs)
        self.pos = pos
        with self.canvas:
            Color(0, 0, 1)
            self.ellipse = Ellipse(pos=(pos[0]-CITY_RADIUS, pos[1]-CITY_RADIUS),
                                   size=(CITY_RADIUS*2, CITY_RADIUS*2))

class AntiAircraft(Widget):
    pos = ListProperty([0, 0])
    def __init__(self, pos, **kwargs):
        super().__init__(**kwargs)
        self.pos = pos
        with self.canvas:
            Color(1, 1, 0)
            self.ellipse = Ellipse(pos=(pos[0]-AA_BASE_RADIUS, pos[1]-AA_BASE_RADIUS),
                                   size=(AA_BASE_RADIUS*2, AA_BASE_RADIUS*2))

class Missile(Widget):
    pos = ListProperty([0, 0])
    def __init__(self, pos, target, speed, missile_type, **kwargs):
        super().__init__(**kwargs)
        self.pos = pos
        self.target = target  # Para interceptor: ponto clicado; para enemy: cidade
        self.speed = speed
        self.missile_type = missile_type  # 'enemy' ou 'interceptor'
        self.life_time = INTERCEPTOR_LIFETIME if missile_type == 'interceptor' else None

        size = (MISSILE_RADIUS_ENEMY*2, MISSILE_RADIUS_ENEMY*2) if missile_type == 'enemy' else (MISSILE_RADIUS_INTERCEPTOR*2, MISSILE_RADIUS_INTERCEPTOR*2)
        with self.canvas:
            Color(1, 0, 0) if missile_type == 'enemy' else Color(0, 1, 0)
            self.ellipse = Ellipse(pos=self.pos, size=size)
        dx = target[0] - pos[0]
        dy = target[1] - pos[1]
        dist = math.hypot(dx, dy) or 0.001
        self.dir = (dx/dist, dy/dist)

    def move(self, dt):
        new_x = self.pos[0] + self.dir[0]*self.speed
        new_y = self.pos[1] + self.dir[1]*self.speed
        self.pos = (new_x, new_y)
        self.ellipse.pos = self.pos
        if self.missile_type == 'interceptor':
            self.life_time -= dt

class Explosion(Widget):
    center_point = ListProperty([0, 0])
    radius = NumericProperty(2)
    explosion_range = NumericProperty(BASE_EXPLOSION_RANGE)
    def __init__(self, center, explosion_range=BASE_EXPLOSION_RANGE, **kwargs):
        super().__init__(**kwargs)
        self.center_point = center
        self.radius = 2
        self.explosion_range = explosion_range
        with self.canvas:
            Color(1, 0.5, 0)
            self.ellipse = Ellipse(pos=(center[0]-self.radius, center[1]-self.radius),
                                   size=(self.radius*2, self.radius*2))
        self.particles = ParticleEffect(center)
        self.canvas.add(self.particles)
    def update(self, dt):
        self.radius += 60*dt
        self.ellipse.size = (self.radius*2, self.radius*2)
        self.ellipse.pos = (self.center_point[0]-self.radius, self.center_point[1]-self.radius)
        self.particles.update(dt)
        return self.radius >= self.explosion_range

# Efeito simples de partículas para explosões
class Particle:
    def __init__(self, pos):
        self.pos = list(pos)
        self.radius = random.uniform(2, 4)
        self.dir = (random.uniform(-1, 1), random.uniform(-1, 1))
        self.speed = random.uniform(30, 60)
        self.life = random.uniform(0.5, 1.0)
        self.alpha = 1.0
    def update(self, dt):
        self.pos[0] += self.dir[0]*self.speed*dt
        self.pos[1] += self.dir[1]*self.speed*dt
        self.life -= dt
        if self.life < 0:
            self.alpha = 0

class ParticleEffect(InstructionGroup):
    def __init__(self, pos, count=20):
        super().__init__()
        self.particles = [Particle(pos) for _ in range(count)]
        self.canvas_instr = []
        for p in self.particles:
            col = Color(1, random.uniform(0.3,1), 0, p.alpha)
            ell = Ellipse(pos=(p.pos[0]-p.radius, p.pos[1]-p.radius), size=(p.radius*2, p.radius*2))
            self.add(col)
            self.add(ell)
            self.canvas_instr.append((col, ell))
    def update(self, dt):
        for i, p in enumerate(self.particles):
            p.update(dt)
            col, ell = self.canvas_instr[i]
            col.a = p.alpha
            ell.pos = (p.pos[0]-p.radius, p.pos[1]-p.radius)

class WarningIndicator(Label):
    def __init__(self, missile, **kwargs):
        super().__init__(**kwargs)
        self.missile = missile
        self.text = "!"
        self.color = (1, 0, 0, 1)
        self.font_size = '20sp'
        self.update_pos()
    def update_pos(self):
        self.center = (self.missile.pos[0]+15, self.missile.pos[1]+15)

class ScoreLabel(Label):
    score = NumericProperty(0)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = "Score: 0"
        self.font_size = '28sp'
        self.color = (1, 1, 1, 1)
        self.bold = True
        self.pos = (0, 0)
        self._update_pos()
        Window.bind(on_resize=self._update_pos)
    def _update_pos(self, *args):
        self.center_x = Window.width/2
        self.top = Window.height - 20
    def update_score(self, new_score):
        self.score = new_score
        self.text = f"Score: {self.score}"

class GameOverLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = "GAME OVER\nToque para reiniciar"
        self.font_size = '40sp'
        self.color = (1, 0, 0, 1)
        self.center = Window.center

# ===== POWER-UPS (mantidos) =====
class BombPowerUp(Widget):
    pos = ListProperty([0, 0])
    powerup_type = StringProperty("bomb")
    def __init__(self, pos, **kwargs):
        super().__init__(**kwargs)
        self.pos = pos
        with self.canvas:
            Color(1, 1, 1)
            self.ellipse = Ellipse(pos=(pos[0]-15, pos[1]-15), size=(30,30))
    def move(self, dt):
        new_y = self.pos[1] - 50*dt
        self.pos = (self.pos[0], new_y)
        self.ellipse.pos = (self.pos[0]-15, self.pos[1]-15)

class SlowMotionPowerUp(Widget):
    pos = ListProperty([0, 0])
    powerup_type = StringProperty("slow")
    def __init__(self, pos, **kwargs):
        super().__init__(**kwargs)
        self.pos = pos
        with self.canvas:
            Color(0, 0, 1)
            self.ellipse = Ellipse(pos=(pos[0]-15, pos[1]-15), size=(30,30))
    def move(self, dt):
        new_y = self.pos[1] - 50*dt
        self.pos = (self.pos[0], new_y)
        self.ellipse.pos = (self.pos[0]-15, self.pos[1]-15)

# ===== AVIÃO E BOMBA =====
class Bomb(Widget):
    pos = ListProperty([0, 0])
    target = ListProperty([0, 0])
    speed = NumericProperty(150)
    def __init__(self, pos, target, **kwargs):
        super().__init__(**kwargs)
        self.pos = pos
        self.target = target  # A cidade-alvo
        with self.canvas:
            Color(1, 1, 0)
            self.ellipse = Ellipse(pos=(pos[0]-10, pos[1]-10), size=(20,20))
    def move(self, dt):
        dx = self.target[0] - self.pos[0]
        dy = self.target[1] - self.pos[1]
        dist = math.hypot(dx, dy) or 0.001
        dir_vector = (dx/dist, dy/dist)
        new_x = self.pos[0] + dir_vector[0]*self.speed*dt
        new_y = self.pos[1] + dir_vector[1]*self.speed*dt
        self.pos = (new_x, new_y)
        self.ellipse.pos = (self.pos[0]-10, self.pos[1]-10)

class Airplane(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.speed = 200
        self.pos = (-50, Window.height-250)
        with self.canvas:
            Color(0.7, 0.7, 0.7)
            self.rect = Ellipse(pos=self.pos, size=(50,20))
        self.bomb_timer = BOMB_DROP_INTERVAL
    def move(self, dt):
        new_x = self.pos[0] + self.speed*dt
        self.pos = (new_x, self.pos[1])
        self.rect.pos = self.pos
        self.bomb_timer -= dt
        return self.bomb_timer <= 0

# ===== LÓGICA PRINCIPAL DO JOGO =====
class MissileCommandGame(Widget):
    score = NumericProperty(0)
    elapsed_time = NumericProperty(0)
    fire_cooldown = NumericProperty(0)
    level = NumericProperty(1)
    slow_motion_active = False
    slow_motion_timer = NumericProperty(0)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.clearcolor = (0.1,0.1,0.1,1)
        self.enemy_missiles = []
        self.interceptor_missiles = []
        self.explosions = []
        self.cities = []
        self.aa_bases = []
        self.warnings = {}
        self.powerups = []
        self.airplanes = []
        self.bombs = []  # Gerencia as bombas lançadas pelo avião
        self.score_label = ScoreLabel()
        self.add_widget(self.score_label)
        self.init_bases_and_cities()
        Clock.schedule_interval(self.update, 1.0/60.0)
        Clock.schedule_interval(self.spawn_enemy, ENEMY_SPAWN_INTERVAL)
        Clock.schedule_interval(self.spawn_airplane, AIRPLANE_SPAWN_INTERVAL)
        Clock.schedule_interval(self.spawn_powerup, POWERUP_SPAWN_INTERVAL)
    def init_bases_and_cities(self):
        # Posiciona as cidades na parte inferior e os AA ao lado delas
        self.city_positions = [
            (Window.width*0.25, 50),
            (Window.width*0.5, 50),
            (Window.width*0.75, 50)
        ]
        # AA posicionados próximos às cidades (à esquerda, centro e direita)
        self.aa_positions = [
            (Window.width*0.25 - 40, 80),
            (Window.width*0.5, 80),
            (Window.width*0.75 + 40, 80)
        ]
        for pos in self.aa_positions:
            aa = AntiAircraft(pos=pos)
            self.aa_bases.append(aa)
            self.add_widget(aa)
        for pos in self.city_positions:
            city = City(pos=pos)
            self.cities.append(city)
            self.add_widget(city)
    def reset_game(self):
        self.clear_widgets()
        self.enemy_missiles = []
        self.interceptor_missiles = []
        self.explosions = []
        self.warnings = {}
        self.powerups = []
        self.airplanes = []
        self.bombs = []
        self.score = 0
        self.elapsed_time = 0
        self.fire_cooldown = 0
        self.level = 1
        self.slow_motion_active = False
        self.slow_motion_timer = 0
        self.score_label.update_score(0)
        self.add_widget(self.score_label)
        self.init_bases_and_cities()
    def spawn_enemy(self, dt):
        if not self.cities:
            return
        self.level = int(self.elapsed_time // LEVEL_INTERVAL) + 1
        speed = INITIAL_ENEMY_SPEED + (self.level*0.5)
        start_x = random.randint(50, int(Window.width-50))
        target = random.choice(self.cities).pos
        missile = Missile(pos=(start_x, Window.height), target=target, speed=speed, missile_type='enemy')
        self.enemy_missiles.append(missile)
        self.add_widget(missile)
    def spawn_airplane(self, dt):
        airplane = Airplane()
        self.airplanes.append(airplane)
        self.add_widget(airplane)
    def spawn_powerup(self, dt):
        x = random.randint(30, int(Window.width-30))
        powerup_type = random.choice(["bomb", "slow"])
        if powerup_type == "bomb":
            powerup = BombPowerUp(pos=(x, Window.height-30))
        else:
            powerup = SlowMotionPowerUp(pos=(x, Window.height-30))
        self.powerups.append(powerup)
        self.add_widget(powerup)
    def on_touch_down(self, touch):
        # Verifica se o toque atingiu um power-up
        for powerup in self.powerups[:]:
            if math.hypot(touch.x-powerup.pos[0], touch.y-powerup.pos[1]) < 30:
                if powerup.powerup_type == "bomb":
                    self.activate_bomb(powerup)
                elif powerup.powerup_type == "slow":
                    self.activate_slow_motion(powerup)
                return
        if hasattr(self, 'game_over_label'):
            self.reset_game()
            self.remove_widget(self.game_over_label)
            del self.game_over_label
            return
        if self.fire_cooldown > 0 or not self.aa_bases:
            return
        base = min(self.aa_bases, key=lambda aa: self.distance(aa.pos, (touch.x, touch.y)))
        interceptor = Missile(pos=base.pos, target=(touch.x, touch.y), speed=6, missile_type='interceptor')
        self.interceptor_missiles.append(interceptor)
        self.add_widget(interceptor)
        self.fire_cooldown = FIRE_COOLDOWN_TIME
    def activate_bomb(self, powerup):
        if powerup in self.powerups:
            self.remove_widget(powerup)
            self.powerups.remove(powerup)
        # Ao ativar, explode todos os mísseis inimigos
        for missile in self.enemy_missiles[:]:
            explosion = Explosion(center=missile.pos, explosion_range=INTERCEPTOR_EXPLOSION_RANGE)
            self.explosions.append(explosion)
            self.add_widget(explosion)
            self.score += 1
            self.score_label.update_score(self.score)
            self.remove_missile(missile)
    def activate_slow_motion(self, powerup):
        if powerup in self.powerups:
            self.remove_widget(powerup)
            self.powerups.remove(powerup)
        self.slow_motion_active = True
        self.slow_motion_timer = SLOW_MOTION_DURATION
    def update(self, dt):
        self.elapsed_time += dt
        if self.fire_cooldown > 0:
            self.fire_cooldown -= dt
        if self.slow_motion_active:
            self.slow_motion_timer -= dt
            if self.slow_motion_timer <= 0:
                self.slow_motion_active = False
        effective_dt = dt * (0.5 if self.slow_motion_active else 1)
        # Atualiza mísseis inimigos
        for missile in self.enemy_missiles[:]:
            missile.move(effective_dt)
            self.check_city_collision(missile)
            self.update_warnings(missile)
        # Atualiza interceptores
        for missile in self.interceptor_missiles[:]:
            missile.move(dt)
            if self.distance(missile.pos, missile.target) < 10 or (missile.life_time is not None and missile.life_time <= 0):
                self.detonate_interceptor(missile)
        # Verifica colisão entre interceptores e aviões
        for airplane in self.airplanes[:]:
            for interceptor in self.interceptor_missiles[:]:
                if self.distance(airplane.pos, interceptor.pos) < 30:
                    explosion = Explosion(center=airplane.pos, explosion_range=INTERCEPTOR_EXPLOSION_RANGE)
                    self.explosions.append(explosion)
                    self.add_widget(explosion)
                    self.remove_missile(interceptor)
                    if airplane in self.airplanes:
                        self.remove_widget(airplane)
                        self.airplanes.remove(airplane)
                    break
        # Atualiza bombas
        for bomb in self.bombs[:]:
            bomb.move(dt)
            # Se algum interceptor interceptar a bomba
            for interceptor in self.interceptor_missiles[:]:
                if self.distance(bomb.pos, interceptor.pos) < 15:
                    explosion = Explosion(center=bomb.pos, explosion_range=BOMB_EXPLOSION_RANGE)
                    self.explosions.append(explosion)
                    self.add_widget(explosion)
                    self.score += 1
                    self.score_label.update_score(self.score)
                    self.remove_missile(interceptor)
                    if bomb in self.bombs:
                        self.remove_widget(bomb)
                        self.bombs.remove(bomb)
                    break
            # Se a bomba atingir seu alvo (a cidade escolhida)
            if self.distance(bomb.pos, bomb.target) < 20:
                explosion = Explosion(center=bomb.pos, explosion_range=BOMB_EXPLOSION_RANGE)
                self.explosions.append(explosion)
                self.add_widget(explosion)
                for city in self.cities[:]:
                    if self.distance(bomb.pos, city.pos) < BOMB_EXPLOSION_RANGE:
                        city.lives -= 1
                        if city.lives <= 0:
                            self.remove_widget(city)
                            self.cities.remove(city)
                self.remove_widget(bomb)
                if bomb in self.bombs:
                    self.bombs.remove(bomb)
        # Atualiza explosões
        for explosion in self.explosions[:]:
            if explosion.update(dt):
                self.remove_widget(explosion)
                self.explosions.remove(explosion)
            else:
                self.check_explosion_impacts(explosion)
        # Atualiza power-ups
        for powerup in self.powerups[:]:
            powerup.move(dt)
            if powerup.pos[1] < 0:
                self.remove_widget(powerup)
                self.powerups.remove(powerup)
        # Atualiza aviões
        for airplane in self.airplanes[:]:
            drop = airplane.move(dt)
            if drop:
                if self.cities:
                    # Escolhe a cidade mais próxima como alvo da bomba
                    target_city = min(self.cities, key=lambda city: self.distance(airplane.pos, city.pos))
                    bomb = Bomb(pos=(airplane.pos[0]+25, airplane.pos[1]), target=target_city.pos)
                    self.bombs.append(bomb)
                    self.add_widget(bomb)
                airplane.bomb_timer = BOMB_DROP_INTERVAL
            if airplane.pos[0] > Window.width+50:
                self.remove_widget(airplane)
                self.airplanes.remove(airplane)
        self.check_game_over()
    def check_city_collision(self, missile):
        for city in self.cities[:]:
            if self.distance(missile.pos, city.pos) < CITY_RADIUS + MISSILE_RADIUS_ENEMY:
                self.create_city_explosion(city.pos)
                city.lives -= 1
                if city.lives <= 0:
                    self.remove_widget(city)
                    self.cities.remove(city)
                self.remove_missile(missile)
                break
    def create_city_explosion(self, pos):
        explosion = Explosion(center=pos)
        self.explosions.append(explosion)
        self.add_widget(explosion)
    def update_warnings(self, missile):
        warning_needed = any(self.distance(missile.pos, city.pos) < WARNING_DISTANCE for city in self.cities)
        if warning_needed and missile not in self.warnings:
            self.add_warning(missile)
        elif not warning_needed and missile in self.warnings:
            self.remove_warning(missile)
        elif missile in self.warnings:
            self.warnings[missile].update_pos()
    def add_warning(self, missile):
        warning = WarningIndicator(missile)
        self.warnings[missile] = warning
        self.add_widget(warning)
    def remove_warning(self, missile):
        if missile in self.warnings:
            self.remove_widget(self.warnings[missile])
            del self.warnings[missile]
    def detonate_interceptor(self, missile):
        explosion = Explosion(center=missile.pos, explosion_range=INTERCEPTOR_EXPLOSION_RANGE)
        self.explosions.append(explosion)
        self.add_widget(explosion)
        self.remove_missile(missile)
    def check_explosion_impacts(self, explosion):
        for enemy in self.enemy_missiles[:]:
            if self.distance(enemy.pos, explosion.center_point) < explosion.radius:
                self.score += 1
                self.score_label.update_score(self.score)
                self.remove_missile(enemy)
    def remove_missile(self, missile):
        if missile in self.enemy_missiles:
            self.enemy_missiles.remove(missile)
        elif missile in self.interceptor_missiles:
            self.interceptor_missiles.remove(missile)
        self.remove_widget(missile)
        if missile in self.warnings:
            self.remove_warning(missile)
    def check_game_over(self):
        if not self.cities and not hasattr(self, 'game_over_label'):
            self.game_over_label = GameOverLabel()
            self.add_widget(self.game_over_label)
    def distance(self, pos1, pos2):
        return math.hypot(pos1[0]-pos2[0], pos1[1]-pos2[1])

# ===== APLICAÇÃO =====
class MissileCommandApp(App):
    def build(self):
        Window.size = (1080, 2200)
        return MissileCommandGame()

if __name__ == '__main__':
    MissileCommandApp().run()
