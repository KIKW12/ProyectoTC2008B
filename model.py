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
class FirefighterAgent(mesa.Agent):
    def __init__(self, unique_id, model, strategy='random'):
        super().__init__(model)
        self.unique_id = unique_id
        self.action_points = 4
        self.saved_ap = 0
        self.is_carrying_victim = False
        self.is_knocked_down = False
        self.strategy = strategy
        self.turn_completed = False
        self.last_positions = []
        self.turns_carrying_victim = 0
        self.current_target = None
        self.target_commitment_turns = 0
        self.area_visit_count = {}

    def step(self):
        if self.is_knocked_down:
            self.is_knocked_down = False
            self.action_points = 4
            return
        if self.strategy == 'random':
            self.random_strategy_with_loop_avoidance()
        elif self.strategy == 'improved':
            self.improved_strategy_single_action()
        else:
            self.random_strategy_with_loop_avoidance()


    def move_action(self, new_position):
        if self.model.manhattan_distance(self.pos, new_position) != 1:
            return False
        door_between = None
        move_tuple = tuple(sorted((self.pos, new_position)))
        if move_tuple in self.model.walls:
            if move_tuple not in self.model.wall_damage or self.model.wall_damage[move_tuple] < 2:
                return False
        if move_tuple in self.model.doors:
            door_between = move_tuple
            door_state = self.model.doors[door_between]['state']
            if door_state == 'closed':
                if self.action_points >= 2:
                    self.model.doors[door_between]['state'] = 'open'
                    self.action_points -= 1
                else:
                    return False
        has_fire = new_position in self.model.fires
        has_smoke = new_position in self.model.smoke
        base_cost = 2 if (has_fire or has_smoke) else 1
        cost = base_cost * 2 if self.is_carrying_victim else base_cost
        if has_fire and self.action_points - cost <= 0:
            return False
        if self.action_points >= cost:
            if has_fire and self.is_carrying_victim:
                return False
            cell_contents = self.model.grid.get_cell_list_contents([new_position])
            for obj in cell_contents:
                if isinstance(obj, FirefighterAgent):
                    return False
            self.last_positions.append(self.pos)
            if len(self.last_positions) > 4:
                self.last_positions.pop(0)
            if len(self.last_positions) >= 3:
                if len(self.last_positions) >= 3 and self.last_positions[-1] == self.last_positions[-3]:
                    return False
                if (len(self.last_positions) >= 4 and
                    self.last_positions[-1] == self.last_positions[-3] and
                    self.last_positions[-2] == self.last_positions[-4]):
                    return False
                if (len(self.last_positions) >= 3 and
                    self.last_positions[-1] == self.last_positions[-3] and
                    self.last_positions[-2] != self.last_positions[-1] and
                    new_position == self.last_positions[-2]):
                    return False
            self.model.grid.move_agent(self, new_position)
            self.action_points -= cost
            if len(self.last_positions) >= 2:
                if new_position not in self.last_positions[-2:]:
                    self.last_positions = [self.pos]
                else:
                    if len(self.last_positions) > 3:
                        self.last_positions = self.last_positions[-3:]
            self.reveal_poi_if_present()
            return True
        else:
            return False
        
    def get_movement_cost(self, target_pos):
        if not self.model.grid.out_of_bounds(target_pos):
            has_fire = target_pos in self.model.fires
            has_smoke = target_pos in self.model.smoke
            base_cost = 2 if (has_fire or has_smoke) else 1
            if self.is_carrying_victim:
                return base_cost * 2
            else:
                return base_cost
        return float('inf')
    
    def extinguish_action(self, target_pos):
        if self.model.manhattan_distance(self.pos, target_pos) > 1:
            return False
        
        # Check if there's a wall between the firefighter and the target
        move_tuple = tuple(sorted((self.pos, target_pos)))
        if move_tuple in self.model.walls:
            if move_tuple not in self.model.wall_damage or self.model.wall_damage[move_tuple] < 2:
                # Wall exists and is not destroyed, can't extinguish through it
                return False
        
        # Check if there's a closed door between the firefighter and the target
        if move_tuple in self.model.doors:
            door_state = self.model.doors[move_tuple]['state']
            if door_state == 'closed':
                # Door is closed, can't extinguish through it
                return False
        
        if self.action_points >= 1:
            action_taken = False
            if target_pos in self.model.fires:
                if self.action_points >= 2:
                    del self.model.fires[target_pos]
                    self.action_points -= 2
                    action_taken = True
                else:
                    del self.model.fires[target_pos]
                    smoke = Smoke(f"smoke_{self.model.smoke_counter}", target_pos)
                    self.model.smoke[target_pos] = smoke
                    self.model.smoke_counter += 1
                    self.action_points -= 1
                    action_taken = True
            elif target_pos in self.model.smoke and not action_taken:
                del self.model.smoke[target_pos]
                self.action_points -= 1
                action_taken = True
            return action_taken
        return False
    
    def chop_wall_action(self, wall_segment):
        if self.action_points >= 2:
            wall_key = None
            for wall in self.model.walls:
                if wall_segment in wall:
                    wall_key = wall
                    break
            if wall_key:
                if wall_key not in self.model.wall_damage:
                    self.model.wall_damage[wall_key] = 0
                if self.model.wall_damage[wall_key] < 2:
                    self.model.wall_damage[wall_key] += 1
                    self.model.damage_cubes += 1
                    self.action_points -= 2
                    state_str = ['saludable', 'dañado', 'destruido'][self.model.wall_damage[wall_key]]
                    return True
                else:
                    return False
        return False
    
    def open_close_door_action(self, door_position):
        if self.action_points >= 1:
            door_key = None
            for door_pos, door_info in self.model.doors.items():
                if self.pos in door_pos or door_position in door_pos:
                    door_key = door_pos
                    break
            if door_key:
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
    
    def carry_victim_action(self):
        if not self.is_carrying_victim:
            cell_contents = self.model.grid.get_cell_list_contents([self.pos])
            victims_in_cell = [obj for obj in cell_contents if isinstance(obj, Victim) and obj.is_revealed]
            if victims_in_cell:
                victim = victims_in_cell[0]
                self.model.grid.remove_agent(victim)
                self.model.deregister_agent(victim)
                self.is_carrying_victim = True
                self.turns_carrying_victim = 0
                self.action_points -= 2
                return True
        return False
    
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
                pass  # No special action for non-victim POIs
            self.model.grid.remove_agent(poi)
            self.model.deregister_agent(poi)

        self.carry_victim_action()

    def rescue_victim_at_exit(self):
        x, y = self.pos
        is_outside = (y == 0 or y == 9 or x == 0 or x == 7)
        if self.is_carrying_victim and is_outside and self.action_points >= 1:
            self.is_carrying_victim = False
            self.turns_carrying_victim = 0
            self.area_visit_count = {}
            self.model.victims_rescued += 1
            self.action_points -= 1
            return True
        return False
    
    def end_turn(self):
        if self.action_points > 0:
            self.saved_ap = 0
        self.action_points = 0
        self.turn_completed = True

    def random_strategy_with_loop_avoidance(self):
        if self.action_points <= 0:
            return False
        if self.rescue_victim_at_exit():
            return True
        possible_moves = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False)
        valid_moves = [p for p in possible_moves if self.model.is_valid_move(self.pos, p)]
        affordable_moves = []
        for move in valid_moves:
            cost = self.get_movement_cost(move)
            if self.action_points >= cost:
                if not self.would_create_loop(move):
                    cell_contents = self.model.grid.get_cell_list_contents([move])
                    has_firefighter = any(isinstance(obj, FirefighterAgent) for obj in cell_contents)
                    if not has_firefighter:
                        affordable_moves.append(move)
        if affordable_moves:
            new_position = self.model.random.choice(affordable_moves)
            if self.move_action(new_position):
                return True
        fallback_moves = []
        for move in valid_moves:
            cost = self.get_movement_cost(move)
            if self.action_points >= cost:
                cell_contents = self.model.grid.get_cell_list_contents([move])
                has_firefighter = any(isinstance(obj, FirefighterAgent) for obj in cell_contents)
                if not has_firefighter:
                    fallback_moves.append(move)
        if fallback_moves:
            new_position = self.model.random.choice(fallback_moves)
            if self.move_action(new_position):
                return True
        if self.carry_victim_action():
            return True
        
        adjacent_positions = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=True)
        for pos in adjacent_positions:
            if self.extinguish_action(pos):
                return True
        if self.open_close_door_action(self.pos):
            return True
        adjacent_walls = []
        for wall in self.model.walls:
            for segment in wall:
                if self.model.manhattan_distance(self.pos, segment) == 1:
                    adjacent_walls.append(segment)
        if adjacent_walls and self.chop_wall_action(adjacent_walls[0]):
            return True
        return False
    
    def would_create_loop(self, new_position):
        if len(self.last_positions) < 2:
            return False
        if len(self.last_positions) >= 2 and new_position == self.last_positions[-2]:
            return True
        if len(self.last_positions) >= 5:
            if (new_position == self.last_positions[-3] and
                self.last_positions[-1] == self.last_positions[-4] and
                self.last_positions[-2] == self.last_positions[-5]):
                return True
        if len(self.last_positions) >= 4:
            recent_positions = self.last_positions[-4:]
            position_count = recent_positions.count(new_position)
            if position_count >= 2:
                return True
        if self.is_carrying_victim and len(self.last_positions) >= 3:
            if new_position in self.last_positions[-3:]:
                return True
        return False
    
    def improved_strategy_single_action(self):
        if self.action_points <= 0:
            self.turn_completed = True
            return False
        if self.rescue_victim_at_exit():
            return True
        if self.is_carrying_victim:
            for pos in self.model.grid.get_neighborhood(self.pos, moore=False, include_center=True):
                if pos in self.model.fires or pos in self.model.smoke:
                    if self.extinguish_action(pos):
                        return True
            exits = [(0, y) for y in range(10)] + [(7, y) for y in range(10)] + \
                    [(x, 0) for x in range(8)] + [(x, 9) for x in range(8)]
            valid_exits = [pos for pos in exits if not self.model.grid.out_of_bounds(pos)]
            valid_exits.sort(key=lambda e: self.model.manhattan_distance(self.pos, e))
            for exit_pos in valid_exits[:6]:
                path, _ = self.model.dijkstra(self.pos, exit_pos, self)
                if path and len(path) > 1:
                    next_pos = path[1]
                    move_cost = self.get_movement_cost(next_pos)
                    if self.action_points >= move_cost and self.move_action(next_pos):
                        return True
            for adj in self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False):
                door_between = tuple(sorted((self.pos, adj)))
                if door_between in self.model.doors and self.model.doors[door_between]['state'] == 'closed':
                    if self.open_close_door_action(adj):
                        return True
            self.turn_completed = True
            self.saved_ap = self.action_points
            self.action_points = 0
            return False
        
        if self.reveal_poi_if_present():
            return True
        
        for pos in self.model.grid.get_neighborhood(self.pos, moore=False, include_center=True):
            if self.extinguish_action(pos):
                return True
        victims = [a for a in self.model.agents if isinstance(a, Victim) and a.is_revealed and hasattr(a, 'pos') and a.pos is not None]
        pois = [a for a in self.model.agents if isinstance(a, POI) and not a.is_revealed and hasattr(a, 'pos') and a.pos is not None]
        targets = victims if victims else pois
        if targets:
            targets.sort(key=lambda t: self.model.manhattan_distance(self.pos, t.pos))
            target = targets[0]
            path, _ = self.model.dijkstra(self.pos, target.pos, self)
            if path and len(path) > 1:
                next_pos = path[1]
                move_cost = self.get_movement_cost(next_pos)
                if self.action_points >= move_cost and self.move_action(next_pos):
                    return True
            for adj in self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False):
                door_between = tuple(sorted((self.pos, adj)))
                if door_between in self.model.doors and self.model.doors[door_between]['state'] == 'closed':
                    if self.model.manhattan_distance(adj, target.pos) < self.model.manhattan_distance(self.pos, target.pos):
                        if self.open_close_door_action(adj):
                            return True
        if self.action_points <= 4:
            self.turn_completed = True
            self.saved_ap = self.action_points
            self.action_points = 0
            return False
        possible_moves = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False)
        candidates = []
        for mv in possible_moves:
            if self.model.is_valid_move(self.pos, mv) and not self.would_create_loop(mv):
                cost = self.get_movement_cost(mv)
                if self.action_points >= cost:
                    candidates.append((mv, cost))
        if candidates:
            candidates.sort(key=lambda mc: (mc[0] in self.model.fires, mc[0] in self.model.smoke))
            mv, _ = candidates[0]
            if self.move_action(mv):
                return True
        self.turn_completed = True
        self.saved_ap = self.action_points
        self.action_points = 0
        return False
    
    def start_new_turn(self):
        self.action_points = 4
        self.saved_ap = 0
        self.turn_completed = False
        self.last_positions = []
        if not self.is_carrying_victim:
            self.turns_carrying_victim = 0
