// Converted URP-compatible Depth Blend Shader
Shader "URP/Blockout/Blockout_Depth_Blend"
{
    Properties
    {
        _Color("Color", Color) = (0.498,0.498,0.498,0.004)
        _Depth_Blend("Depth Blend", Float) = 1
    }

    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Geometry+0" "IsEmissive" = "true" }
        LOD 100
        ZWrite Off
        Blend SrcAlpha OneMinusSrcAlpha
        Cull Off

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
            };

            struct Varyings
            {
                float4 positionHCS : SV_POSITION;
                float4 screenPos : TEXCOORD0;
            };

            float4 _Color;
            float _Depth_Blend;
            TEXTURE2D(_CameraDepthTexture); SAMPLER(sampler_CameraDepthTexture);

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                float3 worldPos = TransformObjectToWorld(IN.positionOS);
                OUT.positionHCS = TransformWorldToHClip(worldPos);
                OUT.screenPos = ComputeScreenPos(OUT.positionHCS);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float2 screenUV = IN.screenPos.xy / IN.screenPos.w;
                float sceneRaw = SAMPLE_TEXTURE2D(_CameraDepthTexture, sampler_CameraDepthTexture, screenUV).r;
                float sceneDepth = LinearEyeDepth(sceneRaw, _ZBufferParams);
                float fragDepth = LinearEyeDepth(IN.screenPos.z / IN.screenPos.w, _ZBufferParams);
                float blendFactor = saturate(abs(sceneDepth - fragDepth) / max(_Depth_Blend, 1e-5));
                return float4(_Color.rgb, blendFactor);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
