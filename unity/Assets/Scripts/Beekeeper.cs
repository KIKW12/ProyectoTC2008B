using UnityEngine;
using System.Collections;

public class Beekeeper : MonoBehaviour
{
    public float movementSpeed = 5.0f;
    public Animator beekeeperAnimator;
    public GameObject currentPrefab;
    private Vector3 targetPosition = new Vector3(0, -14, 0);
    public bool isMoving = false;

    void Update()
    {
        if (isMoving)
        {
            // drift towards target
            transform.position = Vector3.MoveTowards(transform.position, targetPosition, movementSpeed * Time.deltaTime);

            // reached target
            if (Vector3.Distance(transform.position, targetPosition) < 0.02f)
            {
                beekeeperAnimator.SetBool("isUp", false);
                beekeeperAnimator.SetBool("isDown", false);
                beekeeperAnimator.SetBool("isRight", false);
                beekeeperAnimator.SetBool("isLeft", false);
                isMoving = false;
            }
        }
    }

    // for GameManager
    public void SetNewTarget(Vector3 newTarget)
    {
        if (targetPosition != newTarget)
        {
            UpdateDirection(newTarget[0] - targetPosition[0], newTarget[1] - targetPosition[1]);
            targetPosition = newTarget;
            isMoving = true;
        }
    }

    private void UpdateDirection(float x, float y)
    {
        if (beekeeperAnimator != null)
        {
            if (Mathf.Abs(x) > Mathf.Abs(y))
            {
                beekeeperAnimator.SetBool("isRight", x > 0);
                beekeeperAnimator.SetBool("isLeft", x < 0);
                beekeeperAnimator.SetBool("isUp", false);
                beekeeperAnimator.SetBool("isDown", false);
            }
            else
            {
                beekeeperAnimator.SetBool("isUp", y > 0);
                beekeeperAnimator.SetBool("isDown", y < 0);
                beekeeperAnimator.SetBool("isRight", false);
                beekeeperAnimator.SetBool("isLeft", false);
            }
        }
    }
}