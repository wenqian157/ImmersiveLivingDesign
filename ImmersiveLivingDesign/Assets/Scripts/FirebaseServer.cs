using Firebase;
using Firebase.Database;
using Firebase.Extensions;
using Newtonsoft.Json;
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Networking;

public class FirebaseServer : MonoBehaviour
{
    public GameObject parent;
    public GameObject floor;
    [Serializable]
    public class MeshData
    {
        public List<List<int>> faces;
        public List<List<float>> vertices;
    }
    public class MeshDatawColor
    {
        public List<List<float>> colors;
        public List<List<int>> faces;
        public List<List<float>> vertices;
    }

    private string databasePath = "https://idlworshop-default-rtdb.firebaseio.com/mesh.json";
    private string floorPath = "https://idlworshop-default-rtdb.firebaseio.com/floor.json";

    async void Start()
    {
        var status = await FirebaseApp.CheckAndFixDependenciesAsync();
        Logs.Instance.debug3D.text = status.ToString();
    }
    public void UpdateMesh()
    {
        StartCoroutine(LoadMeshAsync());
        StartCoroutine(LoadFloorAsync());
    }

    IEnumerator LoadMeshAsync()
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
                yield return new WaitForSeconds(0.1f);
            }

            string json = www.downloadHandler.text;
            Logs.Instance.debug3D.text = json.Length.ToString();
            MeshData meshData = JsonConvert.DeserializeObject<MeshData>(json);
            Mesh mesh = ConvertToUnityMesh(meshData);
            parent.GetComponent<MeshFilter>().mesh = mesh;
            parent.transform.localRotation = Quaternion.identity;

        }
    }
    IEnumerator LoadFloorAsync()
    {
        using (UnityWebRequest www = UnityWebRequest.Get(floorPath))
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
                yield return new WaitForSeconds(0.1f);
            }

            string json = www.downloadHandler.text;
            //Logs.Instance.debug3D.text = json.Length.ToString();
            MeshDatawColor meshData = JsonConvert.DeserializeObject<MeshDatawColor>(json);
            Mesh mesh = ConvertToUnityMeshwColor(meshData);
            Mesh meshCopy = Instantiate(mesh);
            floor.GetComponent<MeshFilter>().mesh = mesh;
            floor.transform.localRotation = Quaternion.identity;
            floor.transform.localPosition = new Vector3(0, 0.1f, 0);
        }
    }

    private Mesh ConvertToUnityMesh(MeshData data)
    {
        Mesh mesh = new Mesh();

        // Convert vertices
        Vector3[] vertices = new Vector3[data.vertices.Count];
        for (int i = 0; i < data.vertices.Count; i++)
        {
            var v = data.vertices[i];
            vertices[i] = new Vector3(v[0], v[2], v[1]);
        }
        mesh.vertices = vertices;

        // Convert faces to triangles
        List<int> triangles = new List<int>();
        foreach (var face in data.faces)
        {
            if (face.Count == 3)
            {
                triangles.AddRange(face);
            }
            else if (face.Count == 4)
            {
                // Convert quad to 2 triangles
                triangles.Add(face[0]);
                triangles.Add(face[1]);
                triangles.Add(face[2]);

                triangles.Add(face[0]);
                triangles.Add(face[2]);
                triangles.Add(face[3]);
            }
        }

        mesh.triangles = triangles.ToArray();

        int[] tris = mesh.triangles;
        for (int i = 0; i < tris.Length; i += 3)
        {
            // swap order of second and third vertex
            int temp = tris[i + 1];
            tris[i + 1] = tris[i + 2];
            tris[i + 2] = temp;
        }
        mesh.triangles = tris;

        // Optional: calculate normals & bounds
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();

        return mesh;
    }
    private Mesh ConvertToUnityMeshwColor(MeshDatawColor data)
    {
        Mesh mesh = new Mesh();

        // Convert vertices
        Vector3[] vertices = new Vector3[data.vertices.Count];
        Color[] colors = new Color[data.vertices.Count];
        for (int i = 0; i < data.vertices.Count; i++)
        {
            var v = data.vertices[i];
            vertices[i] = new Vector3(v[0], v[2], v[1]);
            colors[i] = new Color(data.colors[i][0],
                data.colors[i][1],
                data.colors[i][2],
                data.colors[i][3]);
        }
        mesh.vertices = vertices;
        mesh.colors = colors;

        // Convert faces to triangles
        List<int> triangles = new List<int>();
        foreach (var face in data.faces)
        {
            if (face.Count == 3)
            {
                triangles.AddRange(face);
            }
            else if (face.Count == 4)
            {
                // Convert quad to 2 triangles
                triangles.Add(face[0]);
                triangles.Add(face[1]);
                triangles.Add(face[2]);

                triangles.Add(face[0]);
                triangles.Add(face[2]);
                triangles.Add(face[3]);
            }
        }

        mesh.triangles = triangles.ToArray();

        int[] tris = mesh.triangles;
        for (int i = 0; i < tris.Length; i += 3)
        {
            // swap order of second and third vertex
            int temp = tris[i + 1];
            tris[i + 1] = tris[i + 2];
            tris[i + 2] = temp;
        }
        mesh.triangles = tris;

        // Optional: calculate normals & bounds
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();

        return mesh;
    }
}
