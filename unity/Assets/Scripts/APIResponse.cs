using System.Collections.Generic;
using Newtonsoft.Json;

[JsonObject]
public class APIResponse
{
    [JsonProperty("status")]
    public string status;

    [JsonProperty("game_state")]
    public GameState game_state;
}

[JsonObject]
public class GameState
{
    [JsonProperty("agents")]
    public List<Agent> agents;

    [JsonProperty("pois")]
    public List<POI> pois;

    [JsonProperty("fires")]
    public List<List<int>> fires;

    [JsonProperty("smoke")]
    public List<List<int>> smoke;

    [JsonProperty("walls")]
    public List<WallOrDoor> walls;

    [JsonProperty("doors")]
    public List<WallOrDoor> doors;

    [JsonProperty("game_stats")]
    public GameStats game_stats;
}

[JsonObject]
public class Agent
{
    [JsonProperty("id")]
    public string id;

    [JsonProperty("pos")]
    public List<int> pos;

    [JsonProperty("carrying_victim")]
    public bool carrying_victim;

    [JsonProperty("action_points")]
    public int action_points;

    [JsonProperty("saved_ap")]
    public int saved_ap;

    [JsonProperty("turn_completed")]
    public bool turn_completed;
}

[JsonObject]
public class POI
{
    [JsonProperty("id")]
    public string id;

    [JsonProperty("pos")]
    public List<int> pos;

    [JsonProperty("is_revealed")]
    public bool is_revealed;

    [JsonProperty("content_type")]
    public string content_type;
}

[JsonObject]
public class WallOrDoor
{
    [JsonProperty("pos")]
    public List<List<int>> pos;

    [JsonProperty("state")]
    public string state;
}

[JsonObject]
public class GameStats
{
    [JsonProperty("victims_rescued")]
    public int victims_rescued;

    [JsonProperty("victims_lost")]
    public int victims_lost;

    [JsonProperty("damage_cubes")]
    public float damage_cubes;

    [JsonProperty("game_over")]
    public bool game_over;

    [JsonProperty("game_won")]
    public bool game_won;

    [JsonProperty("win_condition")]
    public int win_condition;

    [JsonProperty("lose_victims")]
    public int lose_victims;

    [JsonProperty("max_damage")]
    public float max_damage;
}