using Firebase;
using Firebase.Database;
using Firebase.Extensions;
using Newtonsoft.Json;
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;
using static Unity.VisualScripting.Member;

public class LocateFurniture : MonoBehaviour
{
    public GameObject Furniture;
    List<MocapData> mocapDatalist;

    private string databasePath = "https://idlworshop-default-rtdb.firebaseio.com/mocapdata.json";

    async void Start()
    {
        var status = await FirebaseApp.CheckAndFixDependenciesAsync();
    }
    public void UpdateTransform()
    {
        StartCoroutine(LoadTrasform());
     
    }

    IEnumerator LoadTrasform()
    {
        using (UnityWebRequest www = UnityWebRequest.Get(databasePath))
        {
            www.SendWebRequest();
            if (!string.IsNullOrEmpty(www.error))
            {
                Debug.LogError($"{www.error}");
                Logs.Instance.debug3D.text = www.error;
                yield break;
            }
            while (!www.isDone)
            {
                Debug.Log("loading mesh...");
                //Logs.Instance.debug3D.text ="loading transform..";
                yield return new WaitForSeconds(0.1f);
            }

            string json = www.downloadHandler.text;
            mocapDatalist = JsonConvert.DeserializeObject<List<MocapData>>(json);
            Logs.Instance.debug3D.text =$"found {mocapDatalist.Count} furniture!";
            AssignTransform();
        }
    }
    public struct MocapData
    {
        public int id;
        public float[] pos;
        public Rot rot;
        public float[] quaternion;
    }
    public struct Rot
    {
        public float[] x;
        public float[] y;
        public float[] z;
    }
    private void AssignTransform()
    {
        Transform bed = Furniture.transform.Find("bed");
        Transform sofa = Furniture.transform.Find("sofa");
        Transform desk = Furniture.transform.Find("desk");
        Transform table = Furniture.transform.Find("table");
        Transform stool1 = Furniture.transform.Find("stool1");
        Transform stool2 = Furniture.transform.Find("stool2");
        Transform person = Furniture.transform.Find("person");

        foreach (var m in mocapDatalist)
        {
            Quaternion convert = Quaternion.Euler(0f, 180f, 0f);

            Quaternion mQ = new Quaternion(m.quaternion[0], m.quaternion[1], m.quaternion[2], m.quaternion[3]);

            Quaternion tQ = QuaternionToUnity(mQ);
            Quaternion uQ = Quaternion.Euler(0, tQ.eulerAngles.y, 0);

            if (m.id == 6)
            {
                bed.localPosition = new Vector3(m.pos[0], 0, m.pos[1]);
                bed.localRotation = uQ;
            }
            else if (m.id == 7)
            {
                sofa.localPosition = new Vector3(m.pos[0], 0, m.pos[1]);
                sofa.localRotation = uQ;
            }
            else if (m.id == 9)
            {
                desk.localPosition = new Vector3(m.pos[0], 0, m.pos[1]);
                desk.localRotation = uQ;
            }
            else if (m.id == 8)
            {
                table.localPosition = new Vector3(m.pos[0], 0, m.pos[1]);
                table.localRotation = uQ;
            }
            else if (m.id == 10)
            {
                stool1.localPosition = new Vector3(m.pos[0], 0, m.pos[1]);
                stool1.localRotation = uQ;
            }
            else if (m.id == 13)
            {
                stool2.localPosition = new Vector3(m.pos[0], 0, m.pos[1]);
                stool2.localRotation = uQ;
            }
            else if (m.id == 14)
            {
                person.localPosition = new Vector3(m.pos[0], 1.7f, m.pos[1]);
                person.localRotation = uQ;
            }

        }
        Furniture.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);

    }
    private static Matrix4x4 MakeM()
    {
        var M = Matrix4x4.identity;
        M.SetColumn(0, new Vector4(-1, 0, 0, 0)); // Sx
        M.SetColumn(1, new Vector4(0, 0, -1, 0)); // Sy
        M.SetColumn(2, new Vector4(0, 1, 0, 0)); // Sz
        M.SetColumn(3, new Vector4(0, 0, 0, 1));
        return M;
    }

    /// Convert a quaternion from the source frame to Unity.
    /// Source quaternion must be in Unity's ctor order (x, y, z, w).
    public static Quaternion QuaternionToUnity(Quaternion sourceQ)
    {
        Matrix4x4 RS = Matrix4x4.Rotate(sourceQ); // source rotation matrix
        Matrix4x4 M = MakeM();
        // Conjugation: R_u = M * R_s * M^T  (M is orthogonal, so inverse = transpose)
        Matrix4x4 RU = M * RS * M.transpose;
        return RU.rotation;
    }

    /// Convert a position from the source frame to Unity (no rotation, just axis change).
    /// (xs, ys, zs) -> (-xs, zs, -ys)
    public static Vector3 PositionToUnity(Vector3 sourcePos)
    {
        return new Vector3(-sourcePos.x, sourcePos.z, -sourcePos.y);
    }
}
