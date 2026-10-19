Shader "Custom/TopWobbleWater"
{
    Properties
    {
        [Header(Base Water)]
        _ShallowColor("Shallow Color", Color) = (0.6, 0.8, 0.95, 1)
        _DeepColor("Deep Color", Color) = (0.2, 0.45, 0.7, 1)
        _FresnelColor("Fresnel Tint", Color) = (0.7, 0.9, 1, 1)

        [Header(Surface Ripple)]
        _FlowSpeed("Ripple Speed", Range(0.0, 5.0)) = 0.6
        _NoiseScale("Ripple Tiling (X, Y)", Vector) = (4, 4, 0, 0)
        _RippleNormalStrength("Ripple Normal Strength", Range(0.0, 2.0)) = 0.4

        [Header(Transparency)]
        _BaseAlpha("Base Alpha", Range(0.0, 1.0)) = 0.55
        _SideAlpha("Side Alpha Multiplier", Range(0.0, 2.0)) = 0.8

        [Header(Lighting)]
        _FresnelPower("Fresnel Power", Range(0.5, 8.0)) = 3.0
        _FresnelStrength("Fresnel Strength", Range(0.0, 2.0)) = 0.7
        _SpecularPower("Specular Power", Range(8.0, 256.0)) = 90.0
        _SpecularStrength("Specular Strength", Range(0.0, 2.0)) = 0.9

        [Header(Top Wobble)]
        _WobbleStrength("Wobble Strength", Range(0.0, 0.1)) = 0.01
        _WobbleSpeed("Wobble Speed", Range(0.0, 10.0)) = 2.0
        _WobbleFrequency("Wobble Frequency", Range(0.0, 20.0)) = 6.0
        _TopY("Water Surface Height (object space Y)", Float) = 0.5
        _WobbleDepth("Wobble Depth From Top", Range(0.01, 2.0)) = 0.35
        _NormalMaskStrength("Side Lock (normal mask)", Range(0.0, 1.0)) = 1.0
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
                half4 _FresnelColor;
                float _FlowSpeed;
                float4 _NoiseScale;
                float _RippleNormalStrength;
                float _BaseAlpha;
                float _SideAlpha;
                float _FresnelPower;
                float _FresnelStrength;
                float _SpecularPower;
                float _SpecularStrength;
                float _WobbleStrength;
                float _WobbleSpeed;
                float _WobbleFrequency;
                float _TopY;
                float _WobbleDepth;
                float _NormalMaskStrength;
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
                float topWeight : TEXCOORD4;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

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

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                UNITY_SETUP_INSTANCE_ID(IN);
                UNITY_TRANSFER_INSTANCE_ID(IN, OUT);

                float3 posOS = IN.positionOS.xyz;
                float t = _Time.y;

                // 1 at top-facing polys, 0 on vertical sides, -1 on bottom.
                // _NormalMaskStrength = 1 -> sides fully locked.
                // _NormalMaskStrength = 0 -> whole upper region wobbles.
                float upFacing = saturate(IN.normalOS.y);
                upFacing = lerp(1.0, upFacing, saturate(_NormalMaskStrength));

                // 1 at _TopY, fading to 0 at _TopY - _WobbleDepth.
                float depth = max(_WobbleDepth, 0.001);
                float heightWeight = smoothstep(_TopY - depth, _TopY, posOS.y);

                float topWeight = upFacing * heightWeight;

                // Horizontal slosh, two de-phased waves so it looks like
                // water rather than the whole mesh sliding.
                posOS.x += sin(t * _WobbleSpeed + posOS.z * _WobbleFrequency + posOS.y * 3.0)
                    * _WobbleStrength * topWeight;
                posOS.z += cos(t * _WobbleSpeed * 0.85 + posOS.x * _WobbleFrequency * 0.9)
                    * _WobbleStrength * topWeight;

                // Small vertical bob, half amplitude so the surface
                // never separates visibly from the container rim.
                posOS.y += sin(t * _WobbleSpeed * 1.3 + (posOS.x + posOS.z) * _WobbleFrequency * 0.7)
                    * _WobbleStrength * 0.5 * topWeight;

                float3 posWS = TransformObjectToWorld(posOS);
                OUT.positionWS = posWS;
                OUT.normalWS = TransformObjectToWorldNormal(IN.normalOS);
                OUT.uv = IN.uv;
                OUT.topWeight = topWeight;
                OUT.positionCS = TransformWorldToHClip(posWS);
                OUT.fogFactor = ComputeFogFactor(OUT.positionCS.z);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(IN);

                float t = _Time.y;

                // Scrolling ripple field, faded out on the sides so only
                // the top surface shimmers. World XZ keeps the pattern
                // stable even while vertices wobble.
                float2 rippleUV = IN.positionWS.xz * 0.5 + float2(t * _FlowSpeed * 0.15, t * _FlowSpeed * 0.1);
                rippleUV *= _NoiseScale.xy * 0.5;
                float n0 = ValueNoise(rippleUV);
                float nx = ValueNoise(rippleUV + float2(0.08, 0.0));
                float nz = ValueNoise(rippleUV + float2(0.0, 0.08));

                float rippleFade = saturate(IN.normalWS.y);
                float2 rippleGrad = float2(nx - n0, nz - n0) * _RippleNormalStrength * rippleFade;

                half3 N = normalize(IN.normalWS + half3(rippleGrad.x, 0, rippleGrad.y));
                half3 viewDir = GetWorldSpaceNormalizeViewDir(IN.positionWS);

                float ndv = abs(dot(N, viewDir));
                float fres = pow(1.0 - saturate(ndv), _FresnelPower);

                // Slight color variation from the ripple so the top reads
                // as moving water even at tiny vertex amplitudes.
                half3 bodyCol = lerp(_ShallowColor.rgb, _DeepColor.rgb, n0 * 0.5 + IN.topWeight * 0.2);

                Light mainLight = GetMainLight();
                half3 ambient = SampleSH(N);
                float wrapNdotL = dot(N, mainLight.direction) * 0.5 + 0.5;
                half3 diffuse = bodyCol * (ambient * 1.2 + mainLight.color * wrapNdotL);

                half3 H = normalize(mainLight.direction + viewDir);
                float spec = pow(saturate(dot(N, H)), _SpecularPower) * _SpecularStrength;
                spec *= 0.3 + 0.7 * rippleFade; // keep sides calmer

                half3 col = diffuse;
                col += _FresnelColor.rgb * fres * _FresnelStrength;
                col += spec * mainLight.color;

                // Sides slightly more transparent so the container reads;
                // top stays solid.
                float alpha = _BaseAlpha * lerp(_SideAlpha, 1.0, rippleFade);

                col = MixFog(col, IN.fogFactor);
                return half4(col, saturate(alpha));
            }
            ENDHLSL
        }
    }

    FallBack "Universal Render Pipeline/Simple Lit"
}
