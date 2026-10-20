using System;
using System.Collections.Generic;
using FMOD.Studio;
using FMODUnity;
using UnityEngine;

/// <summary>
/// A drop-in stand-in for Unity's AudioSource that plays FMOD events.
///
/// It follows the AudioSource workflow: assign a default event (the "clip"), call <see cref="Play"/>,
/// <see cref="Stop"/>, <see cref="Pause"/>, or fire extra events with <see cref="PlayOneShot"/>, and query
/// <see cref="isPlaying"/>. Every voice is attached to this GameObject, so 3D events follow it.
/// Stop() ends the main voice and any one-shots, like AudioSource.Stop().
/// </summary>
[AddComponentMenu("Audio/FMOD Audio Source")]
public class FMODAudioSource : MonoBehaviour
{
    [Serializable]
    public struct ParameterValue
    {
        public string name;
        public float value;
    }

    [Tooltip("The event played by Play(); the equivalent of AudioSource.clip.")]
    [SerializeField] private EventReference _event;
    [SerializeField] private bool _playOnAwake;
    [SerializeField, Range(0f, 1f)] private float _volume = 1f;
    [SerializeField, Range(0.1f, 3f)] private float _pitch = 1f;
    [Tooltip("Let events fade out (per their AHDSR / fade settings) on Stop() instead of cutting off.")]
    [SerializeField] private bool _allowFadeOut = true;
    [Tooltip("Parameters applied to every voice this source starts.")]
    [SerializeField] private ParameterValue[] _parameters;

    private readonly List<EventInstance> _voices = new List<EventInstance>();
    private readonly Dictionary<string, float> _parameterValues = new Dictionary<string, float>();
    private Rigidbody _rigidbody;
    private bool _paused;

    /// <summary>The event played by <see cref="Play()"/>.</summary>
    public EventReference clip
    {
        get => _event;
        set => _event = value;
    }

    public bool playOnAwake
    {
        get => _playOnAwake;
        set => _playOnAwake = value;
    }

    public float volume
    {
        get => _volume;
        set
        {
            _volume = Mathf.Clamp01(value);
            foreach (var voice in _voices) voice.setVolume(_volume);
        }
    }

    public float pitch
    {
        get => _pitch;
        set
        {
            _pitch = value;
            foreach (var voice in _voices) voice.setPitch(_pitch);
        }
    }

    /// <summary>True while any voice (main or one-shot) is still sounding.</summary>
    public bool isPlaying
    {
        get
        {
            Prune();
            return _voices.Count > 0;
        }
    }

    public bool isPaused => _paused;

    private void Awake()
    {
        _rigidbody = GetComponent<Rigidbody>();

        if (_parameters == null) return;
        foreach (var p in _parameters)
        {
            if (!string.IsNullOrEmpty(p.name)) _parameterValues[p.name] = p.value;
        }
    }

    private void Start()
    {
        if (_playOnAwake) Play();
    }

    private void Update()
    {
        Prune();
    }

    private void OnDisable()
    {
        StopAll(true);
    }

    /// <summary>Plays the default event, restarting it if it was already playing.</summary>
    public void Play()
    {
        Play(_event);
    }

    /// <summary>Makes <paramref name="eventReference"/> the default event and plays it.</summary>
    public void Play(EventReference eventReference)
    {
        _event = eventReference;
        StopAll(false);
        StartVoice(eventReference, 1f);
    }

    /// <summary>Plays an event on top of whatever is already playing. Does not change the default event.</summary>
    public void PlayOneShot(EventReference eventReference, float volumeScale = 1f)
    {
        StartVoice(eventReference, volumeScale);
    }

    /// <summary>Stops everything this source is playing.</summary>
    public void Stop()
    {
        StopAll(!_allowFadeOut);
    }

    /// <summary>Stops everything this source is playing, choosing fade-out behaviour explicitly.</summary>
    public void Stop(bool immediate)
    {
        StopAll(immediate);
    }

    public void Pause()
    {
        _paused = true;
        foreach (var voice in _voices) voice.setPaused(true);
    }

    public void UnPause()
    {
        _paused = false;
        foreach (var voice in _voices) voice.setPaused(false);
    }

    /// <summary>Sets an FMOD parameter on every live voice and on voices started later.</summary>
    public void SetParameter(string parameterName, float value)
    {
        _parameterValues[parameterName] = value;
        foreach (var voice in _voices) voice.setParameterByName(parameterName, value);
    }

    /// <summary>Fire-and-forget at a world position, like AudioSource.PlayClipAtPoint.</summary>
    public static void PlayAtPoint(EventReference eventReference, Vector3 position)
    {
        if (eventReference.IsNull)
        {
            Debug.LogWarning("FMODAudioSource.PlayAtPoint called with an empty event reference.");
            return;
        }

        RuntimeManager.PlayOneShot(eventReference, position);
    }

    private void StartVoice(EventReference eventReference, float volumeScale)
    {
        if (eventReference.IsNull)
        {
            Debug.LogWarning($"FMODAudioSource on '{name}' has no event to play.", this);
            return;
        }

        var voice = RuntimeManager.CreateInstance(eventReference);
        voice.setVolume(_volume * volumeScale);
        voice.setPitch(_pitch);
        RuntimeManager.AttachInstanceToGameObject(voice, gameObject, _rigidbody);
        foreach (var pair in _parameterValues) voice.setParameterByName(pair.Key, pair.Value);
        if (_paused) voice.setPaused(true);

        voice.start();
        _voices.Add(voice);
    }

    private void StopAll(bool immediate)
    {
        var mode = immediate ? FMOD.Studio.STOP_MODE.IMMEDIATE : FMOD.Studio.STOP_MODE.ALLOWFADEOUT;
        foreach (var voice in _voices)
        {
            voice.stop(mode);
            voice.release();
        }

        _voices.Clear();
    }

    /// <summary>Releases voices that have finished.</summary>
    private void Prune()
    {
        for (var i = _voices.Count - 1; i >= 0; i--)
        {
            var voice = _voices[i];
            if (voice.isValid() && voice.getPlaybackState(out var state) == FMOD.RESULT.OK
                && state != PLAYBACK_STATE.STOPPED) continue;

            if (voice.isValid()) voice.release();
            _voices.RemoveAt(i);
        }
    }
}
