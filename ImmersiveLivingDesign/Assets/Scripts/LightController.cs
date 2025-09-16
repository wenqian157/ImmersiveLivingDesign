using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using Hessburg;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.InputSystem;

public class LightController : MonoBehaviour
{

    public SunLight sunLight;
    [HideInInspector]
    public float timeOfDay = 12f;

    // Control parameters (tweak these in Inspector)
    [Header("Skybox Settings")]
    public float minExposure = 0.05f;  // Very dark at night
    public float maxExposure = 1.2f;   // Brightest at noon

    public Color nightColor = new Color(0.4f, 0.45f, 0.55f); // Slightly blue night sky
    public Color dayColor = Color.white;                     // Normal daylight
    public Color sunsetTint = new Color(1.0f, 0.85f, 0.7f);  // Subtle warm color

    [Header("Post Exposure Settings")]
    public Volume globalVolume;  // Assign your global volume
    public float minEV = -3f;    // Night exposure
    public float maxEV = 0f;     // Noon exposure
    public float lampExposureGain = 0.35f; // How much lamp affects exposure

    [Header("Lamp Settings")]
    public Light lamp;           // Assign your point or spot light
    public float lightIntensity = 5f; // Max lamp intensity at night
    public float fadeSpeed = 5f; // How fast lamp fades in/out
    public bool isLightOn = false;

    private ColorAdjustments colorAdjustments;
    private float postExposure = 0;
    private float curvature = 3f;

    private void Awake()
    {
        if (globalVolume != null)
        {
            globalVolume.profile.TryGet(out colorAdjustments);
        }
    }
    public void UpdateSunlight()
    {
        sunLight.timeInHours = timeOfDay;
        //Logs.Instance.debug3D.text = timeOfDay.ToString();
    }
    public void UpdateExposure() 
    {
        float normalized = (Mathf.Cos(Mathf.PI * timeOfDay / 12f) + 1f) * 0.5f;
        postExposure = -6f * Mathf.Pow(normalized, curvature);
        colorAdjustments.postExposure.value = postExposure;

        if (isLightOn)
        {
            float baseEV = postExposure;
            float lampEV = Mathf.Log(1f + lamp.intensity * lampExposureGain, 2f);
            colorAdjustments.postExposure.value = baseEV + lampEV;
        }
    }
    public void UpdateLamp()
    {
        Logs.Instance.debug3D.text = isLightOn.ToString();

        if (isLightOn)
        {
            //lamp.intensity = Mathf.Lerp(lamp.intensity, lightIntensity, Time.deltaTime * fadeSpeed);
            lamp.intensity = lightIntensity;
        }
        else
        {
            //lamp.intensity = Mathf.Lerp(lamp.intensity, 0, Time.deltaTime * fadeSpeed);
            lamp.intensity = 0;
        }
    }
    public void UpdateSkybox()
    {
        if (RenderSettings.skybox == null) return;

        float t = timeOfDay / 24f; // Normalize (0 = midnight, 0.5 = noon)

        // Exposure curve: dark at night, bright at noon
        // Cosine gives us a smooth curve peaking at noon (0.5)
        float dayCurve = Mathf.Clamp01(Mathf.Cos((t - 0.5f) * Mathf.PI * 2f));
        float exposure = Mathf.Lerp(minExposure, maxExposure, dayCurve);
        RenderSettings.skybox.SetFloat("_Exposure", exposure);

        // Tint: fades to nightColor at night, slightly warm at sunrise/sunset
        float warmFactor = Mathf.Exp(-Mathf.Pow(Mathf.Abs(timeOfDay - 6f) / 2f, 2)) // sunrise
                         + Mathf.Exp(-Mathf.Pow(Mathf.Abs(timeOfDay - 18f) / 2f, 2)); // sunset
        warmFactor = Mathf.Clamp01(warmFactor); // ensures 0–1

        // Lerp between night and day colors based on dayCurve
        Color baseColor = Color.Lerp(nightColor, dayColor, dayCurve);
        Color finalColor = Color.Lerp(baseColor, sunsetTint, warmFactor * 0.3f); // subtle warmth
        RenderSettings.skybox.SetColor("_Tint", finalColor);
        //Logs.Instance.debug3D.text = finalColor.ToString();
    }
}
