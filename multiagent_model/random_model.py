import mesa
import heapq
import random
class Wall:
    def __init__(self, unique_id):
        self.unique_id = unique_id
class Door:
    def __init__(self, unique_id, state='closed'):
        self.unique_id = unique_id
        self.state = state
        self.destroyed = False
class Victim(mesa.Agent):
    def __init__(self, unique_id, model, is_revealed=False):
        super().__init__(model)
        self.unique_id = unique_id
        self.is_revealed = is_revealed
class POI(mesa.Agent):
    def __init__(self, unique_id, model, content_type='unknown'):
        super().__init__(model)
        self.unique_id = unique_id
        self.content_type = content_type
        self.is_revealed = False
class Fire:
    def __init__(self, unique_id, pos):
        self.unique_id = unique_id
        self.pos = pos
class Smoke:
    def __init__(self, unique_id, pos):
        self.unique_id = unique_id
        self.pos = pos
class Sign:
    def __init__(self, unique_id, pos):
        self.unique_id = unique_id
        self.pos = pos
class RandomFirefighterAgent(mesa.Agent):
    def __init__(self, unique_id, model):
        super().__init__(model)
        self.unique_id = unique_id
        self.action_points = 4
        self.saved_ap = 0
        self.is_carrying_victim = False
        self.is_knocked_down = False
        self.turn_completed = False
        self.verbose = model.verbose
    def step(self):
        if self.is_knocked_down:
            self.is_knocked_down = False
            self.action_points = 4
            return
        if self.action_points > 0:
            self.random_action()
        else:
            self.turn_completed = True
    def random_action(self):
        actions = [
            self.random_move,
            self.random_extinguish,
            self.random_carry_victim,
            self.random_drop_victim,
            self.random_open_close_door,
            self.random_chop_wall,
            self.end_turn_voluntarily
        ]
        action = random.choice(actions)
        action()
        if self.is_carrying_victim:
            self.rescue_victim_at_exit()
    def random_move(self):
        if self.action_points < 1:
            return False
        possible_moves = self.model.grid.get_neighborhood(
            self.pos, moore=False, include_center=False)
        possible_moves = list(possible_moves)
        random.shuffle(possible_moves)
        for move in possible_moves:
            if not self.model.grid.out_of_bounds(move):
                cell_contents = self.model.grid.get_cell_list_contents([move])
                has_firefighter = any(isinstance(obj, RandomFirefighterAgent) for obj in cell_contents)
                if not has_firefighter:
                    move_tuple = tuple(sorted((self.pos, move)))
                    if move_tuple in self.model.walls:
                        if move_tuple in self.model.wall_damage and self.model.wall_damage[move_tuple] >= 2:
                            pass
                        else:
                            continue
                    if move_tuple in self.model.doors:
                        door_state = self.model.doors[move_tuple]['state']
                        if door_state == 'closed':
                            if random.random() < 0.5 and self.action_points >= 2:
                                self.model.doors[move_tuple]['state'] = 'open'
                                self.action_points -= 1
                            else:
                                continue
                        elif door_state == 'destroyed':
                            continue
                    has_fire = move in self.model.fires
                    base_cost = 2 if has_fire else 1
                    if self.is_carrying_victim:
                        cost = base_cost * 2
                    else:
                        cost = base_cost
                    if self.action_points >= cost:
                        if has_fire and self.is_carrying_victim:
                            continue
                        self.model.grid.move_agent(self, move)
                        self.action_points -= cost
                        self.reveal_poi_if_present()
                        return True
        return False
    def random_extinguish(self):
        if self.action_points < 1:
            return False
        possible_targets = self.model.grid.get_neighborhood(
            self.pos, moore=False, include_center=True)
        possible_targets = list(possible_targets)
        random.shuffle(possible_targets)
        for target_pos in possible_targets:
            # Check if there's a wall between the firefighter and the target
            if target_pos != self.pos:  # Skip check for current position
                move_tuple = tuple(sorted((self.pos, target_pos)))
                if move_tuple in self.model.walls:
                    if move_tuple not in self.model.wall_damage or self.model.wall_damage[move_tuple] < 2:
                        # Wall exists and is not destroyed, can't extinguish through it
                        continue
            
            if target_pos in self.model.fires:
                if self.action_points >= 2:
                    del self.model.fires[target_pos]
                    self.action_points -= 2
                    return True
                elif self.action_points >= 1:
                    del self.model.fires[target_pos]
                    smoke = Smoke(f"smoke_{self.model.smoke_counter}", target_pos)
                    self.model.smoke[target_pos] = smoke
                    self.model.smoke_counter += 1
                    self.action_points -= 1
                    return True
            elif target_pos in self.model.smoke:
                del self.model.smoke[target_pos]
                self.action_points -= 1
                return True
        return False
    def random_carry_victim(self):
        if self.action_points < 1 or self.is_carrying_victim:
            return False
        cell_contents = self.model.grid.get_cell_list_contents([self.pos])
        victims_in_cell = [obj for obj in cell_contents if isinstance(obj, Victim) and obj.is_revealed]
        if victims_in_cell:
            victim = victims_in_cell[0]
            self.model.grid.remove_agent(victim)
            self.model.deregister_agent(victim)
            self.is_carrying_victim = True
            self.action_points -= 1
            return True
        return False
    def random_drop_victim(self):
        if not self.is_carrying_victim or self.action_points < 1:
            return False
        possible_drops = self.model.grid.get_neighborhood(
            self.pos, moore=False, include_center=False)
        possible_drops = list(possible_drops)
        random.shuffle(possible_drops)
        for drop_pos in possible_drops:
            if not self.model.grid.out_of_bounds(drop_pos):
                victim = Victim(f"dropped_victim_{self.model.victim_counter}", self.model, is_revealed=True)
                self.model.grid.place_agent(victim, drop_pos)
                self.model.register_agent(victim)
                self.model.victim_counter += 1
                self.model.total_victims_on_board += 1
                self.is_carrying_victim = False
                self.action_points -= 1
                return True
        return False
    def random_open_close_door(self):
        if self.action_points < 1:
            return False
        door_keys = []
        for door_pos, door_info in self.model.doors.items():
            if self.pos in door_pos:
                door_keys.append(door_pos)
        if door_keys:
            door_key = random.choice(door_keys)
            current_state = self.model.doors[door_key]['state']
            if current_state == 'closed':
                new_state = 'open'
            elif current_state == 'open':
                new_state = 'closed'
            else:
                return False
            self.model.doors[door_key]['state'] = new_state
            self.action_points -= 1
            return True
        return False
    def random_chop_wall(self):
        if self.action_points < 2:
            return False
        adjacent_walls = []
        for wall in self.model.walls:
            for segment in wall:
                if self.model.manhattan_distance(self.pos, segment) == 1:
                    adjacent_walls.append(wall)
        if adjacent_walls:
            wall_key = random.choice(adjacent_walls)
            if wall_key not in self.model.wall_damage:
                self.model.wall_damage[wall_key] = 0
            if self.model.wall_damage[wall_key] < 2:
                self.model.wall_damage[wall_key] += 1
                self.model.damage_cubes += 1
                self.action_points -= 2
                state_str = ['saludable', 'dañado', 'destruido'][self.model.wall_damage[wall_key]]
                return True
        return False
    def end_turn_voluntarily(self):
        if not self.turn_completed and self.action_points > 0:
            if random.random() < 0.2:
                self.end_turn()
                return True
        return False
    def end_turn(self):
        if self.action_points > 0:
            potential_saved = self.saved_ap + self.action_points
            if potential_saved <= 4:
                self.saved_ap = potential_saved
            else:
                self.saved_ap = 4
                wasted_ap = potential_saved - 4
        self.action_points = 0
        self.turn_completed = True
    def reveal_poi_if_present(self):
        cell_contents = self.model.grid.get_cell_list_contents([self.pos])
        pois_in_cell = [obj for obj in cell_contents if isinstance(obj, POI) and not obj.is_revealed]
        for poi in pois_in_cell:
            poi.is_revealed = True
            if poi.content_type == 'victim':
                victim = Victim(f"revealed_victim_{poi.unique_id}", self.model, is_revealed=True)
                self.model.grid.place_agent(victim, poi.pos)
                self.model.register_agent(victim)
                self.model.total_victims_on_board += 1
            else:
                pass
            self.model.grid.remove_agent(poi)
            self.model.deregister_agent(poi)
    def rescue_victim_at_exit(self):
        x, y = self.pos
        is_outside = (y == 0 or y == 9 or x == 0 or x == 7)
        if self.is_carrying_victim and is_outside:
            self.is_carrying_victim = False
            self.model.victims_rescued += 1
            return True
        return False
