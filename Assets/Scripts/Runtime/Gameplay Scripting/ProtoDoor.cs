using System.Collections;
using UnityEngine;

public class ProtoDoor : MonoBehaviour, UseActivator
{
    [SerializeField] private Quaternion _openRot;
    [SerializeField] private Quaternion _closeRot;
    [SerializeField, Range(0.1f, 2f)] private float _animTime = 0.75f;
    [SerializeField] private bool _open;

    private bool _inAnim;

    public void Use()
    {
        if (_inAnim) return;

        if (_open)
        {
            StartCoroutine(Close());
            _open = false;
        }
        else
        {
            StartCoroutine(Open());
            _open = true;
        }

        IEnumerator Open()
        {
            _inAnim = true;
            float time = 0;
            while (time < _animTime)
            {
                time += Time.deltaTime;
                transform.rotation = Quaternion.Lerp(_closeRot, _openRot, time / _animTime);
                yield return null;
            }
            transform.rotation = _openRot;
            _inAnim = false;
        }

        IEnumerator Close()
        {
            _inAnim = true;
            float time = _animTime;
            while (time > 0)
            {
                time -= Time.deltaTime;
                transform.rotation = Quaternion.Lerp(_closeRot, _openRot, time / _animTime);
                yield return null;
            }
            transform.rotation = _closeRot;
            _inAnim = false;
        }
    }

    public void SetStartRot()
    {
        _openRot = transform.rotation;
    }

    public void SetEndRot()
    {
        _closeRot = transform.rotation;
    }
}

#if UNITY_EDITOR
[UnityEditor.CustomEditor(typeof(ProtoDoor))]
public class ProtoDoorEditor : UnityEditor.Editor
{
    public override void OnInspectorGUI()
    {
        if (GUILayout.Button("Get Open Position"))
        {
            (target as ProtoDoor).SetStartRot();
        }

        if (GUILayout.Button("Get Close Position"))
        {
            (target as ProtoDoor).SetEndRot();
        }

        base.OnInspectorGUI();

        if (GUILayout.Button("Toggle"))
        {
            (target as ProtoDoor).Use();
        }
    }
}
#endif