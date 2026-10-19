// Converted URP-compatible version of Blockout_Shader_Comment
Shader "URP/Blockout/Blockout_Shader_Comment"
{
    Properties
    {
        _Color("Color", Color) = (1,1,1,1)
        _Drop_Value("Drop_Value", Float) = 0.5
        _Gloss("Gloss", Range(0 , 1)) = 0.5
        _Metallic("Metallic", Range(0 , 1)) = 0.5
        _Texture("Texture", 2D) = "white" {}
        _Depth_Blend("Depth_Blend", Float) = 0.1
        _TilingFactor("TilingFactor", Float) = 2
        _Float3("Float 3", Range(0 , 1)) = 0
    }

    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent" }
        LOD 200
        Cull Off
        Blend SrcAlpha OneMinusSrcAlpha

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 uv : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionHCS : SV_POSITION;
                float3 worldPos : TEXCOORD0;
                float3 worldNormal : TEXCOORD1;
                float4 screenPos : TEXCOORD2;
            };

            CBUFFER_START(UnityPerMaterial)
            float4 _Color;
            float _Drop_Value;
            float _Gloss;
            float _Metallic;
            float _TilingFactor;
            float _Float3;
            float _Depth_Blend;
            float4 _Texture_ST;
            CBUFFER_END

            TEXTURE2D(_Texture); SAMPLER(sampler_Texture);
            TEXTURE2D_X_FLOAT(_CameraDepthTexture); SAMPLER(sampler_CameraDepthTexture);

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                float3 worldPos = TransformObjectToWorld(IN.positionOS.xyz);
                OUT.positionHCS = TransformWorldToHClip(worldPos);
                OUT.worldPos = worldPos;
                OUT.worldNormal = TransformObjectToWorldNormal(IN.normalOS);
                OUT.screenPos = ComputeScreenPos(OUT.positionHCS);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float3 viewDir = normalize(GetCameraPositionWS() - IN.worldPos);
                float3 normalWS = normalize(IN.worldNormal);

                float fresnel = pow(1.0 - saturate(dot(normalWS, viewDir)), 5.0);
                float blend = lerp(1.0, 0.5, fresnel);

                float dotX = pow(saturate(dot(normalWS, float3(1, 0, 0))), 3.0);
                float dotY = pow(saturate(dot(normalWS, float3(0, 1, 0))), 3.0);
                float dotZ = pow(saturate(dot(normalWS, float3(0, 0, 1))), 3.0);

                float2 uvX = IN.worldPos.zy * _TilingFactor;
                float2 uvY = IN.worldPos.xz * _TilingFactor;
                float2 uvZ = IN.worldPos.xy * _TilingFactor;

                float4 colX = SAMPLE_TEXTURE2D(_Texture, sampler_Texture, uvX);
                float4 colY = SAMPLE_TEXTURE2D(_Texture, sampler_Texture, uvY);
                float4 colZ = SAMPLE_TEXTURE2D(_Texture, sampler_Texture, uvZ);

                float4 combined = _Color * (dotX * colX + dotY * colY + dotZ * colZ);
                float alphaDrop = (dotX * colX.a + dotY * colY.a + dotZ * colZ.a) * _Drop_Value;
                float4 color = clamp(combined + alphaDrop, 0.0, 1.0);

                float2 screenUV = IN.screenPos.xy / IN.screenPos.w;
                float rawDepth = SAMPLE_TEXTURE2D(_CameraDepthTexture, sampler_CameraDepthTexture, screenUV);
                float sceneDepth = LinearEyeDepth(rawDepth, _ZBufferParams);
                float fragDepth = LinearEyeDepth(IN.screenPos.z / IN.screenPos.w, _ZBufferParams);
                float depthBlend = abs(sceneDepth - fragDepth) / _Depth_Blend;

                float3 finalColor = color.rgb * blend;
                return float4(finalColor, _Color.a * depthBlend * _Float3);
            }
            ENDHLSL
        }
    }
    Fallback Off
}