class RandomFireRescueModel(mesa.Model):
    def __init__(self, num_agents=1, verbose=False):
        super().__init__()
        self.num_agents = num_agents
        self.verbose = verbose
        self.building_width = 8
        self.building_height = 10
        self.current_step = 0
        self.fires = {}
        self.smoke = {}
        self.walls = set()
        self.doors = {}
        self.signs = {}
        self.wall_damage = {}
        self.damage_cubes = 0
        self.MAX_DAMAGE_CUBES = 24
        self.grid = mesa.space.MultiGrid(self.building_width, self.building_height, True)
        self.schedule = mesa.time.RandomActivation(self)
        self.all_agents = []
        self.victims_rescued = 0
        self.victims_lost = 0
        self.total_victims_on_board = 0
        self.total_poi = 0
        self.fire_counter = 1
        self.smoke_counter = 1
        self.sign_counter = 1
        self.victim_counter = 1
        self.poi_counter = 1
        self.agent_counter = 1
        self.game_over = False
        self.game_outcome = None
        self._create_perimeter_walls()
        self._create_interior_walls()
        self._create_door_at_position((0, 4))
        self._create_door_at_position((3, 0))
        self._create_door_at_position((7, 4))
        self._create_door_at_position((3, 9))
        self._create_interior_doors()
        poi_positions = [(2, 2), (5, 2), (2, 7), (5, 7)]
        for pos in poi_positions:
            self._create_poi(pos)
        self._add_initial_fire_and_smoke()
        self._add_firefighters(num_agents)
    def register_agent(self, agent):
        if agent not in self.all_agents:
            self.all_agents.append(agent)
    def deregister_agent(self, agent):
        if agent in self.all_agents:
            self.all_agents.remove(agent)
    def step(self):
        self.current_step += 1
        self.schedule.step()
    def step_firefighter(self):
        firefighter_agents = [agent for agent in self.all_agents
                             if isinstance(agent, RandomFirefighterAgent)]
        if all(agent.is_knocked_down for agent in firefighter_agents):
            return
        active_agents = [agent for agent in firefighter_agents
                         if not agent.turn_completed and not agent.is_knocked_down]
        if active_agents:
            active_agent = active_agents[0]
            active_agent.step()
        else:
            for agent in firefighter_agents:
                agent.turn_completed = False
                agent.action_points = 4 + agent.saved_ap
                agent.saved_ap = 0
            if firefighter_agents:
                firefighter_agents[0].step()
    def step_fire(self):
        self.advance_fire_phase()
    def step_complete_turn(self):
        firefighter_agents = [agent for agent in self.all_agents
                             if isinstance(agent, RandomFirefighterAgent)]
        all_turns_completed = False
        while not all_turns_completed:
            self.step_firefighter()
            all_turns_completed = all(agent.turn_completed for agent in firefighter_agents)
        self.step_fire()
        self.check_game_outcome()
    def _create_perimeter_walls(self):
        for j in range(self.building_height):
            wall = tuple(sorted(((0, j), (1, j))))
            self.walls.add(wall)
        for j in range(self.building_height):
            wall = tuple(sorted(((6, j), (7, j))))
            self.walls.add(wall)
        for i in range(self.building_width):
            wall = tuple(sorted(((i, 0), (i, 1))))
            self.walls.add(wall)
        for i in range(self.building_width):
            wall = tuple(sorted(((i, 8), (i, 9))))
            self.walls.add(wall)
    def _create_interior_walls(self):
        wall_segments = [
            ((2,1),(3,1)), ((2,2),(3,2)), ((2,3),(3,3)), ((2,4),(3,4)),
            ((2,5),(3,5)), ((2,6),(3,6)), ((2,7),(3,7)), ((2,8),(3,8)),
            ((4,3),(5,3)), ((4,4),(5,4)), ((4,5),(5,5)), ((4,6),(5,6)),
            ((4,7),(5,7)), ((4,8),(5,8)),
            ((3,2),(3,3)), ((4,2), (4,3)),
            ((5,3), (5,4)), ((6,3), (6,4)),
            ((1,5),(1,6)),((2,5),(2,6)),
            ((5,5),(5,6)),((6,5),(6,6)),
            ((1,7),(1,8)),((2,7),(2,8)),
            ((3,6),(3,7)),((4,6),(4,7))
        ]
        for wall in wall_segments:
            wall_tuple = tuple(sorted(wall))
            self.walls.add(wall_tuple)
    def _create_door_at_position(self, pos):
        x, y = pos
        wall_to_remove = None
        if x == 0 and 0 <= y < self.building_height:
            wall_to_remove = tuple(sorted(((0, y), (1, y))))
        elif x == 7 and 0 <= y < self.building_height:
            wall_to_remove = tuple(sorted(((6, y), (7, y))))
        elif y == 0 and 0 <= x < self.building_width:
            wall_to_remove = tuple(sorted(((x, 0), (x, 1))))
        elif y == 9 and 0 <= x < self.building_width:
            wall_to_remove = tuple(sorted(((x, 8), (x, 9))))
        if wall_to_remove and wall_to_remove in self.walls:
            self.walls.remove(wall_to_remove)
            self.doors[wall_to_remove] = {'state': 'open'}
            sign = Sign(f"sign_{self.sign_counter}", pos)
            self.signs[pos] = sign
            self.sign_counter += 1
    def _create_interior_doors(self):
        door_segments = [
            ((3, 2), (3, 3)),
            ((5, 3), (5, 4)),
            ((2, 5), (2, 6)),
            ((4, 6), (4, 7))
        ]
        for segment in door_segments:
            wall_tuple = tuple(sorted(segment))
            if wall_tuple in self.walls:
                self.walls.remove(wall_tuple)
                self.doors[wall_tuple] = {'state': 'closed'}
                sign_pos = segment[0]
                sign = Sign(f"sign_{self.sign_counter}", sign_pos)
                self.signs[sign_pos] = sign
                self.sign_counter += 1
    def _create_poi(self, pos):
        content_type = random.choice(['victim', 'false_alarm'])
        poi = POI(f"poi_{self.poi_counter}", self, content_type)
        self.grid.place_agent(poi, pos)
        self.register_agent(poi)
        self.poi_counter += 1
        self.total_poi += 1
    def _add_initial_fire_and_smoke(self):
        fire_pos = (4, 4)
        fire = Fire(f"fire_{self.fire_counter}", fire_pos)
        self.fires[fire_pos] = fire
        self.fire_counter += 1
        smoke_pos = (3, 4)
        smoke = Smoke(f"smoke_{self.smoke_counter}", smoke_pos)
        self.smoke[smoke_pos] = smoke
        self.smoke_counter += 1
    def _add_firefighters(self, num_agents):
        entry_points = [(0, 4), (3, 0), (7, 4), (3, 9)]
        for i in range(num_agents):
            pos = random.choice(entry_points)
            agent = RandomFirefighterAgent(f"bombero_{self.agent_counter}", self)
            self.grid.place_agent(agent, pos)
            self.schedule.add(agent)
            self.register_agent(agent)
            self.agent_counter += 1
    def manhattan_distance(self, pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
    def is_valid_move(self, pos1, pos2):
        if self.grid.out_of_bounds(pos2):
            return False
        move_tuple = tuple(sorted((pos1, pos2)))
        if move_tuple in self.walls:
            if move_tuple in self.wall_damage and self.wall_damage[move_tuple] >= 2:
                pass
            else:
                return False
        return True
    def advance_fire_phase(self):
        if self.game_over:
            return
        red_die = random.randint(1, 6)
        black_die = random.randint(1, 8)
        target_pos = (black_die - 1, red_die - 1)
        if target_pos in self.fires:
            self.handle_explosion(target_pos)
        elif target_pos in self.smoke:
            del self.smoke[target_pos]
            fire = Fire(f"fire_{self.fire_counter}", target_pos)
            self.fires[target_pos] = fire
            self.fire_counter += 1
        else:
            smoke = Smoke(f"smoke_{self.smoke_counter}", target_pos)
            self.smoke[target_pos] = smoke
            self.smoke_counter += 1
    def handle_explosion(self, explosion_center):
        self.check_firefighter_damage(explosion_center)
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        for dx, dy in directions:
            current_pos = explosion_center
            while True:
                next_pos = (current_pos[0] + dx, current_pos[1] + dy)
                if self.grid.out_of_bounds(next_pos):
                    break
                wall_segment = tuple(sorted((current_pos, next_pos)))
                if wall_segment in self.walls:
                    if wall_segment not in self.wall_damage:
                        self.wall_damage[wall_segment] = 0
                    if self.wall_damage[wall_segment] < 2:
                        self.wall_damage[wall_segment] += 1
                        self.damage_cubes += 1
                        state = ['saludable', 'dañado', 'destruido'][self.wall_damage[wall_segment]]
                    if self.wall_damage[wall_segment] < 2:
                        break
                if wall_segment in self.doors:
                    door_state = self.doors[wall_segment]['state']
                    if door_state == 'closed':
                        self.doors[wall_segment]['state'] = 'destroyed'
                        break
                if next_pos in self.smoke:
                    del self.smoke[next_pos]
                if next_pos not in self.fires:
                    fire = Fire(f"fire_{self.fire_counter}", next_pos)
                    self.fires[next_pos] = fire
                    self.fire_counter += 1
                    self.check_firefighter_damage(next_pos)
                current_pos = next_pos
    def check_firefighter_damage(self, pos):
        cell_contents = self.grid.get_cell_list_contents([pos])
        firefighters = [obj for obj in cell_contents if isinstance(obj, RandomFirefighterAgent)]
        for ff in firefighters:
            if not ff.is_knocked_down:
                ff.is_knocked_down = True
                ff.action_points = 0
                ff.turn_completed = True
                if ff.is_carrying_victim:
                    ff.is_carrying_victim = False
                    self.victims_lost += 1
                else:
                    pass
        victims = [obj for obj in cell_contents if isinstance(obj, Victim)]
        for victim in victims:
            self.grid.remove_agent(victim)
            self.deregister_agent(victim)
            self.victims_lost += 1
            self.total_victims_on_board -= 1
    def check_game_outcome(self):
        if self.victims_rescued >= 7:
            self.game_over = True
            self.game_outcome = "win"
        if self.victims_lost >= 4:
            self.game_over = True
            self.game_outcome = "loss"
        if self.damage_cubes >= self.MAX_DAMAGE_CUBES:
            self.game_over = True
            self.game_outcome = "loss"
        return self.game_over
    def get_state(self):
        firefighter_positions = []
        for agent in self.all_agents:
            if isinstance(agent, RandomFirefighterAgent):
                firefighter_positions.append({
                    'id': agent.unique_id,
                    'pos': agent.pos,
                    'carrying_victim': agent.is_carrying_victim,
                    'knocked_down': agent.is_knocked_down,
                    'action_points': agent.action_points,
                    'saved_ap': agent.saved_ap
                })
        victim_positions = []
        for agent in self.all_agents:
            if isinstance(agent, Victim):
                victim_positions.append({
                    'id': agent.unique_id,
                    'pos': agent.pos,
                    'is_revealed': agent.is_revealed
                })
        poi_positions = []
        for agent in self.all_agents:
            if isinstance(agent, POI):
                poi_positions.append({
                    'id': agent.unique_id,
                    'pos': agent.pos,
                    'is_revealed': agent.is_revealed,
                    'content_type': agent.content_type
                })
        fire_positions = [{'pos': pos} for pos in self.fires.keys()]
        smoke_positions = [{'pos': pos} for pos in self.smoke.keys()]
        sign_positions = [{'pos': pos} for pos in self.signs.keys()]
        walls_list = [{'segment': list(segment)} for segment in self.walls]
        doors_list = []
        for segment, info in self.doors.items():
            doors_list.append({
                'segment': list(segment),
                'state': info['state']
            })
        wall_damage_list = []
        for segment, damage in self.wall_damage.items():
            wall_damage_list.append({
                'segment': list(segment),
                'damage': damage
            })
        return {
            'step': self.current_step,
            'firefighters': firefighter_positions,
            'victims': victim_positions,
            'pois': poi_positions,
            'fires': fire_positions,
            'smoke': smoke_positions,
            'signs': sign_positions,
            'walls': walls_list,
            'doors': doors_list,
            'wall_damage': wall_damage_list,
            'victims_rescued': self.victims_rescued,
            'victims_lost': self.victims_lost,
            'total_victims_on_board': self.total_victims_on_board,
            'damage_cubes': self.damage_cubes,
            'max_damage_cubes': self.MAX_DAMAGE_CUBES,
            'game_over': self.game_over,
            'game_outcome': self.game_outcome
        }
