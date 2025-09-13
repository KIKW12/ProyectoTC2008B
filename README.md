# Fire Rescue Simulation

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Mesa](https://img.shields.io/badge/Mesa-ABF?style=for-the-badge&logo=python&logoColor=white)](https://mesa.readthedocs.io/)
[![Unity](https://img.shields.io/badge/Unity-000000?style=for-the-badge&logo=unity&logoColor=white)](https://unity.com/)
[![HTTP](https://img.shields.io/badge/HTTP_Server-FF5733?style=for-the-badge)](https://docs.python.org/3/library/http.server.html)
[![JSON](https://img.shields.io/badge/JSON-000000?style=for-the-badge&logo=json&logoColor=white)](https://www.json.org/)
[![JSON.NET](https://img.shields.io/badge/JSON.NET-68217A?style=for-the-badge&logo=nuget&logoColor=white)](https://www.newtonsoft.com/json)
[![Agent Based Modeling](https://img.shields.io/badge/Agent_Based_Modeling-4B8BBE?style=for-the-badge)](https://en.wikipedia.org/wiki/Agent-based_model)

This project implements an agent-based simulation of a fire rescue scenario, inspired by the board game "Flash Point: Fire Rescue". The simulation models firefighters navigating through a building to rescue victims while managing fire spread and structural damage.

## Project Overview

The Fire Rescue Simulation is built using [Mesa](https://mesa.readthedocs.io/), a Python framework for agent-based modeling, and features a Unity-based simulation game for visualization and interaction. The simulation includes:

- A grid-based building with walls, doors, and fire/smoke
- Firefighter agents with different movement and decision-making strategies
- Points of interest (POIs) that may contain victims or false alarms
- Fire propagation and damage mechanics
- A REST API server for controlling the simulation and retrieving state
- A Unity-based game client that visualizes the simulation state
- JSON.NET for deserializing server responses in the Unity client

## Components

### Agents and Environment

- **Firefighter Agents**: The main actors that navigate through the building, extinguish fires, and rescue victims. They have action points (AP) and can carry out various actions like moving, opening doors, and extinguishing fires.
- **Walls and Doors**: Define the structure of the building. Walls can be damaged/chopped, and doors can be opened or closed.
- **Fire and Smoke**: Hazards that spread throughout the building. Fire causes damage and can harm firefighters and victims.
- **Victims**: Need to be rescued by firefighters and carried to exit points.
- **POIs (Points of Interest)**: Unknown elements that need to be investigated by firefighters. They can contain victims or be false alarms.

### Models

- **FireRescueModel (model.py)**: The main simulation model with improved strategy for firefighter agents.
- **RandomFireRescueModel (random_model.py)**: An alternative model where firefighters use random strategies.

### Server

The project includes a HTTP server (server.py) that provides a REST API for controlling the simulation:

- `/init`: Initialize the simulation
- `/step`: Execute a single action step
- `/step_firefighter`: Execute a firefighter action
- `/step_fire`: Execute a fire propagation phase
- `/step_complete_turn`: Complete a full turn (all firefighter actions + fire phase)
- `/reset`: Reset the simulation with configurable parameters

The server responds with JSON data containing the current state of the simulation. This data is consumed by the Unity client, which uses JSON.NET (Newtonsoft.Json) to deserialize the responses and update the game visualization accordingly. The communication protocol ensures that the Unity game always reflects the current state of the simulation model.

## Strategies

The simulation implements different strategies for firefighter agents:

1. **Random Strategy**: Agents make random decisions about movement and actions.
2. **Improved Strategy**: More sophisticated decision-making that prioritizes:
   - Rescuing known victims
   - Investigating POIs
   - Extinguishing fires
   - Exploring unexplored areas

## Game Mechanics

The simulation follows these game mechanics:

- Firefighters have 4 action points (AP) per turn
- Actions like moving, extinguishing fires, and carrying victims consume AP
- Moving through fire or smoke costs extra AP
- The fire spreads during the fire phase
- Victims in fire locations are lost
- The game ends when:
  - Enough victims are rescued (win)
  - Too many victims are lost (lose)
  - Too much structural damage occurs (lose)

## Project Structure

- `model.py`: Main simulation model with improved strategy
- `random_model.py`: Alternative simulation model with random strategy
- `server.py`: HTTP server providing a REST API for the simulation

## Detailed Model Implementation

### Model Architecture

The simulation is built on a model-agent architecture where the `FireRescueModel` class serves as the central controller for the simulation environment. The model manages:

1. **Grid Structure**: An 8x10 grid representing the building layout
2. **Agent Management**: Creating, placing, and tracking all agents in the simulation
3. **Environmental Elements**: Walls, doors, fire, and smoke
4. **Game State**: Tracking victory/loss conditions, damage, and victim status

#### Initialization

During initialization, the model:

- Creates the grid and defines building dimensions
- Sets up initial conditions and counters
- Loads the scenario from a file or creates it programmatically
- Places firefighter agents at designated entry points
- Initializes game state variables

#### Key Model Attributes

- `width`, `height`: Dimensions of the grid
- `walls`, `doors`: Sets and dictionaries tracking building structure
- `fires`, `smoke`: Dictionaries tracking hazard locations
- `victims_rescued`, `victims_lost`: Game state counters
- `damage_cubes`: Tracks structural damage to the building
- `game_over`, `game_won`: End-game state flags

### Detailed Agent Implementation

#### FirefighterAgent

The `FirefighterAgent` is the most complex agent in the simulation, representing a firefighter that navigates the building and performs actions.

##### Attributes

- `unique_id`: Unique identifier for the agent
- `action_points`: Number of action points available (typically 4 per turn)
- `saved_ap`: Action points saved from previous turns
- `is_carrying_victim`: Boolean indicating if carrying a victim
- `is_knocked_down`: Boolean indicating if incapacitated
- `strategy`: Decision-making approach ('random' or 'improved')
- `last_positions`: List tracking recent movements to avoid loops
- `area_visit_count`: Dictionary tracking exploration patterns
- `turns_carrying_victim`: Counter for victim carrying duration
- `current_target`: Target position for movement
- `target_commitment_turns`: Commitment to current target

##### Actions

1. **Movement**:
   - `move_action(new_position)`: Moves the firefighter to an adjacent position
   - Costs vary based on terrain and if carrying a victim
   - Handles interactions with doors and walls
   - Movement through fire/smoke costs double AP

2. **Fire Management**:
   - `extinguish_action(target_pos)`: Removes fire or smoke from a position
   - Costs 1 AP per action
   - Cannot extinguish through walls or closed doors

3. **Structure Interaction**:
   - `chop_wall_action(wall_segment)`: Damages walls (costs 2 AP)
   - `open_close_door_action(door_position)`: Toggles door state (costs 1 AP)

4. **Victim Handling**:
   - `carry_victim_action()`: Picks up a revealed victim
   - `rescue_victim_at_exit()`: Completes a rescue at an exit
   - `reveal_poi_if_present()`: Investigates POIs to find victims

5. **Turn Management**:
   - `end_turn()`: Finalizes a turn and saves remaining AP
   - `start_new_turn()`: Resets AP and status for a new turn

#### Other Agents and Elements

1. **Victim**:
   - Passive agent that must be carried to safety
   - Has revealed/unrevealed state
   - When in fire, becomes a casualty

2. **POI (Point of Interest)**:
   - Represents unknown elements that must be investigated
   - Can contain victims or be false alarms
   - Revealed when a firefighter enters its position

3. **Wall**:
   - Represents barriers between cells
   - Can be damaged and eventually removed by firefighters

4. **Door**:
   - Special passageway that can be opened/closed
   - Allows movement and extinguishing when open
   - Blocks actions when closed

5. **Fire and Smoke**:
   - Environmental hazards that affect movement costs
   - Smoke can convert to fire during fire phase
   - Fire damages structures and endangers victims

### Decision-Making Strategies

#### Random Strategy

The random strategy (`random_strategy_with_loop_avoidance`):

- Makes random action choices with basic avoidance of immediate loops
- Considers affordability of moves based on AP availability
- Has minimal planning and simply reacts to local conditions
- Includes fallback mechanisms when optimal moves aren't available

#### Improved Strategy

The improved strategy (`improved_strategy_single_action`):

- Prioritizes actions based on a tactical hierarchy:
  1. Rescuing victims at exits if carrying one
  2. Carrying revealed victims
  3. Investigating POIs
  4. Extinguishing fires to create safe paths
  5. Exploring new areas
- Maintains a memory of visited areas to promote exploration
- Commits to targets for multiple turns to avoid indecision
- Considers AP efficiency and costs of different actions

### Pathfinding Algorithm

The simulation uses a modified Dijkstra's algorithm for pathfinding, implemented in the `dijkstra(start, end, firefighter)` method:

#### Algorithm Details

1. **Initialization**:
   - Creates a priority queue starting with the source position
   - Maintains a visited set to avoid cycles
   - Sets up a limit on iterations to prevent infinite loops

2. **Cost Calculation**:
   - Movement costs vary based on terrain (fire/smoke)
   - Carrying a victim doubles movement costs
   - Walls block movement unless damaged or opened
   - Doors allow movement only when open

3. **Path Construction**:
   - Builds a path incrementally, tracking the optimal route
   - Returns the full path and total cost
   - Returns None if no path is found

4. **Special Considerations**:
   - Handles interior vs. exterior paths differently
   - Avoids positions occupied by other firefighters
   - Prioritizes paths with lower costs and fewer hazards

#### Pseudocode

```pseudo
function dijkstra(start, end, firefighter):
    priority_queue = [(0, start, [])]  # (cost, position, path)
    visited = empty set
    
    while priority_queue not empty:
        current_cost, current_pos, path = pop lowest cost from priority_queue
        
        if current_pos == end:
            return path, current_cost
            
        if current_pos in visited:
            continue
            
        add current_pos to visited
        
        for each neighbor of current_pos:
            if neighbor is valid move:
                movement_cost = calculate_cost(current_pos, neighbor, firefighter)
                new_path = path + [neighbor]
                add (current_cost + movement_cost, neighbor, new_path) to priority_queue
                
    return None  # No path found
```

#### Handling Complex Scenarios

The pathfinding algorithm handles several complex scenarios:

- Finding paths around fire and smoke with cost optimization
- Navigating through open doors and avoiding closed ones
- Considering whether the firefighter is carrying a victim (affecting costs)
- Finding alternate routes when direct paths are blocked

## Visualization

The simulation is visualized through a Unity-based game client that communicates with the server API. This client:

- Connects to the Python server via HTTP requests
- Uses JSON.NET to deserialize the server responses
- Renders the building layout, agents, fire, and smoke in a 3D environment
- Provides an interactive interface for controlling firefighter actions
- Displays game state information like victim status and damage levels

The Unity client interprets the simulation state data received from the server and converts it into visual elements, creating an engaging and intuitive representation of the simulation. This separation of simulation logic (Python/Mesa) and visualization (Unity) allows for independent development and optimization of each component.

## Future Improvements

- Add more sophisticated firefighter strategies
- Implement a web-based visualization
- Add more complex building layouts
- Include additional game mechanics like specialized equipment
- Support for multiple players/collaborative gameplay
