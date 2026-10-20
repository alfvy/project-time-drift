using UnityEngine;
using UnityEngine.InputSystem;
using Cursor = UnityEngine.Cursor;

namespace SimPC.Computer
{
    /// <summary>
    /// "Sit at the computer" mode, hooked into the project's Use system: the screen object is tagged "Use", so
    /// <see cref="PlayerUse"/> calls <see cref="Use"/> when the player presses Use while looking at it.
    /// The camera then glides in front of the screen, movement/look/cursor lock are suspended on <see cref="CC"/>,
    /// and the mouse drives the UI. Escape stands back up.
    /// </summary>
    [DefaultExecutionOrder(100)] // after CC, which rewrites the camera rotation every Update
    [RequireComponent(typeof(ComputerScreen))]
    public sealed class ComputerSeat : MonoBehaviour, UseActivator
    {
        [SerializeField, Min(0.01f)] float transitionTime = 0.45f;
        [SerializeField, Min(1f)] float fillMargin = 1.08f;

        enum State { Standing, SittingDown, Seated, StandingUp }

        State state;
        float blend;
        Pose standPose;
        Pose seatPose;
        Camera viewCamera;
        ComputerScreen screen;

        public bool IsSeated => state == State.Seated || state == State.SittingDown;

        void Awake()
        {
            screen = GetComponent<ComputerScreen>();
        }

        public void Use()
        {
            if (state == State.Standing) Sit();
        }

        void Update()
        {
            if (state != State.Seated) return;

            ApplySeatPose();
            if (Keyboard.current != null && Keyboard.current.escapeKey.wasPressedThisFrame) Stand();
        }

        void ApplySeatPose()
        {
            viewCamera.transform.SetPositionAndRotation(seatPose.position, seatPose.rotation);
        }

        void LateUpdate()
        {
            if (state == State.Standing) return;

            // The seated pose is re-applied every frame (also in Update) so pointer rays see what is rendered.
            if (state == State.Seated)
            {
                ApplySeatPose();
                return;
            }

            var target = state == State.SittingDown ? 1f : 0f;
            blend = Mathf.MoveTowards(blend, target, Time.unscaledDeltaTime / transitionTime);
            var t = Mathf.SmoothStep(0f, 1f, blend);
            viewCamera.transform.SetPositionAndRotation(
                Vector3.Lerp(standPose.position, seatPose.position, t),
                Quaternion.Slerp(standPose.rotation, seatPose.rotation, t));

            if (blend != target) return;
            if (state == State.SittingDown)
            {
                state = State.Seated;
            }
            else
            {
                state = State.Standing;
                ResumePlayer();
            }
        }

        void Sit()
        {
            var player = CC.instance;
            if (player == null) return;
            viewCamera = player.GetComponentInChildren<Camera>();
            if (viewCamera == null) return;

            var cam = viewCamera.transform;
            standPose = new Pose(cam.position, cam.rotation);
            seatPose = ComputeSeatPose();

            player.SetControlsSuspended(true);
            Cursor.lockState = CursorLockMode.None;
            Cursor.visible = true;
            screen.PointerCamera = viewCamera;

            blend = 0f;
            state = State.SittingDown;
        }

        void Stand()
        {
            screen.PointerCamera = null;
            blend = 1f;
            state = State.StandingUp;
        }

        void ResumePlayer()
        {
            if (CC.instance != null) CC.instance.SetControlsSuspended(false);
        }

        /// <summary>A pose straight in front of the screen, far enough back that the whole screen fits the view.</summary>
        Pose ComputeSeatPose()
        {
            var toViewer = -transform.forward;
            var size = (Vector2)transform.lossyScale;
            var halfTan = Mathf.Tan(viewCamera.fieldOfView * 0.5f * Mathf.Deg2Rad);
            var fitDistance = Mathf.Max(size.y * 0.5f / halfTan, size.x * 0.5f / (halfTan * viewCamera.aspect)) * fillMargin;
            // Stay outside the near clip plane or the screen itself gets clipped away.
            var distance = Mathf.Max(fitDistance, viewCamera.nearClipPlane * 1.5f);
            return new Pose(transform.position + toViewer * distance, Quaternion.LookRotation(-toViewer, transform.up));
        }

        // void OnDisable()
        // {
        //     if (state == State.Standing) return;
        //     screen.PointerCamera = null;
        //     state = State.Standing;
        //     ResumePlayer();
        // }
    }
}
