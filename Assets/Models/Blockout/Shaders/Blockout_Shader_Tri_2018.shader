// Converted URP-compatible version of Blockout_Shader_Tri
Shader "URP/Blockout/Blockout_Shader_Tri"
{
    Properties
    {
        _Color("Color", Color) = (1,1,1,1)
        _Locked_Drop("Locked_Drop", Float) = 0.7
        _Drop_Value("Drop_Value", Float) = 0.5
        _Texture("Texture", 2D) = "white" {}
        _Gloss("Gloss", Range(0 , 1)) = 0.227
        _Metallic("Metallic", Range(0 , 1)) = 0.087
    }

    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Transparent" }
        LOD 200
        Cull Back

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float4 color : COLOR;
            };

            struct Varyings
            {
                float4 positionHCS : SV_POSITION;
                float3 worldPos : TEXCOORD0;
                float3 worldNormal : TEXCOORD1;
                float4 vertexColor : COLOR;
            };

            CBUFFER_START(UnityPerMaterial)
            float4 _Color;
            float _Locked_Drop;
            float _Drop_Value;
            float _Gloss;
            float _Metallic;
            float4 _Texture_ST;
            CBUFFER_END

            TEXTURE2D(_Texture); SAMPLER(sampler_Texture);

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                float3 worldPos = TransformObjectToWorld(IN.positionOS.xyz);
                OUT.positionHCS = TransformWorldToHClip(worldPos);
                OUT.worldPos = worldPos;
                OUT.worldNormal = TransformObjectToWorldNormal(IN.normalOS);
                OUT.vertexColor = IN.color;
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float3 normalWS = normalize(IN.worldNormal);

                float dotX = pow(saturate(dot(normalWS, float3(1, 0, 0))), 3.0);
                float dotY = pow(saturate(dot(normalWS, float3(0, 1, 0))), 3.0);
                float dotZ = pow(saturate(dot(normalWS, float3(0, 0, 1))), 3.0);

                float2 uvX = float2(IN.worldPos.y, IN.worldPos.z);
                float2 uvY = float2(IN.worldPos.x, IN.worldPos.z);
                float2 uvZ = float2(IN.worldPos.x, IN.worldPos.y);

                float4 colX = SAMPLE_TEXTURE2D(_Texture, sampler_Texture, uvX);
                float4 colY = SAMPLE_TEXTURE2D(_Texture, sampler_Texture, uvY);
                float4 colZ = SAMPLE_TEXTURE2D(_Texture, sampler_Texture, uvZ);

                float4 combined = _Color * (dotX * colX + dotY * colY + dotZ * colZ);
                float alphaDrop = (dotX * colX.a + dotY * colY.a + dotZ * colZ.a) * _Drop_Value;
                float4 color = clamp(combined + alphaDrop, 0.0, 1.0);

                float4 finalColor = lerp(color * _Locked_Drop, color, IN.vertexColor.r);
                return float4(finalColor.rgb, 1.0);
            }
            ENDHLSL
        }
    }
    Fallback Off
}