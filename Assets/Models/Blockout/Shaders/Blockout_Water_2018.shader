// Converted URP-compatible Water Shader
Shader "URP/Blockout/Blockout_Water"
{
    Properties
    {
        _SpecColor("Specular Color", Color) = (1,1,1,1)
        _Gloss("Gloss", Range(0, 1)) = 0.5
        _Spec("Spec", Range(0, 1)) = 0.5
        _Depth_Fade("Depth Fade", Float) = 1
        _Water_Colour_Power("Water Colour Power", Float) = 2
        _Speed("Speed", Float) = 1
        _Tex_World_Scale("Tex World Scale", Float) = 0.5
        _Alpha("Alpha", Float) = 0.5
        _Tex("Tex", 2D) = "white" {}
        _Color_2("Color 2", Color) = (0.933,0.933,0.933,0.004)
        _Depth_Color("Depth Color", Color) = (0.627,0.655,0.678,0.004)
        _Color_1("Color 1", Color) = (0.722,0.541,0.376,0.004)
        _Fresnel_Colour_Bias("Fresnel Colour Bias", Float) = 0
        _Fresnel_Colour_Scale("Fresnel Colour Scale", Float) = 1
    }

    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent" "IgnoreProjector" = "True" }
        LOD 200

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            Cull Back
            ZWrite Off

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
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
                float3 normalWS : TEXCOORD1;
                float2 uv : TEXCOORD2;
                float4 screenPos : TEXCOORD3;
            };

            float4 _Color_1, _Color_2, _Depth_Color;
            float _Fresnel_Colour_Bias, _Fresnel_Colour_Scale, _Water_Colour_Power;
            float _Depth_Fade, _Alpha, _Speed, _Tex_World_Scale;
            float _Gloss, _Spec;
            TEXTURE2D(_Tex); SAMPLER(sampler_Tex);
            TEXTURE2D(_CameraDepthTexture); SAMPLER(sampler_CameraDepthTexture);

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                float3 worldPos = TransformObjectToWorld(IN.positionOS);
                OUT.positionHCS = TransformWorldToHClip(worldPos);
                OUT.worldPos = worldPos.xyz;
                OUT.normalWS = TransformObjectToWorldNormal(IN.normalOS);
                OUT.uv = IN.uv;
                OUT.screenPos = ComputeScreenPos(OUT.positionHCS);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float3 viewDir = normalize(GetCameraPositionWS() - IN.worldPos);
                float fresnel = _Fresnel_Colour_Bias + _Fresnel_Colour_Scale * pow(1.0 - saturate(dot(IN.normalWS, viewDir)), _Water_Colour_Power);
                float4 baseColor = lerp(_Depth_Color, _Color_2, fresnel);
                float4 topColor = lerp(_Color_1, _Color_2, fresnel);

                float2 screenUV = IN.screenPos.xy / IN.screenPos.w;
                float rawDepth = SAMPLE_TEXTURE2D(_CameraDepthTexture, sampler_CameraDepthTexture, screenUV).r;
                float sceneDepth = LinearEyeDepth(rawDepth, _ZBufferParams);
                float pixelDepth = LinearEyeDepth(IN.screenPos.z / IN.screenPos.w, _ZBufferParams);
                float depthLerp = saturate(abs(sceneDepth - pixelDepth) / _Depth_Fade);
                float4 waterColor = lerp(baseColor, topColor, depthLerp);

                float2 worldUV = float2(IN.worldPos.x, IN.worldPos.z) * _Tex_World_Scale;
                float timeOffset = _Time.y * _Speed;
                float2 uvA = worldUV * 1.2 + float2(0.4, 0.0) * timeOffset;
                float2 uvB = worldUV + float2(0.0, 0.55) * timeOffset;
                float2 uvC = worldUV * 0.8 + float2(0.35, 0.0) * timeOffset;
                float2 uvD = worldUV * 1.4 + float2(0.0, -0.45) * timeOffset;

                float noise = min(SAMPLE_TEXTURE2D(_Tex, sampler_Tex, uvA).r, SAMPLE_TEXTURE2D(_Tex, sampler_Tex, uvB).r);
                noise += min(SAMPLE_TEXTURE2D(_Tex, sampler_Tex, uvC).r, SAMPLE_TEXTURE2D(_Tex, sampler_Tex, uvD).r);
                noise = clamp(noise, 0.498, 1.0);

                float shallowDepth = abs(sceneDepth - pixelDepth);
                float edgeFade = pow(saturate(shallowDepth * 3.0), 3.0);

                float3 normalWS = normalize(IN.normalWS);
                Light mainLight = GetMainLight();
                float3 lightDir = normalize(mainLight.direction);
                float3 halfway = normalize(viewDir + lightDir);

                float NdotL = saturate(dot(normalWS, lightDir));
                float3 diffuse = waterColor.rgb * NdotL * mainLight.color;
                float spec = pow(saturate(dot(normalWS, halfway)), 1.0 / max(_Gloss, 0.0001));
                float3 specular = spec * _Spec * mainLight.color;

                float3 finalColor = diffuse + specular;
                return float4(finalColor, saturate(edgeFade * _Alpha));
            }
            ENDHLSL
        }
    }
    Fallback Off
}