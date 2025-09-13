using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using Newtonsoft.Json;
using TMPro;

public enum StrategyType
{
    Improved,
    Random
}

public class GameManager : MonoBehaviour
{
    public string apiURL = "http://localhost:8585/step";
    public float pollingInterval = 2.0f; // time between API calls
    public float cellSize = 2.0f;

    public Vector3 wallOffset;
    public Vector3 doorOffset;

    public int numberOfAgents = 3;
    public StrategyType strategy = StrategyType.Improved;

    // prefabs
    public GameObject agentPrefab;
    public GameObject beekeeperCarryingPoiPrefab;
    public GameObject firePrefab;
    public GameObject smokePrefab;
    public GameObject poiPrefab;
    public GameObject fullWallPrefab;
    public GameObject damagedWallPrefab;
    public GameObject closedDoorPrefab;
    public GameObject openDoorPrefab;
    public GameObject destroyedDoorPrefab;

    public TMP_Text gameStatusText;

    private GameObject dynamicObjectsParent;
    private GameObject staticObjectsParent;

    private Dictionary<string, GameObject> dynamicObjects = new Dictionary<string, GameObject>();
    private Dictionary<string, GameObject> staticObjects = new Dictionary<string, GameObject>();

    private bool isBoardSetup = false;

    void Awake()
    {
        // initialize parents
        StartCoroutine(PerformCleanup());
        dynamicObjectsParent = new GameObject("Dynamic Objects");
        staticObjectsParent = new GameObject("Static Objects");
    }

    private IEnumerator PerformCleanup()
    {
        // cleanup request to API and setup initial board
        var resetRequest = new
        {
            num_agents = numberOfAgents,
            strategy = strategy.ToString().ToLower()
        };
        string jsonBody = JsonConvert.SerializeObject(resetRequest);

        UnityWebRequest request = UnityWebRequest.PostWwwForm("http://localhost:8585/reset", "");
        request.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(jsonBody));
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");

        yield return request.SendWebRequest();

        if (request.result == UnityWebRequest.Result.Success)
        {
            string jsonResponse = request.downloadHandler.text;
            try
            {
                APIResponse response = JsonConvert.DeserializeObject<APIResponse>(jsonResponse);
                
                if (response?.game_state != null)
                {
                    SetupBoard(response.game_state);
                    UpdateBoard(response.game_state);
                    isBoardSetup = true;
                }
            }
            catch (System.Exception e)
            {
                Debug.LogError("Error parsing reset response: " + e.Message);
            }
        }
        else
        {
            Debug.LogError("Error sending cleanup request: " + request.error);
        }

