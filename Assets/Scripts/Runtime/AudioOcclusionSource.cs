using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.UIElements;

public class AudioOcclusionSource : MonoBehaviour
{
    private Transform listenerTransform;

    private float lineCastHitCount = 0f;
    private float linesCastCount = 0f;

    [SerializeField]
    private float occlusionWidening;
    [SerializeField, Range(0f, 180f)]
    private float directionAngle = 90f;
    [SerializeField]
    private LayerMask occlusionLayer;

    private AudioSource _source;
    private AudioLowPassFilter _lowPass;

    public float debug;

    private void Start()
    {
        listenerTransform = CC.instance.cam.transform;
        _lowPass = GetComponent<AudioLowPassFilter>();
    }

    private void Update()
    {
        Occlude();
    }

    public void Occlude()
    {
        FindOcclusionAmount(transform.position, listenerTransform.position);
        SetParameter();

        lineCastHitCount = 0f;
        linesCastCount = 0f;
    }

    private void FindOcclusionAmount(Vector3 sourcePos, Vector3 listenerPos)
    {
        Vector3 sourceLeft = CalculatePoint(sourcePos, listenerPos, occlusionWidening, 1);
        Vector3 sourceRight = CalculatePoint(sourcePos, listenerPos, occlusionWidening, -1);
        Vector3 listenerLeft = CalculatePoint(listenerPos, sourcePos, occlusionWidening, 1);
        Vector3 listenerRight = CalculatePoint(listenerPos, sourcePos, occlusionWidening, -1);
        Vector3 sourceAbove = new Vector3(sourcePos.x, sourcePos.y + occlusionWidening, sourcePos.z);
        Vector3 sourceBelow = new Vector3(sourcePos.x, sourcePos.y - occlusionWidening, sourcePos.z);
        Vector3 listenerAbove = new Vector3(listenerPos.x, listenerPos.y + occlusionWidening, listenerPos.z);
        Vector3 listenerBelow = new Vector3(listenerPos.x, listenerPos.y - occlusionWidening, listenerPos.z);

        CastLine(sourceLeft, listenerLeft);
        CastLine(sourceLeft, listenerPos);
        CastLine(sourceLeft, listenerRight);
        CastLine(sourcePos, listenerLeft);
        CastLine(sourcePos, listenerPos);
        CastLine(sourcePos, listenerRight);
        CastLine(sourceRight, listenerLeft);
        CastLine(sourceRight, listenerPos);
        CastLine(sourceRight, listenerLeft);
        CastLine(sourceAbove, listenerAbove);
        CastLine(sourceBelow, listenerBelow);
    }

    /**********************************************************************
    * CastLine draws a line from (Start) to (End). It increments 
    * lineCastHitCount++ for every collider hit that is part
    * of an occlusion layer. Lines are colored red if they hit and green
    * if not.
    **********************************************************************/
    private void CastLine(Vector3 Start, Vector3 End)
    {
        RaycastHit hit;
        Physics.Linecast(Start, End, out hit, ~occlusionLayer);
        if (hit.collider)
        {
            lineCastHitCount++;
            Debug.DrawLine(Start, hit.point, Color.red);
        }
        else
        {
            Debug.DrawLine(Start, End, Color.green);
        }

        linesCastCount++;
    }

    /**********************************************************************
    * CalculatePoint returns the point on the line perpendicular to the
    * line between source point (a) and listener point (b) through source point (a)
    * multiplied by 1 or -1 (sign) to get point (m) units to the left or right.
    **********************************************************************/
    private Vector3 CalculatePoint(Vector3 a, Vector3 b, float m, int sign)
    {
        float x;
        float z;
        float n = Vector3.Distance(new Vector3(a.x, 0f, a.z), new Vector3(b.x, 0f, b.z));
        float o = m / n;

        x = a.x + sign * (o * (a.z - b.z));
        z = a.z - sign * (o * (a.x - b.x));

        return new Vector3(x, a.y, z);
    }

    /**********************************************************************
    * SetParameter loops through all FMOD event instances and sets their
    * occlusion parameter specified in FMOD. The amount is the ratio
    * of the number of lines cast that hit and occlusion layer to the
    * total number of lines cast. This ratio between 0 - 1 will determine
    * how much occlusion happens based on a parementer curve defined in 
    * FMOD.
    **********************************************************************/
    private void SetParameter()
    {
        float occlusion = lineCastHitCount / linesCastCount;

        var facingWeight = Vector3.Dot(listenerTransform.forward, (transform.position - listenerTransform.position).normalized);

        var final = (1 - occlusion) * Util.Map(facingWeight, -1, 1, 0.75f, 1);

        debug = final;

        _lowPass.cutoffFrequency = Util.Map(final, 0, 1, 1500, 22000);
    }
}