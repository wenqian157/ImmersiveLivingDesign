using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;
using Hessburg;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

public class OculusControllerActions : MonoBehaviour
{
    [SerializeField]
    private InputActionReference seeThrough;
    [SerializeField]
    private InputActionReference load;
    [SerializeField]
    private FirebaseServer server;
    [SerializeField]
    private LocateFurniture furniture;
    [SerializeField]
    private LightController lightController;
    [SerializeField]
    private OVRController oVRController;

    private float timeChangeSpeed = 6f;

    private void Awake()
    {
        load.action.started += UpdateMesh;
        seeThrough.action.started += SeeThroughValueChange;
    }
    IEnumerator DoEveryTwoSeconds()
    {
        while (true)
        {
            UpdateMesh2s();
            yield return new WaitForSeconds(2f); // wait 2 seconds
        }
    }
    private void UpdateMesh2s()
    {
        Logs.Instance.debug3D.text = "load!";
        server.UpdateMesh();
        furniture.UpdateTransform();
    }
    private void UpdateMesh(InputAction.CallbackContext context)
    {
        Logs.Instance.debug3D.text = "load!";
        server.UpdateMesh();
        furniture.UpdateTransform();
    }
    private void SeeThroughValueChange(InputAction.CallbackContext context)
    {
        Vector2 value = context.ReadValue<Vector2>();
        oVRController.UpdateSeeThrough(value);
    }
#if UNITY_EDITOR
    private void Start()
    {
        //StartCoroutine(DoEveryTwoSeconds());
    }
#endif
    private void Update()
    {
#if UNITY_EDITOR
        if (Keyboard.current.spaceKey.isPressed)
        {
            server.UpdateMesh();
            furniture.UpdateTransform();
        }

        if (Keyboard.current.digit0Key.isPressed)
        {
            lightController.timeOfDay += timeChangeSpeed * Time.deltaTime;
        }
        if (Keyboard.current.digit9Key.isPressed)
        {
            lightController.timeOfDay -= timeChangeSpeed * Time.deltaTime;
        }

        // Wrap around 0-24
        if (lightController.timeOfDay > 24f) lightController.timeOfDay -= 24f;
        if (lightController.timeOfDay < 0f) lightController.timeOfDay += 24f;

        if (Keyboard.current.lKey.wasPressedThisFrame)
        {
            lightController.isLightOn = !lightController.isLightOn;
        }
#endif

        lightController.UpdateSunlight();
        lightController.UpdateLamp();
        lightController.UpdateExposure();
    }
}
