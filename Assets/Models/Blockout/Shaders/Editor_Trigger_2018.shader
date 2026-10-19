// URP-compatible version of "Blockout/Editor_Trigger"
Shader "URP/Blockout/Editor_Trigger"
{
    Properties
    {
        _Depth_Blend("Depth_Blend", Float) = 1
        _Emissive_Brightness("Emissive_Brightness", Float) = 1
        _Color_1("Color_1", Color) = (0.345098,0.3686275,0.627451,1)
        _Extra_Lines("Extra_Lines", Float) = 0.5
        _Texture0("Texture 0", 2D) = "white" {}
    }

    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry+0" "IsEmissive" = "true" }
        LOD 200
        Blend One One
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

            TEXTURE2D(_Texture0);
			SAMPLER(sampler_Texture0);
            TEXTURE2D_X_FLOAT(_CameraDepthTexture);
			SAMPLER(sampler_CameraDepthTexture);

			// CBUFFER_START(UnityPerMaterial)
            //     float4 _Texture0_ST;
            // CBUFFER_END

            float _Depth_Blend;
            float _Emissive_Brightness;
            float4 _Color_1;
            float _Extra_Lines;

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
            };

            struct Varyings
            {
                float4 positionHCS : SV_POSITION;
                float3 worldNormal : TEXCOORD0;
                float3 worldPos : TEXCOORD1;
                float4 screenPos : TEXCOORD2;
            };

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
                float3 N = normalize(IN.worldNormal);
                float3 V = normalize(GetCameraPositionWS() - IN.worldPos);
                float fresnel = pow(1.0 - dot(N, V), 2.0);
                float intensity = lerp(0.1, 0.4, fresnel);

                // Direction contributions
                float3 dpow = pow(abs(N), 5.0);

                // Sample UVs
                float time = _Time.y * 0.8;
                float2 yz = IN.worldPos.yz;
                float2 xz = IN.worldPos.xz;
                float2 xy = IN.worldPos.xy;

                float sampleXZ = SAMPLE_TEXTURE2D(_Texture0, sampler_Texture0, xz).r;
                float sampleYZ = SAMPLE_TEXTURE2D(_Texture0, sampler_Texture0, yz).r;
                float sampleXY = SAMPLE_TEXTURE2D(_Texture0, sampler_Texture0, xy).r;

                float3 lines = dpow.x * sampleYZ + dpow.y * sampleXZ + dpow.z * sampleXY;

                float2 screenUV = IN.screenPos.xy / IN.screenPos.w;
                float rawDepth = SAMPLE_DEPTH_TEXTURE(_CameraDepthTexture, sampler_CameraDepthTexture, screenUV).r;
                float sceneDepth = LinearEyeDepth(rawDepth, _ZBufferParams);
                float pixelDepth = LinearEyeDepth(IN.screenPos.z, _ZBufferParams);
                float blend = abs(sceneDepth - pixelDepth) / max(_Depth_Blend, 1e-5);

                float3 finalColor = _Color_1.rgb * intensity * (1.0 + lines) * _Emissive_Brightness * blend;
                return float4(finalColor, 1.0);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
