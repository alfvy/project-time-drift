using System;
using UnityEditor;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.XR;

[RequireComponent(typeof(Rigidbody))]
[RequireComponent(typeof(CapsuleCollider))]
public class CC : MonoSingleton<CC>
{
    public Vector3 LookDir => _camTransform.transform.forward;
    public Vector3 LookPos => _camTransform.transform.position;

    public Camera cam = null!;
    public PlayerInput playerInput = null!;

    [Tooltip("X is Sideways, Z is Forward, Y is Upwards")]
    [SerializeField] private Vector3 moveSpeed = new Vector3(8, 40, 10);
    // move speed multiplier for running
    [SerializeField] private MouseLook mouseLook = new();
    // how long can the player press the jump button 
    [SerializeField] private bool _onGround;
    [SerializeField] private Vector3 desiredMove;
    [SerializeField] private Vector2 _moveInput = Vector2.zero;
    [SerializeField] private Transform _heldObjectTransform;
    public PlayerState state;
    private Vector2 _lookInput = Vector2.zero;
    private Transform _camTransform = null!;
    private Vector3 _groundContactNormal, _previousVelocity, _camInitPos;
    private Rigidbody _rb = null!;
    private CapsuleCollider _capsule = null!;
    private InputAction _moveAction = null!,
        _lookAction = null!,
        _cancelAction = null!,
        _interactAction = null!;

    private void Awake()
    {
        playerInput = GetComponent<PlayerInput>();
        state = Instantiate(state);
    }

    private void OnValidate()
    {
        playerInput = GetComponent<PlayerInput>();
        _rb = GetComponent<Rigidbody>();
    }

    private void Start()
    {
        _rb = GetComponent<Rigidbody>();
        _camTransform = GetComponentInChildren<Camera>().transform;
        _capsule = GetComponent<CapsuleCollider>();
        _moveAction = playerInput.actions["Move"];
        _lookAction = playerInput.actions["Look"];
        _interactAction = playerInput.actions["Interact"];
        _cancelAction = playerInput.actions["Cancel"];
        mouseLook.Init(transform, _camTransform, _cancelAction, _interactAction);
    }

    private void OnEnable()
    {
        if (_moveAction == null) return;

        _moveAction.Enable();
        _lookAction.Enable();
        _cancelAction.Enable();
    }

    private void OnDisable()
    {
        if (_moveAction == null) return;

        _moveAction.Dispose();
        _lookAction.Dispose();
        _cancelAction.Dispose();
    }

    private void Update()
    {
        if (_moveAction.IsPressed())
        {
            _moveInput = _moveAction.ReadValue<Vector2>();
        }
        else { _moveInput = Vector2.zero; }

        if (_lookAction.IsPressed())
        {
            _lookInput = _lookAction.ReadValue<Vector2>();
        }
        else { _lookInput = Vector2.zero; }

        // rotate the camera
        RotateView();
        // check the if the player is grounded
        GroundCheck();
    }

    private void FixedUpdate()
    {
        // get the forward vector of the camera
        desiredMove = _camTransform.forward * (_moveInput.y * moveSpeed.z) +
                      _camTransform.right * (_moveInput.x * moveSpeed.x);

        // keep the desired move vector strictly 2 dimensional
        desiredMove.y = 0;
        desiredMove = Vector3.ProjectOnPlane(desiredMove, _groundContactNormal);

        desiredMove.y = _rb.velocity.y;
        // get the previous velocity of the rigidbody with the default y velocity
        // when the player needs to move, add the desired movement vector
        var sidewaysLerp = new Vector3(_previousVelocity.x / 1.5f,
            _rb.velocity.y, _previousVelocity.z / 1.5f);
        // var sidewaysLerp = new Vector3(0f, _rb.velocity.y, 0f);
        _rb.velocity = _moveInput.magnitude > 0 ? desiredMove : sidewaysLerp;
        // if the player is grounded
        // set the ground time to the current time

        _rb.velocity = Vector3.ClampMagnitude(_rb.velocity, 40);
    }

    private void LateUpdate()
    {
        // get the players previous velocity
        if (_moveInput.magnitude == 0)
            _previousVelocity = _rb.velocity;
    }

    private void RotateView()
    {
        //avoids the mouse looking if the game is effectively paused
        if (Mathf.Abs(Time.timeScale) < float.Epsilon) return;

        // get the rotation before it's changed
        float oldYRotation = transform.eulerAngles.y;

        mouseLook.LookRotation(transform, _camTransform, _moveInput, _lookInput);

        if (_onGround)
        {
            // Rotate the rigidbody velocity to match the new direction that the character is looking
            var velRotation = Quaternion.AngleAxis(transform.eulerAngles.y - oldYRotation, Vector3.up);
            _rb.velocity = velRotation * _rb.velocity;
        }
    }

    private void GroundCheck()
    {
        RaycastHit hitInfo;
        if (Physics.SphereCast(transform.position + _capsule.center,
                _capsule.radius * (1.0f - 0.1f), Vector3.down, out hitInfo,
                ((_capsule.height / 2f) - _capsule.radius) + 0.1f, Physics.AllLayers,
                QueryTriggerInteraction.Ignore))
        {
            _onGround = true;
            _groundContactNormal = hitInfo.normal;
        }
        else
        {
            _onGround = false;
            _groundContactNormal = Vector3.up;
        }
    }

    public void SetHeldItem(GameObject go)
    {
        go.transform.SetParent(_heldObjectTransform);
        go.transform.localPosition = Vector3.zero;
        go.transform.localRotation = Quaternion.identity;
    }

    public Transform GetHeldItem()
    {
        return _heldObjectTransform.GetChild(0);
    }

    public static InputAction GetInputAction(string actionName)
    {
        return instance.playerInput.actions[actionName];
    }

    private static readonly string[] SuspendableActions = { "Move", "Look", "Use", "Interact", "Cancel" };

    /// <summary>
    /// Pauses/resumes movement, looking, interaction and cursor locking.
    /// Used while the player is sitting at a computer (see Simulated Computer/Runtime/Integration).
    /// </summary>
    public void SetControlsSuspended(bool suspended)
    {
        foreach (var actionName in SuspendableActions)
        {
            var action = playerInput.actions[actionName];
            if (suspended) action.Disable();
            else action.Enable();
        }

        mouseLook.SetCursorLock(!suspended);
    }
}
