using System.Collections;
using UnityEngine;

public class Clock : MonoBehaviour
{
    [SerializeField] private AudioSource _source;
    [SerializeField] private Transform _secondsArm;
    [SerializeField] private Transform _minutesArm;
    [SerializeField] private Transform _hoursArm;

    [SerializeField] private AudioClip[] _tickTocks;
    private int i;

    private void Start()
    {
        StartCoroutine(SecondsTick());
    }

    private const float DegreesPerSecond = 360f / 60f;
    private const float DegreesPerMinute = 360f / 60f / 60f;
    private const float DegreesPerHour = 360f / 60f / 60f / 12f;

    IEnumerator SecondsTick()
    {
        while (true)
        {
            _secondsArm.Rotate(0, 0, DegreesPerSecond);
            _minutesArm.Rotate(0, 0, DegreesPerMinute);
            _hoursArm.Rotate(0, 0, DegreesPerHour);

            if (i > _tickTocks.Length - 1) i = 0;
            print(i);
            _source.PlayOneShot(_tickTocks[i]);
            i++;

            yield return new WaitForSecondsRealtime(1);
        }
    }

    public enum Type
    {
        GameTime, Realtime
    }
}