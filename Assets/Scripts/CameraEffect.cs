using UnityEngine;

public class CameraEffect : MonoBehaviour
{
    private Quaternion targetRotation; // Target rotation for the camera
    private Quaternion defaultRotation; // Default rotation (Neutral state)
    private float rotationSpeed = 2f; // Speed of the rotation

    private void Start()
    {
        // Store the default rotation (assumes the camera starts in a "Neutral" orientation)
        defaultRotation = transform.rotation;
        targetRotation = defaultRotation; // Initially, the target is the default rotation
    }

    private void Update()
    {
        // Smoothly interpolate towards the target rotation
        transform.rotation = Quaternion.Lerp(transform.rotation, targetRotation, Time.deltaTime * rotationSpeed);
    }

    // Public method to trigger the camera rotation
    public void TriggerState(string state)
    {
        switch (state)
        {
            case "Leaning Left":
                // Set target rotation for leaning left
                targetRotation = Quaternion.Euler(transform.eulerAngles.x, transform.eulerAngles.y, -10f);
                break;

            case "Leaning Right":
                // Set target rotation for leaning left
                targetRotation = Quaternion.Euler(transform.eulerAngles.x, transform.eulerAngles.y, 10f);
                break;

            case "Neutral":
            default:
                // Return to default (neutral) rotation
                targetRotation = defaultRotation;
                break;
        }
    }
}
