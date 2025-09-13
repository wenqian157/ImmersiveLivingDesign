using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;

public class OculusControllerActions : MonoBehaviour
{
    [SerializeField]
    private InputActionReference seeThrough;
    public InputActionReference load = null;
    public FirebaseServer server;
    public LocateFurniture furniture;
    public OVRPassthroughLayer passthroughLayer;

    private float changePerSecond = 2;
    private float _axis;
    private bool userHorizontal = true;
    private float opacity = 0.1f;

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
        _axis = userHorizontal ? value.x : value.y;
        opacity += _axis * changePerSecond * Time.deltaTime;
        opacity = Mathf.Clamp01(opacity);
        passthroughLayer.textureOpacity = opacity;
        Logs.Instance.debug3D.text = opacity.ToString();
    }
#if UNITY_EDITOR
    private void Start()
    {
        StartCoroutine(DoEveryTwoSeconds());
    }
    private void Update()
    {
        if (Keyboard.current.spaceKey.isPressed)
        {
            server.UpdateMesh();
            furniture.UpdateTransform();
        }
    }
#endif
}
