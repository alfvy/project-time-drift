// Converted URP-compatible Leaf Shader
Shader "URP/Blockout/Blockout_Leaf"
{
    Properties
    {
        _Gloss("Gloss", Range(0, 1)) = 0
        _Spec("Spec", Range(0, 1)) = 0
    }

    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry" }
        LOD 200
        Cull Off

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
            };

            struct Varyings
            {
                float4 positionHCS : SV_POSITION;
                float3 worldPos : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
            };

            float _Gloss;
            float _Spec;

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                float3 worldPos = TransformObjectToWorld(IN.positionOS);
                OUT.positionHCS = TransformWorldToHClip(worldPos);
                OUT.worldPos = worldPos.xyz;
                OUT.normalWS = TransformObjectToWorldNormal(IN.normalOS);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float3 viewDir = normalize(GetCameraPositionWS() - IN.worldPos);
                float3 normalWS = normalize(IN.normalWS);

                float3 baseColor = float3(0.286, 0.498, 1.0);
                float fresnel = pow(1.0 - saturate(dot(normalWS, viewDir)), 5.0);
                float3 finalAlbedo = lerp(baseColor * 0.6, baseColor, fresnel);

                Light light = GetMainLight();
                float3 lightDir = normalize(light.direction);
                float NdotL = saturate(dot(normalWS, lightDir));
                float3 diffuse = finalAlbedo * NdotL * light.color;

                float3 halfway = normalize(viewDir + lightDir);
                float spec = pow(saturate(dot(normalWS, halfway)), 1.0 / max(_Gloss, 0.0001));
                float3 specular = spec * _Spec * light.color;

                return float4(diffuse + specular, 1.0);
            }
            ENDHLSL
        }
    }
    Fallback Off
}