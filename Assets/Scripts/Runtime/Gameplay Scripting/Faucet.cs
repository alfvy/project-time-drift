using UnityEngine;

public class Faucet : MonoBehaviour, UseActivator
{
    public GameObject water;
    public GameObject waterJug;
    public bool waterIsRunning = false;
    public bool attemptFaucet = false;
    public bool playerLookingAt;
    public float waterTimer;
    public AudioSource waterSFX;
    public AudioClip waterRunClip;
    public AudioClip waterStopClip;
    public AudioClip valveToggle;
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
            waterSFX.PlayOneShot(waterRunClip);
            waterVFX.SetActive(true);
        }
    }

    public void Use()
    {
        if (!attemptFaucet)
        {
            waterSFX.PlayOneShot(valveToggle);
        }

        attemptFaucet = true;

        print("used faucet");

        if (waterIsRunning)
        {
            waterSFX.Stop();
            waterSFX.PlayOneShot(valveToggle);
            waterSFX.PlayOneShot(waterStopClip);
            water.SetActive(true);
            CC.instance.SetHeldItem(waterJug);
            waterVFX.SetActive(false);

            CC.instance.state.SetState("ACT1WaterFromFaucet", "true", PlayerState.ValueType.Bool);
        }
    }
}