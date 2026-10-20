// Branson backdrop surface shader (terrain, buildings, trees, roads, props).
//
// Cheap, unshadowed, vertex-coloured shading for non-playable scenery that is meant to sit
// "behind the glass":   hemispheric ambient + a weak share of the scene's sun, atmospheric haze that
// is tinted from the scene's own sky (default reflection / skybox), optional procedural canopy
// texture, optional procedural lit windows, optional emissive (vertex alpha).
//
// Vertex colour:  RGB = linear albedo.
//                 A   = canopy mask            (_CANOPY)
//                       floor phase 0..1       (_WINDOWS)
//                       emissive amount        (_EMISSIVE_ALPHA)
//
// URP Deferred note: this is a forward-only shader, so the pass must be "UniversalForwardOnly".
Shader "Branson/Land"
{
    Properties
    {
        [Header(Lighting)]
        _Exposure ("Exposure", Range(0, 6)) = 1
        _SunInfluence ("Sun Influence", Range(0, 2)) = 0.30
        _AmbientSky ("Ambient Sky", Color) = (0.040, 0.062, 0.090, 1)
        _AmbientGround ("Ambient Ground", Color) = (0.014, 0.016, 0.018, 1)

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

        [Header(Canopy)]
        [Toggle(_CANOPY)] _Canopy ("Canopy detail (vertex alpha = mask)", Float) = 0
        _CanopyScale ("Canopy Scale (m)", Float) = 11
        _CanopyContrast ("Canopy Contrast", Range(0, 1.5)) = 0.7

        [Header(Windows)]
        [Toggle(_WINDOWS)] _Windows ("Procedural windows (vertex alpha = floor phase)", Float) = 0
        _WindowLit ("Lit Fraction", Range(0, 1)) = 0.30
        _WindowGlow ("Lit Colour", Color) = (1.0, 0.62, 0.28, 1)
        _WindowGlowBoost ("Lit Boost", Float) = 2.5
        _WindowDark ("Dark Glass", Color) = (0.010, 0.018, 0.026, 1)
        _FloorHeight ("Floor Height (m)", Float) = 3.6
        _WindowCell ("Window Cell Width (m)", Float) = 3.2

        [Header(Emissive)]
        [Toggle(_EMISSIVE_ALPHA)] _EmissiveAlpha ("Vertex alpha = emissive", Float) = 0
        _EmissiveBoost ("Emissive Boost", Float) = 3
    }

    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }

        Pass
        {
            Name "BransonForward"
            Tags { "LightMode" = "UniversalForwardOnly" }

            Cull Back
            ZWrite On
            ZTest LEqual

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vert
            #pragma fragment frag
            #pragma shader_feature_local _CANOPY
            #pragma shader_feature_local _WINDOWS
            #pragma shader_feature_local _EMISSIVE_ALPHA

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half _Exposure;
                half _SunInfluence;
                half4 _AmbientSky;
                half4 _AmbientGround;
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
                float _Canopy;
                float _CanopyScale;
                half _CanopyContrast;
                float _Windows;
                half _WindowLit;
                half4 _WindowGlow;
                half _WindowGlowBoost;
                half4 _WindowDark;
                float _FloorHeight;
                float _WindowCell;
                float _EmissiveAlpha;
                half _EmissiveBoost;
            CBUFFER_END

            #include "BransonCommon.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS   : NORMAL;
                float4 color      : COLOR;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                half3  normalWS   : TEXCOORD1;
                float4 color      : COLOR;
            };

            Varyings vert(Attributes v)
            {
                Varyings o;
                VertexPositionInputs p = GetVertexPositionInputs(v.positionOS.xyz);
                o.positionCS = p.positionCS;
                o.positionWS = p.positionWS;
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                o.color = v.color;
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                float3 toCam = _WorldSpaceCameraPos - i.positionWS;
                float dist = length(toCam);
                float3 N = normalize(i.normalWS);
                half3 albedo = i.color.rgb;
                half3 emissive = 0;

                #if defined(_CANOPY)
                {
                    float2 p = i.positionWS.xz / _CanopyScale;
                    float fw = max(fwidth(p.x), fwidth(p.y));
                    float aa = saturate(1.0 - fw * 1.3);
                    float n = VNoise(p) * 0.55 + VNoise(p * 2.31 + 17.0) * 0.30 + VNoise(p * 5.9 - 9.0) * 0.15;
                    albedo *= 1.0 + (n - 0.5) * _CanopyContrast * 2.0 * i.color.a * aa;
                }
                #endif

                #if defined(_WINDOWS)
                {
                    half wall = 1.0 - smoothstep(0.2, 0.5, abs(N.y));
                    if (wall > 0.01)
                    {
                        float2 t = float2(-N.z, N.x);
                        t /= max(length(t), 1e-4);
                        float u = dot(i.positionWS.xz, t) / _WindowCell;
                        float v = i.positionWS.y / _FloorHeight - i.color.a;
                        float2 cell = floor(float2(u, v));
                        float2 f = frac(float2(u, v));
                        float rnd = Hash21(cell + floor(i.positionWS.xz * 0.173) * 7.31);
                        float fw = max(fwidth(u), fwidth(v));
                        float aa = saturate(1.0 - fw * 0.9);
                        float s = max(fw, 0.02);
                        float wx = smoothstep(0.18, 0.18 + s, f.x) * (1.0 - smoothstep(0.82 - s, 0.82, f.x));
                        float wy = smoothstep(0.26, 0.26 + s, f.y) * (1.0 - smoothstep(0.80 - s, 0.80, f.y));
                        float w = wx * wy;
                        float cover = 0.64 * 0.54;
                        float groundBoost = cell.y < 1.0 ? 0.28 : 0.0;
                        float lit = step(rnd, saturate(_WindowLit + groundBoost));
                        float wMask = lerp(w, cover, 1.0 - aa) * wall;
                        float litVal = lerp(lit, saturate(_WindowLit), 1.0 - aa);
                        albedo = lerp(albedo, _WindowDark.rgb, wMask * 0.94);
                        emissive += _WindowGlow.rgb * (_WindowGlowBoost * wMask * litVal * (0.55 + 0.9 * frac(rnd * 7.0)));
                    }
                }
                #endif

                Light mainLight = GetMainLight();
                half ndl = saturate(dot(N, mainLight.direction));
                half3 hemi = lerp(_AmbientGround.rgb, _AmbientSky.rgb, N.y * 0.5h + 0.5h);
                half3 col = albedo * (hemi + mainLight.color * (_SunInfluence * ndl)) * _Exposure;

                #if defined(_EMISSIVE_ALPHA)
                    emissive += albedo * (i.color.a * _EmissiveBoost);
                #endif

                // atmospheric haze, tinted from the scene sky in the direction of the point
                float3 dir = -toCam / max(dist, 1e-3);
                half3 hazeCol = BransonHazeColor(dir);
                half fogAmt = BransonHazeAmount(dist);
                col = lerp(col, hazeCol, fogAmt);
                col += emissive * (1.0 - fogAmt * 0.65);
                return half4(col, 1.0h);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
