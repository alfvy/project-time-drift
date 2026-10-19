Shader "Hidden/DepthCookie"
{
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"

            struct appdata {
                float4 vertex : POSITION;
            };

            struct v2f {
                float4 pos : SV_POSITION;
                float depth : TEXCOORD0;
            };

            v2f vert (appdata v) {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                // Get the linear depth between 0 and 1
                o.depth = -UnityObjectToViewPos(v.vertex).z / _ProjectionParams.z;
                return o;
            }

            fixed4 frag (v2f i) : SV_Target {
                // Return depth as color. 
                // Objects closer to light = 0 (black/shadow), background = 1 (white/light)
                return i.depth;
            }
            ENDCG
        }
    }
}