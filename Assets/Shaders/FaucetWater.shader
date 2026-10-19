Shader "Custom/FaucetRunningWater"
{
    Properties
    {
        [Header(Base Water)]
        _ShallowColor("Shallow Color", Color) = (0.6, 0.8, 0.95, 1)
        _DeepColor("Deep Color", Color) = (0.2, 0.45, 0.7, 1)
        _FoamColor("Foam Color", Color) = (0.9, 0.97, 1, 1)
        _FresnelColor("Fresnel Tint", Color) = (0.7, 0.9, 1, 1)

        [Header(Flow)]
        _FlowSpeed("Flow Speed", Range(0.0, 5.0)) = 1.8
        _NoiseScale("Noise Tiling (X, Y)", Vector) = (3, 1.5, 0, 0)
        _StreakTiling("Foam Streak Tiling (X, Y)", Vector) = (8, 3, 0, 0)
        _FoamThreshold("Foam Threshold", Range(0.0, 1.0)) = 0.62
        _FoamStrength("Foam Strength", Range(0.0, 2.0)) = 0.8

        [Header(Transparency)]
        _BaseAlpha("Base Alpha", Range(0.0, 1.0)) = 0.45
        _AlphaVariation("Flow Alpha Variation", Range(0.0, 1.0)) = 0.4
        _TopFade("Top Fade (faucet mouth)", Range(0.0, 0.5)) = 0.15
        _BottomFade("Bottom Fade (splash end)", Range(0.0, 0.5)) = 0.1

        [Header(Lighting)]
        _FresnelPower("Fresnel Power", Range(0.5, 8.0)) = 3.0
        _FresnelStrength("Fresnel Strength", Range(0.0, 2.0)) = 0.8
        _SpecularPower("Specular Power", Range(8.0, 256.0)) = 80.0
        _SpecularStrength("Specular Strength", Range(0.0, 2.0)) = 0.9

        [Header(Wobble)]
        _WobbleStrength("Wobble Strength", Range(0.0, 0.1)) = 0.015
        _WobbleSpeed("Wobble Speed", Range(0.0, 10.0)) = 4.0
        _WobbleFrequency("Wobble Frequency", Range(0.0, 20.0)) = 8.0
    }

    SubShader
    {
        Tags
        {
            "Queue" = "Transparent"
            "RenderType" = "Transparent"
            "RenderPipeline" = "UniversalPipeline"
            "IgnoreProjector" = "True"
        }
        LOD 200

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }

            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            Cull Off

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile_instancing

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _ShallowColor;
                half4 _DeepColor;
                half4 _FoamColor;
                half4 _FresnelColor;
                float _FlowSpeed;
                float4 _NoiseScale;
                float4 _StreakTiling;
                float _FoamThreshold;
                float _FoamStrength;
                float _BaseAlpha;
                float _AlphaVariation;
                float _TopFade;
                float _BottomFade;
                float _FresnelPower;
                float _FresnelStrength;
                float _SpecularPower;
                float _SpecularStrength;
                float _WobbleStrength;
                float _WobbleSpeed;
                float _WobbleFrequency;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float2 uv : TEXCOORD2;
                half fogFactor : TEXCOORD3;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            // --- Procedural value noise, no textures needed ---
            float Hash12(float2 p)
            {
                float3 p3 = frac(float3(p.xyx) * 0.1031);
                p3 += dot(p3, p3.yzx + 33.33);
                return frac((p3.x + p3.y) * p3.z);
            }

            float ValueNoise(float2 p)
            {
                float2 i = floor(p);
                float2 f = frac(p);
                float2 u = f * f * (3.0 - 2.0 * f);
                float a = Hash12(i);
                float b = Hash12(i + float2(1.0, 0.0));
                float c = Hash12(i + float2(0.0, 1.0));
                float d = Hash12(i + float2(1.0, 1.0));
                return lerp(lerp(a, b, u.x), lerp(c, d, u.x), u.y);
            }

            float Fbm(float2 p)
            {
                float v = 0.0;
                float amp = 0.55;
                for (int i = 0; i < 3; i++)
                {
                    v += amp * ValueNoise(p);
                    p = p * 2.03 + float2(17.3, 9.1);
                    amp *= 0.5;
                }
                return v;
            }

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                UNITY_SETUP_INSTANCE_ID(IN);
                UNITY_TRANSFER_INSTANCE_ID(IN, OUT);

                // Wobble grows towards the bottom of the stream (uv.y = 0).
                // Assumes a standard Unity Cylinder: v = 1 at top, v = 0 at bottom.
                float bottomWeight = 1.0 - IN.uv.y;
                float t = _Time.y;

                float3 posOS = IN.positionOS.xyz;
                posOS.x += sin(t * _WobbleSpeed + posOS.y * _WobbleFrequency) * _WobbleStrength * bottomWeight;
                posOS.z += cos(t * _WobbleSpeed * 0.8 + posOS.y * _WobbleFrequency * 0.9) * _WobbleStrength * bottomWeight;

                // Slight radius pulsing so the stream doesn't look like a rigid pipe.
                float pulse = 1.0 + sin(t * _WobbleSpeed * 1.7 + posOS.y * _WobbleFrequency * 2.0) * _WobbleStrength * 2.0 * bottomWeight;
                posOS.x *= pulse;
                posOS.z *= pulse;

                float3 posWS = TransformObjectToWorld(posOS);
                OUT.positionWS = posWS;
                OUT.normalWS = TransformObjectToWorldNormal(IN.normalOS);
                OUT.uv = IN.uv;
                OUT.positionCS = TransformWorldToHClip(posWS);
                OUT.fogFactor = ComputeFogFactor(OUT.positionCS.z);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(IN);

                float t = _Time.y;

                // Downward scrolling: +t moves the pattern toward smaller v (down).
                float2 flowUV = float2(IN.uv.x * _NoiseScale.x, IN.uv.y * _NoiseScale.y + t * _FlowSpeed);
                float2 flowUV2 = float2(IN.uv.x * _NoiseScale.x * 1.7 + 4.7, IN.uv.y * _NoiseScale.y * 2.2 + t * _FlowSpeed * 1.6);
                float n1 = Fbm(flowUV);
                float n2 = Fbm(flowUV2);
                float flow = n1 * 0.6 + n2 * 0.4;

                // Thin vertical foam streaks, stretched in Y and scrolling fast.
                float2 streakUV = float2(IN.uv.x * _StreakTiling.x, IN.uv.y * _StreakTiling.y + t * _FlowSpeed * 1.5);
                float streak = ValueNoise(streakUV);
                streak = smoothstep(0.35, 0.95, streak);

                half3 N = normalize(IN.normalWS);
                half3 viewDir = GetWorldSpaceNormalizeViewDir(IN.positionWS);

                // abs() keeps both faces of the double-sided cylinder consistent.
                float ndv = abs(dot(N, viewDir));
                float fres = pow(1.0 - saturate(ndv), _FresnelPower);

                // Water body color ramp driven by flow noise.
                half3 bodyCol = lerp(_ShallowColor.rgb, _DeepColor.rgb, flow);

                // Foam mask from combined noise + streaks.
                float foamMask = smoothstep(_FoamThreshold, 1.0, flow * 0.6 + streak * 0.6);

                // Simple wrap diffuse + ambient so backfaces never go black.
                Light mainLight = GetMainLight();
                half3 ambient = SampleSH(N);
                float wrapNdotL = dot(N, mainLight.direction) * 0.5 + 0.5;
                half3 diffuse = bodyCol * (ambient * 1.2 + mainLight.color * wrapNdotL);

                // Blinn-Phong specular from the main light.
                half3 H = normalize(mainLight.direction + viewDir);
                float spec = pow(saturate(dot(N, H)), _SpecularPower) * _SpecularStrength;

                half3 col = diffuse;
                col += _FresnelColor.rgb * fres * _FresnelStrength;
                col += spec * mainLight.color;
                col = lerp(col, _FoamColor.rgb, foamMask * saturate(_FoamStrength));

                float alpha = _BaseAlpha + flow * _AlphaVariation + fres * _FresnelStrength * 0.5 + foamMask * 0.4 + spec * 0.5;

                // Fade the ends so the stream joins the faucet mouth and splash cleanly.
                float topFade = 1.0 - smoothstep(1.0 - max(_TopFade, 0.001), 1.0, IN.uv.y);
                float bottomFade = smoothstep(0.0, max(_BottomFade, 0.001), IN.uv.y);
                alpha *= topFade * bottomFade;
                alpha = saturate(alpha);

                col = MixFog(col, IN.fogFactor);
                return half4(col, alpha);
            }
            ENDHLSL
        }
    }

    FallBack "Universal Render Pipeline/Simple Lit"
}
