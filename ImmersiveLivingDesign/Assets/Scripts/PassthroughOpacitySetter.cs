using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class PassthroughOpacitySetter : MonoBehaviour
{
    public OVRPassthroughLayer layer; // assign via Inspector

    [Range(0f, 1f)]
    public float opacity = 0.5f; // 0 = fully transparent, 1 = fully opaque

    void Start()
    {
        if (layer != null)
            layer.textureOpacity = opacity; // change at runtime too
    }

    public void SetOpacity(float v)
    {
        if (layer != null) layer.textureOpacity = Mathf.Clamp01(v);
    }
}
