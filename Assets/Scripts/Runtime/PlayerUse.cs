using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.ProBuilder.Shapes;

public class PlayerUse : MonoBehaviour
{
    [SerializeField, Range(0.25f, 1f)] private float _minInteractDistance = 0.33f;

    private InputAction _useAction;
    private CC _player;

    void Start()
    {
        _useAction = CC.GetInputAction("Use");
        _player = CC.instance;
    }

    void Update()
    {
        if (_useAction.WasPressedThisFrame())
        {
            var hits = Physics.SphereCastAll(_player.LookPos, 0.25f, _player.LookDir, _minInteractDistance);
            if (hits.Length == 0) return;

            foreach (var hit in hits)
            {
                if (hit.transform.CompareTag("Use"))
                {
                    hit.transform.GetComponent<UseActivator>().Use();
                }
            }
        }
#if UNITY_EDITOR
        if (_useAction.IsPressed())
        {
            if (Physics.SphereCast(_player.LookPos, 0.25f, _player.LookDir, out var hit, _minInteractDistance))
            {
                DebugExtension.DebugWireSphere(hit.point, Color.red, 0.25f);
            }
        }
#endif
    }
}
