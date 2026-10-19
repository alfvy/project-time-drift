using Unity.Mathematics;
using UnityEngine;

public class MakeCoffee : MonoBehaviour, UseActivator
{
    public bool hasWater = false;
    public bool firstUse = false;
    public Transform waterJugPosition;
    public Transform mugPosition;
    public AudioSource coffeeSFX;
    public GameObject waterStandIn;
    public GameObject flowVFX;
    public AudioClip toggleClip;
    public AudioClip flowClip;
    public CoffeeFill coffeeFill;
    public bool startFill;
    public float fillTimer;
    public bool finished;

    public void Update()
    {
        if (startFill)
        {
            fillTimer += Time.deltaTime;
        }

        if (fillTimer > 5f)
        {
            flowVFX.SetActive(false);
            finished = true;
        }
    }

    public void Use()
    {
        if (finished)
        {
            // mug
        }

        coffeeSFX.PlayOneShot(toggleClip);

        if (!firstUse)
        {
            var mugStateCheck = CC.instance.state.GetBoolState("ACT1CoffeeMug");
            if (mugStateCheck)
            {
                CC.instance.state.SetState("ACT1CoffeeMug", "false", PlayerState.ValueType.Bool);
                firstUse = true;
                var mug = CC.instance.GetHeldItem();
                mug.SetParent(mugPosition);
                mug.localPosition = Vector3.zero;
                mug.localRotation = quaternion.identity;
                return;
            }
        }

        var waterStateCheck = CC.instance.state.GetBoolState("ACT1WaterFromFaucet");
        if (waterStateCheck)
        {
            hasWater = true;
        }

        print("use coffee machine");
        if (hasWater)
        {
            print("coffee machine is filled");
            var waterJug = CC.instance.GetHeldItem();
            waterJug.SetParent(waterJugPosition);
            waterJug.localPosition = Vector3.zero;
            waterJug.localRotation = Quaternion.identity;
            waterStandIn.SetActive(true);
            flowVFX.SetActive(true);
            coffeeSFX.PlayOneShot(flowClip);
            startFill = true;
            coffeeFill.startFill = true;
        }
        else
        {
            print("coffee machine is empty");
        }
    }
}
