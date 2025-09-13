using UnityEngine;

public class GridSpawner : MonoBehaviour
{
    [Header("Prefab to Spawn")]
    public GameObject prefab;

    [Header("Grid Settings")]
    public int countX = 5;
    public int countY = 5;
    public float spacing = 1.5f;

    [Header("Spawn Offset")]
    public Vector3 startOffset = Vector3.zero;

    void Start()
    {
        if (prefab == null)
        {
            Debug.LogWarning("No prefab assigned to GridSpawner!");
            return;
        }

        for (int y = 0; y < countY; y++)
        {
            for (int x = 0; x < countX; x++)
            {
                Vector3 pos = new Vector3(
                    x * spacing,
                    y * spacing,
                    0
                ) + startOffset;

                Instantiate(prefab, pos, Quaternion.identity, transform);
            }
        }
    }
}
