using UnityEditor.ShaderKeywordFilter;
using UnityEngine;

public class CoffeeFill : MonoBehaviour
{
    public Transform fill;
    public bool startFill;
    public float top;

    void Update()
    {
        if (startFill)
        {
            if (!fill.gameObject.activeSelf) fill.gameObject.SetActive(true);
            var prevPosition = fill.localPosition;
            prevPosition.y = Mathf.Clamp(prevPosition.y + (Time.deltaTime * 0.01f), -10, top);
            fill.localPosition = prevPosition;
        }
    }
}