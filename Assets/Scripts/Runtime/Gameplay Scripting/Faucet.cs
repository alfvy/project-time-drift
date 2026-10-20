using FMODUnity;
using UnityEngine;

public class Faucet : MonoBehaviour, UseActivator
{
    public GameObject water;
    public GameObject waterJug;
    public bool waterIsRunning = false;
    public bool attemptFaucet = false;
    public bool playerLookingAt;
    public float waterTimer;
    public FMODAudioSource waterSFX;
    public EventReference waterRunEvent;
    public EventReference waterStopEvent;
    public EventReference valveToggleEvent;
    public GameObject waterVFX;

    private Transform _player;

    void Start()
    {
        _player = CC.instance.transform;
    }

    public void Update()
    {
        if (waterIsRunning) return;
        playerLookingAt = Vector3.Dot(_player.forward, (_player.position - transform.position).normalized) < 0.3f;

        if (attemptFaucet && !playerLookingAt)
        {
            waterTimer += Time.deltaTime;
        }

        if (waterTimer > 2f && !waterSFX.isPlaying)
        {
            waterIsRunning = true;
            waterSFX.PlayOneShot(waterRunEvent);
            waterVFX.SetActive(true);
        }
    }

    public void Use()
    {
        if (!attemptFaucet)
        {
            waterSFX.PlayOneShot(valveToggleEvent);
        }

        attemptFaucet = true;

        print("used faucet");

        if (waterIsRunning)
        {
            waterSFX.Stop();
            waterSFX.PlayOneShot(valveToggleEvent);
            waterSFX.PlayOneShot(waterStopEvent);
            water.SetActive(true);
            CC.instance.SetHeldItem(waterJug);
            waterVFX.SetActive(false);

            CC.instance.state.SetState("ACT1WaterFromFaucet", "true", PlayerState.ValueType.Bool);
        }
    }
}