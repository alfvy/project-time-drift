// Additive light-reflection streaks on the Branson river (see Tools/BransonBackdrop/br_streaks.py).
// Vertex colour: rgb = light colour, a = intensity (0 at the edges / ends of the streak).
Shader "Branson/Streak"
{
    Properties
    {
        _Intensity ("Intensity", Float) = 0.55
        _Flicker ("Break-up", Range(0, 1)) = 0.85
    }

    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent" "RenderPipeline" = "UniversalPipeline" "IgnoreProjector" = "True" }

        Pass
        {
            Name "BransonStreak"
            Tags { "LightMode" = "UniversalForwardOnly" }

            Blend One One
            ZWrite Off
            ZTest LEqual
            Cull Off

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float _Intensity;
                half _Flicker;
            CBUFFER_END

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
                float2 p = i.positionWS.xz;
                float t = _Time.y;
                // broken, shimmering glitter: noise stretched along the view direction (z), drifting slowly
                float n1 = VNoise(float2(p.x * 1.9, p.y * 0.045 + t * 0.30));
                float n2 = VNoise(float2(p.x * 5.1 + 7.3, p.y * 0.11 - t * 0.55));
                float m = lerp(1.0, saturate(0.20 + 1.15 * (0.62 * n1 + 0.38 * n2)), _Flicker);
                float a = saturate(i.color.a);
                a = a * a * (3.0 - 2.0 * a);
                return half4(i.color.rgb * (a * m * _Intensity), 1.0h);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
