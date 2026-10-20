// Branson river surface.
//
// Opaque, forward-only (URP Deferred friendly).  Reflects the scene's own panoramic sky with a Fresnel
// term, so the river automatically picks up whatever glow / time of day the skybox shows.
// Vertex colour carries baked data from the Blender generator:
//     R = signed water depth, remapped (-2 .. +8 m  ->  0 .. 1)
//     G = far-shore reflection darkening (1 at the south bank, falling off over ~70 m)
//     B = open-water factor (0 at the banks, 1 mid-channel)
Shader "Branson/Water"
{
    Properties
    {
        [Header(Body)]
        _DeepColor ("Deep Colour", Color) = (0.004, 0.014, 0.020, 1)
        _ShallowColor ("Shallow Colour", Color) = (0.026, 0.060, 0.058, 1)
        _ShallowDepth ("Shallow Depth (m)", Float) = 3.0

        [Header(Reflection)]
        _FresnelF0 ("Fresnel F0", Range(0, 0.2)) = 0.025
        _FresnelPower ("Fresnel Power", Range(1, 8)) = 5.0
        _ReflectionBrightness ("Reflection Brightness", Range(0, 8)) = 3.0
        _ReflectionMip ("Reflection Blur (mip)", Range(0, 8)) = 2.5
        _ReflectionTint ("Reflection Tint (linear multiplier)", Vector) = (0.72, 0.96, 1.12, 1)
        _FarShoreDarken ("Far Shore Darkening", Range(0, 1)) = 0.6

        [Header(Ripples)]
        _RippleStrength ("Ripple Strength (slope)", Range(0, 0.6)) = 0.035
        _FlowSpeed ("Flow Speed", Float) = 0.35
        _FlowDir ("Flow Direction (x,z)", Vector) = (1, 0.12, 0, 0)

        [Header(Shore)]
        _FoamColor ("Foam Colour", Color) = (0.10, 0.12, 0.12, 1)
        _FoamWidth ("Foam Width (m)", Float) = 1.1

        [Header(Sparkle)]
        _Sparkle ("Sparkle Amount", Range(0, 6)) = 0.3
        _SparkleColor ("Sparkle Colour", Color) = (1.0, 0.82, 0.55, 1)

        [Header(Haze)]
        _HazeDensity ("Haze Density", Float) = 0.00075
        _HazeStrength ("Haze Strength", Range(0, 1)) = 1
        _HazeFloor ("Haze Floor", Color) = (0.008, 0.016, 0.022, 1)
        _HazeMip ("Haze Sky Blur (mip)", Range(0, 9)) = 6
        _HazeElev ("Haze Sky Elevation", Range(0, 0.5)) = 0.12
        _HazeFarStart ("Haze Far Fade Start (m)", Float) = 780
        _HazeFarEnd ("Haze Far Fade End (m)", Float) = 985

        [Header(Sky Source)]
        [NoScaleOffset] _SkyTex ("Sky Panorama (synced from the scene skybox)", 2D) = "black" {}
        _SkyTint ("Sky Tint (linear multiplier)", Vector) = (1, 1, 1, 1)
        _SkyExposure ("Sky Exposure", Float) = 0.28
        _SkyRotation ("Sky Rotation", Float) = 0
    }

    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }

        Pass
        {
            Name "BransonWater"
            Tags { "LightMode" = "UniversalForwardOnly" }

            Cull Off
            ZWrite On
            ZTest LEqual

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _DeepColor;
                half4 _ShallowColor;
                float _ShallowDepth;
                half _FresnelF0;
                half _FresnelPower;
                half _ReflectionBrightness;
                half _ReflectionMip;
                float4 _ReflectionTint;
                half _FarShoreDarken;
                half _RippleStrength;
                float _FlowSpeed;
                float4 _FlowDir;
                half4 _FoamColor;
                float _FoamWidth;
                half _Sparkle;
                half4 _SparkleColor;
                float _HazeDensity;
                half _HazeStrength;
                half4 _HazeFloor;
                half _HazeMip;
                half _HazeElev;
                float _HazeFarStart;
                float _HazeFarEnd;
                float4 _SkyTint;
                half _SkyExposure;
                half _SkyRotation;
            CBUFFER_END

            #include "BransonCommon.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float4 color      : COLOR;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float4 color      : COLOR;
            };

            // slope contribution of one travelling wave; fades out where it would alias
            float2 WaveGrad(float2 p, float2 dir, float wavelength, float omega, float slope, float t)
            {
                float k = 6.2831853 / wavelength;
                float ph = k * dot(dir, p) - omega * t;
                float fade = saturate(1.0 - fwidth(ph) * 0.30);
                return dir * (slope * fade * cos(ph));
            }

            Varyings vert(Attributes v)
            {
                Varyings o;
                VertexPositionInputs p = GetVertexPositionInputs(v.positionOS.xyz);
                o.positionCS = p.positionCS;
                o.positionWS = p.positionWS;
                o.color = v.color;
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                float3 toCam = _WorldSpaceCameraPos - i.positionWS;
                float dist = length(toCam);
                float3 V = toCam / max(dist, 1e-3);
                float2 p = i.positionWS.xz;
                float depth = i.color.r * 10.0 - 2.0;
                float farMask = i.color.g;
                float open = i.color.b;

                // ---- ripples (anisotropic, travelling along the flow direction), calmer with distance
                float t = _Time.y * _FlowSpeed;
                float2 flow = normalize(_FlowDir.xy);
                float2 perp = float2(-flow.y, flow.x);
                float2 pw = p + 4.0 * (VNoise(p * 0.03 + t * 0.05) - 0.5);
                float rs = _RippleStrength * lerp(0.45, 1.0, open) * (1.0 - 0.65 * smoothstep(120.0, 650.0, dist));
                float2 g = 0;
                g += WaveGrad(pw, normalize(flow + perp * 0.35), 23.0, 1.64, rs * 0.90, t);
                g += WaveGrad(pw, normalize(flow - perp * 0.50), 11.0, 2.35, rs * 0.80, t);
                g += WaveGrad(pw, normalize(perp + flow * 0.40), 5.3, 3.40, rs * 0.55, t);
                g += WaveGrad(pw, normalize(flow + perp * 1.20), 2.6, 4.80, rs * 0.40, t);
                g += WaveGrad(pw, normalize(perp - flow * 0.70), 1.2, 7.30, rs * 0.25, t);
                float3 n = normalize(float3(-g.x, 1.0, -g.y));

                // ---- reflection of the scene's sky
                float3 R = reflect(-V, n);
                R.y = max(R.y, 0.065);
                half3 refl = BransonSampleSky(R, _ReflectionMip) * _ReflectionBrightness * _ReflectionTint.rgb;
                refl *= lerp(1.0h, 0.25h, saturate(farMask * _FarShoreDarken));
                half F = _FresnelF0 + (1.0h - _FresnelF0) * pow(saturate(1.0 - dot(n, V)), _FresnelPower);

                // ---- body colour from depth
                half shallow = 1.0h - smoothstep(0.0, _ShallowDepth, depth);
                half3 body = lerp(_DeepColor.rgb, _ShallowColor.rgb, shallow);
                half3 col = lerp(body, refl, saturate(F));

                // ---- shoreline foam
                float foamN = smoothstep(0.30, 0.80, VNoise(pw * 0.9 + t * 0.3));
                float foam = (1.0 - smoothstep(0.0, _FoamWidth, depth)) * lerp(0.35, 1.0, foamN);
                foam += (1.0 - smoothstep(0.0, 0.20, depth)) * 0.7;
                col = lerp(col, _FoamColor.rgb, saturate(foam) * 0.85);

                // ---- sun-glow sparkles
                Light mainLight = GetMainLight();
                float2 viewH = normalize(-V.xz + 1e-4);
                float2 sunH = normalize(mainLight.direction.xz + 1e-4);
                float align = lerp(0.35, 1.0, pow(saturate(dot(viewH, sunH)), 2.0));
                float2 sp = p * 1.4;
                float2 cid = floor(sp);
                float rnd = Hash21(cid + floor(_Time.y * 1.7 + Hash21(cid) * 5.0));
                float spark = smoothstep(0.972, 1.0, rnd) * smoothstep(0.5, 0.15, length(frac(sp) - 0.5));
                float sAA = saturate(1.0 - max(fwidth(sp.x), fwidth(sp.y)) * 0.8);
                float sFade = (1.0 - smoothstep(40.0, 260.0, dist)) * sAA * smoothstep(0.0, 1.5, depth);
                col += _SparkleColor.rgb * (spark * sFade * align * _Sparkle * 0.9);

                // ---- haze (same model as Branson/Land)
                half3 hazeCol = BransonHazeColor(-V);
                half fogAmt = BransonHazeAmount(dist);
                col = lerp(col, hazeCol, fogAmt);
                return half4(col, 1.0h);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
