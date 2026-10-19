using UnityEngine;
using System;
using AYellowpaper.SerializedCollections;

[CreateAssetMenu(fileName = "PlayerState", menuName = "PlayerState", order = 0)]
public class PlayerState : ScriptableObject
{
    [Serializable]
    public struct StateValue
    {
        public ValueType Type;
        public string Value;
    }

    [SerializedDictionary("Name", "Value")]
    public SerializedDictionary<string, StateValue> _state;

    public bool GetBoolState(string key)
    {
        if (_state.ContainsKey(key))
        {
            var state = _state[key];
            if (state.Type == ValueType.Bool)
                return Convert.ToBoolean(state.Value);
        }

        return false;
    }

    public int GetIntState(string key)
    {
        if (_state.ContainsKey(key))
        {
            var state = _state[key];
            if (state.Type == ValueType.Int)
                return Convert.ToInt32(state.Value);
        }

        return int.MinValue;
    }

    public float GetFloatState(string key)
    {
        if (_state.ContainsKey(key))
        {
            var state = _state[key];
            if (state.Type == ValueType.Float)
                return Convert.ToSingle(state.Value);
        }

        return float.NegativeInfinity;
    }

    public string GetStringState(string key)
    {
        if (_state.ContainsKey(key))
        {
            var state = _state[key];
            if (state.Type == ValueType.String)
                return state.Value;
        }

        return null;
    }

    public bool SetState(string key, string value, ValueType type)
    {
        if (_state.ContainsKey(key))
        {
            var state = _state[key];
            if (state.Type == type)
            {
                _state[key] = new StateValue { Type = type, Value = value };
                return true;
            }
        }

        return false;
    }

    public enum ValueType
    {
        Bool, Int, Float, String
    }
}

