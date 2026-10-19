// Converted URP-compatible HLSL Shader (URP 12+ recommended)
Shader "URP/Blockout/Blockout_Shader_Base"
{
    Properties
    {
        _Color("Color", Color) = (0.447,0.447,0.447,1)
        _Locked_Drop("Locked Drop", Float) = 0.7
        _Texture("Texture", 2D) = "black" {}
        _Drop_Value("Drop Value", Float) = 0.5
        _Gloss("Gloss", Range(0, 1)) = 0.227
        _Metallic("Metallic", Range(0, 1)) = 0.087
    }

    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Transparent" "RenderPipeline" = "UniversalPipeline" }
        // LOD 300
        Cull Back
        ZWrite On
        ZTest LEqual
        Blend Off

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 uv : TEXCOORD0;
                float4 color : COLOR;
            };

            struct Varyings
            {
                float4 positionHCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 worldNormal : TEXCOORD1;
                float3 worldPos : TEXCOORD2;
                float4 color : COLOR;
            };

            float4 _Color;
            float _Locked_Drop;
            float _Drop_Value;
            float _Gloss;
            float _Metallic;
            float4 _Texture_ST;
            TEXTURE2D(_Texture); SAMPLER(sampler_Texture);

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                float3 worldPos = TransformObjectToWorld(IN.positionOS);
                OUT.positionHCS = TransformWorldToHClip(worldPos.xyz);
                OUT.worldNormal = TransformObjectToWorldNormal(IN.normalOS);
                OUT.worldPos = worldPos.xyz;
                OUT.uv = TRANSFORM_TEX(IN.uv, _Texture);
                OUT.color = IN.color;
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                

                float4 texColor = SAMPLE_TEXTURE2D(_Texture, sampler_Texture, IN.uv);
                float4 baseColor = clamp((_Color * texColor) + (texColor.a * _Drop_Value), 0.0, 1.0);
                float4 finalColor = lerp(baseColor * _Locked_Drop, baseColor, IN.color.r);

                // float3 albedo = finalColor.rgb;
                // float3 normalWS = normalize(IN.worldNormal);
                // float3 viewDirWS = normalize(GetCameraPositionWS() - IN.worldPos);

                // // Simple direct lighting approximation (Lambert + Fresnel rim light)
                // Light light = GetMainLight();
                // float3 lightDirWS = normalize(light.direction);
                // float NdotL = saturate(dot(normalWS, lightDirWS));

                // float3 diffuse = albedo * NdotL * light.color.rgb;
                // float3 halfwayDir = normalize(viewDirWS + lightDirWS);
                // float spec = pow(saturate(dot(normalWS, halfwayDir)), 1.0 / max(_Gloss, 0.0001));
                // float3 specular = spec * lerp(0.04, albedo, _Metallic) * light.color.rgb;

                // float3 finalLighting = diffuse + specular;

                InputData inputData = (InputData)0;
                inputData.positionWS = IN.worldPos;
                inputData.normalWS = normalize(IN.worldNormal);
                inputData.viewDirectionWS = normalize(GetCameraPositionWS() - IN.worldPos);

                SurfaceData surfaceData = (SurfaceData)0;
                surfaceData.albedo = finalColor.rgb;
                surfaceData.metallic = _Metallic;
                surfaceData.smoothness = _Gloss;
                surfaceData.alpha = 1;

                float4 color = UniversalFragmentBlinnPhong(inputData, surfaceData);
                return color;

                // return half4(finalLighting, 1.0);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
