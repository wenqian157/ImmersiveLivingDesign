using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class OVRController : MonoBehaviour
{
    [SerializeField]
    private OVRPassthroughLayer passthroughLayer;

    private float changePerSecond = 2;
    private float _axis;
    private bool userHorizontal = true;
    private float opacity = 0.1f;

    public void UpdateSeeThrough(Vector2 value)
    {
        _axis = userHorizontal ? value.x : value.y;
        opacity += _axis * changePerSecond * Time.deltaTime;
        opacity = Mathf.Clamp01(opacity);
        passthroughLayer.textureOpacity = opacity;
        //Logs.Instance.debug3D.text = opacity.ToString();
    }

}
