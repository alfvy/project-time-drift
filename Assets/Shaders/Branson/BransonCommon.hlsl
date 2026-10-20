// Shared helpers for the Branson/* shaders.  Include AFTER the UnityPerMaterial CBUFFER, which must
// declare: _SkyTint, _SkyExposure, _SkyRotation, _HazeDensity, _HazeStrength, _HazeFloor, _HazeMip, _HazeElev, _HazeFarStart, _HazeFarEnd.
#ifndef BRANSON_COMMON_INCLUDED
#define BRANSON_COMMON_INCLUDED

TEXTURE2D(_SkyTex);
SAMPLER(sampler_SkyTex);

float Hash21(float2 p)
{
    p = frac(p * float2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return frac(p.x * p.y);
}

float VNoise(float2 p)
{
    float2 i = floor(p);
    float2 f = frac(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = Hash21(i);
    float b = Hash21(i + float2(1, 0));
    float c = Hash21(i + float2(0, 1));
    float d = Hash21(i + float2(1, 1));
    return lerp(lerp(a, b, f.x), lerp(c, d, f.x), f.y);
}

// Samples the scene's panoramic skybox exactly the way Unity's Skybox/Panoramic shader does
// (360 degree, lat-long layout), so reflections / haze always match what is drawn as the sky.
half3 BransonSampleSky(float3 dir, float mip)
{
    float a = _SkyRotation * 0.017453292;
    float s, c;
    sincos(a, s, c);
    float3 d = normalize(dir);
    float3 r = float3(c * d.x - s * d.z, d.y, s * d.x + c * d.z);
    float lon = atan2(r.z, r.x);
    float lat = acos(clamp(r.y, -1.0, 1.0));
    float2 uv = float2(0.5 - lon * 0.15915494, 1.0 - lat * 0.31830989);
    return SAMPLE_TEXTURE2D_LOD(_SkyTex, sampler_SkyTex, uv, mip).rgb * _SkyTint.rgb * _SkyExposure;
}

// colour of the sky behind a point seen along `dirFromCam`
half3 BransonHazeColor(float3 dirFromCam)
{
    float3 d = normalize(float3(dirFromCam.x, max(dirFromCam.y, 0.0) * 0.25 + _HazeElev, dirFromCam.z));
    return BransonSampleSky(d, _HazeMip) + _HazeFloor.rgb;
}

half BransonHazeAmount(float dist)
{
    float k = dist * _HazeDensity;
    half fog = saturate(1.0 - exp2(-k * k * 1.4427)) * _HazeStrength;
    // everything melts into the sky colour before the camera far plane so the scenery never ends in a hard edge
    return max(fog, smoothstep(_HazeFarStart, _HazeFarEnd, dist));
}

#endif
