// Converted URP-compatible HLSL Shader (URP 12+ recommended)
Shader "URP/Blockout/Area_Comment_Wireframe"
{
    Properties
    {
        _SpecColor("Specular Color", Color) = (1,1,1,1)
        _Depth_Blend("Depth Blend", Float) = 1
        _Color("Color", Color) = (0.498,0.498,0.498,1)
    }

    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Geometry+0" }
        LOD 200

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            Cull Back
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            
            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
            };

            struct Varyings
            {
                float4 positionHCS : SV_POSITION;
                float3 worldPos : TEXCOORD0;
                float3 worldNormal : TEXCOORD1;
                float4 screenPos : TEXCOORD2;
            };

            float4 _Color;
            float _Depth_Blend;
            TEXTURE2D(_CameraDepthTexture);
            SAMPLER(sampler_CameraDepthTexture);

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                float3 worldPos = TransformObjectToWorld(IN.positionOS);
                OUT.positionHCS = TransformWorldToHClip(worldPos.xyz);
                OUT.worldPos = worldPos.xyz;
                OUT.worldNormal = TransformObjectToWorldNormal(IN.normalOS);
                OUT.screenPos = ComputeScreenPos(OUT.positionHCS);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float3 viewDir = normalize(GetCameraPositionWS() - IN.worldPos);
                float fresnel = pow(1.0 - saturate(dot(IN.worldNormal, viewDir)), 2.0);
                float4 colorMix = lerp(1.4 * _Color, _Color, fresnel);
                colorMix = clamp(colorMix, 0.0, 1.0);

                float2 screenUV = IN.screenPos.xy / IN.screenPos.w;
                float rawDepth = SAMPLE_TEXTURE2D(_CameraDepthTexture, sampler_CameraDepthTexture, screenUV).r;
                float sceneEyeDepth = LinearEyeDepth(rawDepth, _ZBufferParams);
                float pixelEyeDepth = LinearEyeDepth(IN.screenPos.z / IN.screenPos.w, _ZBufferParams);
                float depthDiff = abs(sceneEyeDepth - pixelEyeDepth) / _Depth_Blend;

                return float4(colorMix.rgb, depthDiff);
            }
            ENDHLSL
        }

        // Pass
        // {
        //     Name "ShadowCaster"
        //     Tags { "LightMode" = "ShadowCaster" }
        //     HLSLPROGRAM
        //     #pragma vertex ShadowPassVertex
        //     #pragma fragment ShadowPassFragment
        //     #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        //     ENDHLSL
        // }
    }
    Fallback Off
}