class FireRescueModel(mesa.Model):
    def __init__(self, width=8, height=10, num_agents=1, strategy='improved'):
        super().__init__()
        self.width, self.height = width, height
        self.grid = mesa.space.MultiGrid(width, height, torus=False)
        self.building_width = 8
        self.building_height = 10
        self.interior_width = 6
        self.interior_height = 8
        num_agents = min(num_agents, 6)
        self.advance_fire = False
        self.victims_rescued = 0
        self.victims_lost = 0
        self.damage_cubes = 0
        self.total_victims_on_board = 0
        self.total_victims_available = 10
        self.total_false_alarms_available = 5
        self.total_poi_markers = self.total_victims_available + self.total_false_alarms_available
        self.poi_placed = 0
        self.WIN_VICTIMS_NEEDED = 7
        self.LOSE_VICTIMS_LOST = 4
        self.MAX_DAMAGE_CUBES = 24
        self.walls = set()
        self.doors = {}
        self.wall_damage = {}
        self.fires = {}
        self.smoke = {}
        self.signs = {}
        self.game_over = False
        self.game_won = False
        self.fire_counter = 0
        self.smoke_counter = 0
        self.sign_counter = 0
        self.poi_counter = 0
        self.victim_counter = 0
        self._load_scenario_from_file("final.txt")
        starting_positions = [(4, 0), (7, 6), (0, 3), (3, 9)]
        for i in range(num_agents):
            agent = FirefighterAgent(f"firefighter_{i+1}", self, strategy)
            spot = starting_positions[i % len(starting_positions)]
            self.register_agent(agent)
            self.grid.place_agent(agent, spot)
    def _load_scenario_from_file(self, filename):
        self._create_perimeter_walls()
        self._create_manual_interior_walls()
        door_positions = [
            (0, 3), (4, 0), (3, 9), (7,6)
        ]
        for x, y in door_positions:
            self._create_door_at_position((x, y))
        interior_doors = [
            ((1, 5), (1, 6)),
            ((1, 7), (1, 8)),
            ((2, 4), (3, 4)),
            ((3, 6), (3, 7)),
            ((4, 8), (5, 8)),
            ((5, 5), (5, 6)),
            ((6, 3), (6, 4)),
            ((4, 2), (4, 3))
        ]
        for wall_segment in interior_doors:
            self._create_interior_door(wall_segment)
        poi_positions = [
            (2, 1),
            (2, 8),
            (5, 4)
        ]
        poi_types = ['false_alarm', 'victim', 'victim']
        for i, pos in enumerate(poi_positions):
            if 1 <= pos[0] <= 6 and 1 <= pos[1] <= 8:
                content_type = poi_types[i]
                poi = POI(f"poi_{self.poi_counter}", self, content_type)
                self.grid.place_agent(poi, pos)
                self.register_agent(poi)
                self.poi_counter += 1
                self.poi_placed += 1
            else:
                pass
        fire_positions = [
            (4, 2), (5, 2), (4,3), (5,3),
            (3,4), (4,4), (4,5), (1,6), (2,6), (2,7)
        ]
        for pos in fire_positions:
            if 1 <= pos[0] <= 6 and 1 <= pos[1] <= 8:
                fire = Fire(f"fire_{self.fire_counter}", pos)
                self.fires[pos] = fire
                self.fire_counter += 1
            else:
                pass
    def _create_perimeter_walls(self):
        for i in range(self.building_width):
            wall = tuple(sorted(((i, 0), (i, 1))))
            if wall != ((0, 0), (1, 0)) and wall != ((0, 0), (0, 1)) and wall != ((6, 0), (7, 0)):
                self.walls.add(wall)
        for i in range(self.building_width):
            wall = tuple(sorted(((i, 8), (i, 9))))
            if wall != ((0, 8), (0, 9)) and wall != ((6, 8), (7, 9)):
                self.walls.add(wall)
        for j in range(self.building_height):
            wall = tuple(sorted(((0, j), (1, j))))
            if wall != ((0, 0), (1, 0)) and wall != ((0, 9), (1, 9)):
                self.walls.add(wall)
        for j in range(self.building_height):
            wall = tuple(sorted(((6, j), (7, j))))
            if wall != ((6, 0), (7, 0)):
                self.walls.add(wall)
        wall_to_remove1 = ((7, 0), (7, 1))
        if wall_to_remove1 in self.walls:
            self.walls.remove(wall_to_remove1)
        wall_to_remove2 = ((7, 8), (7, 9))
        if wall_to_remove2 in self.walls:
            self.walls.remove(wall_to_remove2)
        wall_to_remove3 = ((6, 9), (7, 9))
        if wall_to_remove3 in self.walls:
            self.walls.remove(wall_to_remove3)
    def _create_manual_interior_walls(self):
        """Create interior walls manually based on the board game layout.
        NOTE: This method is kept for future reference when implementing interior doors.
        The wall segments here can be used as a reference for where interior doors should be placed.
        """
        walls_created = 0
        wall_segments = [
            ((2,1),(3,1)), ((2,2),(3,2)), ((2,3),(3,3)), ((2,4),(3,4)), ((2,5),(3,5)), ((2,6),(3,6)), ((2,7),(3,7)), ((2,8),(3,8)),
            ((4,3),(5,3)), ((4,4),(5,4)), ((4,5),(5,5)), ((4,6),(5,6)), ((4,7),(5,7)), ((4,8),(5,8)),
            ((3,2),(3,3)), ((4,2), (4,3)),
            ((5,3), (5,4)), ((6,3), (6,4)),
            ((1,5),(1,6)),((2,5),(2,6)),
            ((5,5),(5,6)),((6,5),(6,6)),
            ((1,7),(1,8)),((2,7),(2,8)),
            ((3,6),(3,7)),((4,6),(4,7)),
        ]
        for wall in wall_segments:
            wall_tuple = tuple(sorted(wall))
            self.walls.add(wall_tuple)
            walls_created += 1
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
            closed_doors = []
            state = 'closed' if pos in closed_doors else 'open'
            self.doors[wall_to_remove] = {'state': state}
            sign = Sign(f"sign_{self.sign_counter}", pos)
            self.signs[pos] = sign
            self.sign_counter += 1
        else:
            pass  # No action needed if wall doesn't exist or can't be removed
            
    def _create_interior_door(self, wall_segment):
        wall_tuple = tuple(sorted(wall_segment))
        if wall_tuple in self.walls:
            self.walls.remove(wall_tuple)
            state = 'closed'
            self.doors[wall_tuple] = {'state': state}
            sign_pos = wall_segment[0]
            sign = Sign(f"sign_{self.sign_counter}", sign_pos)
            self.signs[sign_pos] = sign
            self.sign_counter += 1
            return True
        else:
            return False
    def is_valid_move(self, pos1, pos2):
        if self.grid.out_of_bounds(pos2):
            return False
        move_tuple = tuple(sorted((pos1, pos2)))
        if move_tuple in self.walls:
            if move_tuple in self.wall_damage and self.wall_damage[move_tuple] >= 2:
                pass
            else:
                return False
        if move_tuple in self.doors:
            door_state = self.doors[move_tuple]['state']
            if door_state == 'closed':
                pass
        cell_contents = self.grid.get_cell_list_contents([pos2])
        for obj in cell_contents:
            if isinstance(obj, FirefighterAgent):
                return False
        return True
    def manhattan_distance(self, pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
    def dijkstra(self, start, end, firefighter=None):
        pq = [(0, start, [])]
        visited = set()
        max_iterations = 500
        iterations = 0
        firefighter_positions = set()
        for agent in self.agents:
            if isinstance(agent, FirefighterAgent) and agent != firefighter:
                firefighter_positions.add(agent.pos)
        is_interior_position = lambda pos: 1 <= pos[0] <= 6 and 1 <= pos[1] <= 8
        allow_outside_paths = not is_interior_position(start) or not is_interior_position(end)
        while pq and iterations < max_iterations:
            iterations += 1
            (cost, current, path) = heapq.heappop(pq)
            if current in visited:
                continue
            path = path + [current]
            visited.add(current)
            if current == end:
                return path, cost
            for neighbor in self.grid.get_neighborhood(current, moore=False, include_center=False):
                if self.grid.out_of_bounds(neighbor):
                    continue
                if neighbor in firefighter_positions and neighbor != end:
                    continue
                if not allow_outside_paths and not is_interior_position(neighbor) and neighbor != end:
                    continue
                if neighbor not in visited and self.is_valid_move(current, neighbor):
                    move_cost = 1
                    move_tuple = tuple(sorted((current, neighbor)))
                    if move_tuple in self.doors:
                        door_state = self.doors[move_tuple]['state']
                        if door_state == 'closed':
                            move_cost += 3
                    if neighbor in self.fires and firefighter and firefighter.is_carrying_victim:
                        move_cost = 1000
                    if neighbor in self.fires:
                        move_cost = 10
                    elif neighbor in self.smoke:
                        move_cost = 3
                    if not is_interior_position(neighbor) and neighbor != end:
                        move_cost += 20
                    if firefighter and hasattr(firefighter, 'last_positions') and len(firefighter.last_positions) >= 3:
                        if neighbor in firefighter.last_positions[-3:]:
                            move_cost += 5
                    heapq.heappush(pq, (cost + move_cost, neighbor, path))
        return None, float('inf')
    def advance_fire_phase(self):
        if self.game_over:
            return
        target_x = self.random.randint(1, 8)
        target_y = self.random.randint(1, 6)
        target_pos = (target_x, target_y)
        if not (1 <= target_pos[0] <= 6 and 1 <= target_pos[1] <= 8):
            return
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
        self.convert_adjacent_smoke_to_fire()
        self.check_victims_in_fire()
        self.replenish_pois()
    def handle_shockwave(self, start_pos, direction):
        current_pos = start_pos
        max_steps = 20
        steps = 0
        while steps < max_steps:
            steps += 1
            next_pos = (current_pos[0] + direction[0], current_pos[1] + direction[1])
            if self.grid.out_of_bounds(next_pos):
                break
            move_tuple = tuple(sorted((current_pos, next_pos)))
            if move_tuple in self.walls:
                if move_tuple not in self.wall_damage:
                    self.wall_damage[move_tuple] = 0
                if self.wall_damage[move_tuple] < 2:
                    self.wall_damage[move_tuple] += 1
                    self.damage_cubes += 1
                    state_str = ['saludable', 'dañado', 'destruido'][self.wall_damage[move_tuple]]
                    if self.wall_damage[move_tuple] == 2:
                        pass  # Wall is destroyed, shockwave continues
                    if self.wall_damage[move_tuple] < 2:
                        break
            if move_tuple in self.doors:
                door_state = self.doors[move_tuple]['state']
                if door_state == 'closed':
                    self.doors[move_tuple]['state'] = 'destroyed'
                    break
                elif door_state == 'open':
                    self.doors[move_tuple]['state'] = 'destroyed'
            if next_pos in self.smoke:
                del self.smoke[next_pos]
                fire = Fire(f"fire_{self.fire_counter}", next_pos)
                self.fires[next_pos] = fire
                self.fire_counter += 1
                break
            elif next_pos not in self.fires:
                fire = Fire(f"fire_{self.fire_counter}", next_pos)
                self.fires[next_pos] = fire
                self.fire_counter += 1
                break
            else:
                current_pos = next_pos

    def handle_explosion(self, pos):
        directions = [(0, 1), (0, -1), (-1, 0), (1, 0)]
        explosion_count = 0
        damaged_walls_this_turn = set()
        for dx, dy in directions:
            current_pos = pos
            while True:
                next_pos = (current_pos[0] + dx, current_pos[1] + dy)
                if self.grid.out_of_bounds(next_pos):
                    break
                move_tuple = tuple(sorted((current_pos, next_pos)))
                if move_tuple in self.walls and move_tuple not in damaged_walls_this_turn:
                    if move_tuple not in self.wall_damage:
                        self.wall_damage[move_tuple] = 0
                    if self.wall_damage[move_tuple] < 2:
                        self.wall_damage[move_tuple] += 1
                        self.damage_cubes += 0.5
                        damaged_walls_this_turn.add(move_tuple)
                        state_str = ['saludable', 'dañado', 'destruido'][self.wall_damage[move_tuple]]
                        if self.wall_damage[move_tuple] == 2:
                            pass  # Wall is destroyed, shockwave continues
                    else:
                        break
                if move_tuple in self.doors:
                    if self.doors[move_tuple]['state'] != 'destroyed':
                        self.doors[move_tuple]['state'] = 'destroyed'
                        break
                if next_pos in self.smoke:
                    del self.smoke[next_pos]
                    fire = Fire(f"fire_{self.fire_counter}", next_pos)
                    self.fires[next_pos] = fire
                    self.fire_counter += 1
                    explosion_count += 1
                    if explosion_count >= 1:
                        break
                if not self.grid.out_of_bounds(next_pos):
                    cell_contents = self.grid.get_cell_list_contents([next_pos])
                    for agent in cell_contents:
                        if isinstance(agent, FirefighterAgent):
                            agent.is_knocked_down = True
                            outside_positions = []
                            for x in range(self.width):
                                outside_positions.extend([(x, 0), (x, 9)])
                            for y in range(1, 9):
                                outside_positions.extend([(0, y), (7, y)])
                            nearest_outside = min(outside_positions, key=lambda spot: self.manhattan_distance(next_pos, spot))
                            self.grid.move_agent(agent, nearest_outside)
                            if agent.is_carrying_victim:
                                agent.is_carrying_victim = False
                                self.victims_lost += 1
                if next_pos in self.fires:
                    current_pos = next_pos
                    self.handle_shockwave(current_pos, (dx, dy))
                else:
                    break
            break

    def convert_adjacent_smoke_to_fire(self):
        def convert_adjacent_smoke_to_fire(self):
            smokes_to_convert = []
            for smoke_pos in list(self.smoke.keys()):
                neighbors = self.grid.get_neighborhood(smoke_pos, moore=False, include_center=False)
                for neighbor_pos in neighbors:
                    if neighbor_pos in self.fires:
                        move_tuple = tuple(sorted((smoke_pos, neighbor_pos)))
                        blocked = False
                        if move_tuple in self.walls:
                            if move_tuple not in self.wall_damage or self.wall_damage[move_tuple] < 2:
                                blocked = True
                        if move_tuple in self.doors and self.doors[move_tuple]['state'] == 'closed':
                            blocked = True
                        if not blocked:
                            smokes_to_convert.append(smoke_pos)
                            break  # No need to check other neighbors for this smoke
            for smoke_pos in smokes_to_convert:
                if smoke_pos in self.smoke:
                    del self.smoke[smoke_pos]
                    if smoke_pos not in self.fires:
                        fire = Fire(f"fire_{self.fire_counter}", smoke_pos)
                        self.fires[smoke_pos] = fire
                        self.fire_counter += 1
                
    def check_victims_in_fire(self):
        starting_positions = [(4, 0), (7, 6), (0, 3), (3, 9)]
        victims_to_remove = []
        pois_to_remove = []
        for agent in self.agents:
            if isinstance(agent, FirefighterAgent):
                if agent.pos in self.fires:
                    agent.is_knocked_down = True
                    if agent.is_carrying_victim:
                        agent.is_carrying_victim = False
                        self.victims_lost += 1
                    nearest_start = min(starting_positions, key=lambda spot: self.manhattan_distance(agent.pos, spot))
                    self.grid.move_agent(agent, nearest_start)
            elif isinstance(agent, Victim) and agent.is_revealed:
                if agent.pos in self.fires:
                    victims_to_remove.append(agent)
            elif isinstance(agent, POI) and not agent.is_revealed:
                if agent.pos in self.fires:
                    pois_to_remove.append(agent)
                    if agent.content_type == 'victim':
                        self.victims_lost += 1
                        self.total_victims_on_board -= 1
        for victim in victims_to_remove:
            self.grid.remove_agent(victim)
            self.deregister_agent(victim)
            self.victims_lost += 1
            self.total_victims_on_board -= 1
        for poi in pois_to_remove:
            self.grid.remove_agent(poi)
            self.deregister_agent(poi)
            self.poi_placed -= 1

    def replenish_pois(self):
        current_pois = len([agent for agent in self.agents
                           if isinstance(agent, POI) and not agent.is_revealed])
        while current_pois < 3 and self.poi_placed < self.total_poi_markers:
            empty_positions = []
            for x in range(1, 7):
                for y in range(1, 9):
                    pos = (x, y)
                    cell_contents = self.grid.get_cell_list_contents([pos])
                    if (not cell_contents and
                        pos not in self.fires and
                        pos not in self.smoke):
                        empty_positions.append(pos)
            if empty_positions:
                red_die = self.random.randint(1, 6)
                black_die = self.random.randint(1, 8)
                target_x = black_die - 1
                target_y = red_die - 1
                pos = (target_x, target_y)
                if not (1 <= pos[0] <= 6 and 1 <= pos[1] <= 8):
                    pos = self.random.choice(empty_positions)
                elif pos not in empty_positions:
                    pos = min(empty_positions, key=lambda p: self.manhattan_distance(pos, p))
                total_victims_revealed = (self.total_victims_on_board +
                                        self.victims_rescued + self.victims_lost)
                victims_in_pois = len([agent for agent in self.agents
                                     if isinstance(agent, POI) and agent.content_type == 'victim'])
                total_victims_used = total_victims_revealed + victims_in_pois
                false_alarms_revealed = len([agent for agent in self.agents
                                           if isinstance(agent, POI) and
                                           agent.content_type == 'false_alarm' and
                                           agent.is_revealed])
                false_alarms_in_pois = len([agent for agent in self.agents
                                          if isinstance(agent, POI) and
                                          agent.content_type == 'false_alarm' and
                                          not agent.is_revealed])
                total_false_alarms_used = false_alarms_revealed + false_alarms_in_pois
                victims_left = self.total_victims_available - total_victims_used
                false_alarms_left = self.total_false_alarms_available - total_false_alarms_used
                if victims_left > 0 and (false_alarms_left == 0 or self.random.random() < 0.67):
                    content_type = 'victim'
                elif false_alarms_left > 0:
                    content_type = 'false_alarm'
                else:
                    break
                poi = POI(f"poi_{self.poi_counter}", self, content_type)
                self.grid.place_agent(poi, pos)
                self.register_agent(poi)
                self.poi_counter += 1
                self.poi_placed += 1
                current_pois += 1
            else:
                break
    def check_game_end(self):
        if self.victims_lost >= self.LOSE_VICTIMS_LOST:
            self.game_over = True
            self.game_won = False
            return
        if self.damage_cubes >= self.MAX_DAMAGE_CUBES:
            self.game_over = True
            self.game_won = False
            return
        if self.victims_rescued >= self.WIN_VICTIMS_NEEDED:
            self.game_over = True
            self.game_won = True
            return
    def step(self):
        if self.game_over:
            return
        if self.advance_fire:
            self.advance_fire_phase()
            self.check_game_end()
            self.advance_fire = False
            return
        firefighters = [agent for agent in self.agents if isinstance(agent, FirefighterAgent)]
        if not firefighters:
            return
        all_turns_completed = all(agent.turn_completed for agent in firefighters)
        if all_turns_completed:
            for agent in firefighters:
                agent.start_new_turn()
        current_firefighter = None
        for agent in firefighters:
            if not agent.turn_completed:
                current_firefighter = agent
                break
        action_taken = current_firefighter.step()
        if current_firefighter.turn_completed:
            self.advance_fire = True
    def get_state(self):
        state = {
            "agents": [],
            "victims": [],
            "pois": [],
            "fires": [],
            "smoke": [],
            "signs": [],
            "walls": [
                {
                    "pos": [list(wall[0]), list(wall[1])],
                    "state": self.wall_damage.get(wall, 0)
                } for wall in self.walls
            ],
            "doors": [],
            "game_stats": {
                "victims_rescued": self.victims_rescued,
                "victims_lost": self.victims_lost,
                "damage_cubes": self.damage_cubes,
                "game_over": self.game_over,
                "game_won": self.game_won,
                "win_condition": self.WIN_VICTIMS_NEEDED,
                "lose_victims": self.LOSE_VICTIMS_LOST,
                "max_damage": self.MAX_DAMAGE_CUBES
            }
        }
        for agent in self.agents:
            if isinstance(agent, FirefighterAgent):
                state["agents"].append({
                    "id": agent.unique_id,
                    "pos": agent.pos,
                    "carrying_victim": agent.is_carrying_victim,
                    "action_points": agent.action_points,
                    "saved_ap": agent.saved_ap,
                    "turn_completed": agent.turn_completed
                })
            elif isinstance(agent, Victim):
                state["victims"].append({
                    "id": agent.unique_id,
                    "pos": agent.pos,
                    "is_revealed": agent.is_revealed
                })
            elif isinstance(agent, POI):
                state["pois"].append({
                    "id": agent.unique_id,
                    "pos": agent.pos,
                    "is_revealed": agent.is_revealed,
                    "content_type": agent.content_type if agent.is_revealed else "unknown"
                })
        state["fires"] = list(self.fires.keys())
        state["smoke"] = list(self.smoke.keys())
        state["signs"] = list(self.signs.keys())
        state["doors"] = [
            {"pos": list(door_pos), "state": info["state"]}
            for door_pos, info in self.doors.items()
        ]
        return state