        // wait few seconds before starting polling
        yield return new WaitForSeconds(1.0f);
        StartCoroutine(PollAPICoroutine());
    }

    IEnumerator PollAPICoroutine()
    {
        // poll api every few seconds
        while (true)
        {
            yield return GetBoardState();
            yield return new WaitForSeconds(pollingInterval);
        }
    }

    IEnumerator GetBoardState()
    {
        // fetch board state from api
        UnityWebRequest request = UnityWebRequest.Get(apiURL);
        yield return request.SendWebRequest();

        if (request.result == UnityWebRequest.Result.Success)
        {
            string jsonResponse = request.downloadHandler.text;
            try
            {
                APIResponse response = JsonConvert.DeserializeObject<APIResponse>(jsonResponse);
                Debug.Log("API Response: " + jsonResponse);

                if (response?.game_state != null)
                {
                    if (!isBoardSetup)
                    {
                        SetupBoard(response.game_state);
                        isBoardSetup = true;
                    }
                    UpdateBoard(response.game_state);

                    // check if game has finished
                    if (response.game_state.game_stats != null)
                    {
                        if (response.game_state.game_stats.game_over)
                        {
                            gameStatusText.text = response.game_state.game_stats.game_won ? "Won! :)" : "Lost :(";
                        }
                        else
                        {
                            gameStatusText.text = "";
                        }
                    }
                }
                else
                {
                    Debug.LogError("Invalid API response or game_state is null.");
                }
            }
            catch (System.Exception e)
            {
                Debug.LogError("Error parsing JSON: " + e.Message + "\nRaw JSON: " + jsonResponse);
            }
        }
        else
        {
            Debug.LogError("Error getting board state: " + request.error);
        }
    }

    private void SetupBoard(GameState state)
    {
        UpdateStaticObjects(state);
    }

    private void UpdateBoard(GameState state)
    {
        // update objects based on the api state
        UpdateStaticObjects(state);

        HashSet<string> newStateKeys = new HashSet<string>();

        if (state.agents != null)
        {
            foreach (var agent in state.agents)
            {
                if (agent?.pos == null) continue;
                string key = "agent_" + agent.id;
                GameObject prefabToUse = agent.carrying_victim ? beekeeperCarryingPoiPrefab : agentPrefab;
                UpdateDynamicObject(key, agent.pos.ToArray(), prefabToUse);
                newStateKeys.Add(key);
            }
        }
        
        if (state.fires != null)
        {
            foreach (var posList in state.fires)
            {
                if (posList?.Count < 2) continue;
                string key = "fire_" + posList[0] + "_" + posList[1];
                UpdateDynamicObject(key, posList.ToArray(), firePrefab);
                newStateKeys.Add(key);
            }
        }
        
        if (state.smoke != null)
        {
            foreach (var posList in state.smoke)
            {
                if (posList?.Count < 2) continue;
                string key = "smoke_" + posList[0] + "_" + posList[1];
                UpdateDynamicObject(key, posList.ToArray(), smokePrefab);
                newStateKeys.Add(key);
            }
        }
        
        if (state.pois != null)
        {
            foreach (var poi in state.pois)
            {
                if (poi?.pos == null) continue;
                string key = "poi_" + poi.id;
                UpdateDynamicObject(key, poi.pos.ToArray(), poiPrefab);
                newStateKeys.Add(key);
            }
        }

        List<string> objectsToRemove = new List<string>();
        foreach (var key in dynamicObjects.Keys)
        {
            if (!newStateKeys.Contains(key))
            {
                objectsToRemove.Add(key);
            }
        }
        foreach (var key in objectsToRemove)
        {
            Destroy(dynamicObjects[key]);
            dynamicObjects.Remove(key);
        }
    }

    private void UpdateStaticObjects(GameState state)
    {
        if (state.walls != null)
        {
            foreach (var wall in state.walls)
            {
                if (wall == null || wall.pos == null || wall.pos.Count < 2) continue;
                string key = "wall_" + wall.pos[0][0] + "_" + wall.pos[0][1] + "_" + wall.pos[1][0] + "_" + wall.pos[1][1];
                UpdateStaticObject(key, wall.pos, GetWallPrefab(wall.state), wallOffset);
            }
        }
        
        if (state.doors != null)
        {
            foreach (var door in state.doors)
            {
                if (door == null || door.pos == null || door.pos.Count < 2) continue;
                string key = "door_" + door.pos[0][0] + "_" + door.pos[0][1] + "_" + door.pos[1][0] + "_" + door.pos[1][1];
                UpdateStaticObject(key, door.pos, GetDoorPrefab(door.state), doorOffset);
            }
        }
    }

    private void UpdateStaticObject(string key, List<List<int>> pos, GameObject prefab, Vector3 offset)
    {
        if (prefab == null)
        {
            if (staticObjects.ContainsKey(key))
            {
                Destroy(staticObjects[key]);
                staticObjects.Remove(key);
            }
            return;
        }

        if (staticObjects.ContainsKey(key))
        {
            GameObject currentObject = staticObjects[key];
            if (currentObject != prefab)
            {
                Destroy(currentObject);
                staticObjects.Remove(key);
                CreateStaticObject(key, pos, prefab, offset);
            }
        }
        else
        {
            CreateStaticObject(key, pos, prefab, offset);
        }
    }

    private void CreateStaticObject(string key, List<List<int>> pos, GameObject prefab, Vector3 offset)
    {
        Vector3 worldPos = GetWorldPosition(pos[0].ToArray(), pos[1].ToArray());
        worldPos += offset;
        GameObject newObject = Instantiate(prefab, worldPos, Quaternion.identity, staticObjectsParent.transform);
        staticObjects.Add(key, newObject);
    }
    
    private GameObject GetWallPrefab(string state)
    {
        // Wall states: 0 = intact, 1 = damaged, 2 = destroyed
        switch (state)
        {
            case "0": // Wall is ok/intact
                return fullWallPrefab;
            case "1": // Wall is damaged
                return damagedWallPrefab;
            case "2": // Wall is destroyed (no wall)
                return null;
            default:
                Debug.LogWarning("Unknown wall state: " + state);
                return fullWallPrefab;
        }
    }

    private GameObject GetDoorPrefab(string state)
    {
        switch (state.ToLower())
        {
            case "open":
                return openDoorPrefab;
            case "closed":
                return closedDoorPrefab;
            case "destroyed":
                return destroyedDoorPrefab;
            default:
                Debug.LogWarning("Unknown door state: " + state);
                return closedDoorPrefab;
        }
    }

    private void UpdateDynamicObject(string key, int[] pos, GameObject prefab)
    {
        // update or create dynamic object, handling prefab changes
        if (pos == null || pos.Length < 2)
        {
            Debug.LogWarning("Invalid position for object " + key);
            return;
        }

        Vector3 newPosition = new Vector3(pos[1] * cellSize, pos[0] * cellSize - 14, 0);

        if (dynamicObjects.ContainsKey(key))
        {
            GameObject obj = dynamicObjects[key];
            Beekeeper bk = obj.GetComponent<Beekeeper>();
            if (bk != null && bk.currentPrefab != prefab)
            {
                StartCoroutine(DelayedPrefabChange(obj, prefab, newPosition, key));
            }
            else
            {
                if (bk != null)
                {
                    bk.SetNewTarget(newPosition);
                }
                else
                {
                    obj.transform.position = newPosition;
                }
                return;
            }
        }
        else
        {
            GameObject newObject = Instantiate(prefab, newPosition, Quaternion.identity, dynamicObjectsParent.transform);
            Beekeeper bkNew = newObject.GetComponent<Beekeeper>();
            if (bkNew != null)
            {
                bkNew.currentPrefab = prefab;
            }
            dynamicObjects.Add(key, newObject);
        }
    }

    private Vector3 GetWorldPosition(int[] pos1, int[] pos2)
    {
        // convert grid positions from the model to unity world coordinates
        if (pos1 == null || pos1.Length < 2 || pos2 == null || pos2.Length < 2)
        {
            Debug.LogWarning("Invalid positions for world position calculation");
            return Vector3.zero;
        }

        if (pos1[1] != pos2[1]){
            return new Vector3((((pos1[1] + pos2[1]) * cellSize) / 2), (pos1[0] * cellSize)-14, 0);
        }
        else
        {
            return new Vector3((pos1[1] * cellSize), (((pos1[0] + pos2[0]) * cellSize) / 2)-14, 0);
        }
    }

    // delayed prefab change
    public void HandlePendingPrefabChange(GameObject oldObject, GameObject newPrefab, Vector3 newPosition, string key)
    {
        if (oldObject != null && dynamicObjects.ContainsKey(key) && dynamicObjects[key] == oldObject)
        {
            Vector3 currentPosition = oldObject.transform.position;
            Quaternion currentRotation = oldObject.transform.rotation;
            Vector3 currentScale = oldObject.transform.localScale;
            
            Destroy(oldObject);
            dynamicObjects.Remove(key);
            
            GameObject newObject = Instantiate(newPrefab, currentPosition, currentRotation, dynamicObjectsParent.transform);
            newObject.transform.localScale = currentScale;
            
            Beekeeper bkNew = newObject.GetComponent<Beekeeper>();
            if (bkNew != null)
            {
                bkNew.currentPrefab = newPrefab;
                bkNew.SetNewTarget(newPosition);
            }
            dynamicObjects.Add(key, newObject);
        }
    }

    private IEnumerator DelayedPrefabChange(GameObject obj, GameObject newPrefab, Vector3 newPosition, string key)
    {
        // Wait 0 seconds before changing prefab
        yield return new WaitForSeconds(0f);
        
        HandlePendingPrefabChange(obj, newPrefab, newPosition, key);
    }
}