using UnityEngine;
using System.Collections.Generic;
using Newtonsoft.Json;

/// <summary>
/// Visualizes kidney displacement vectors from metadata
/// Shows anchors (upper_pole, hilum, lower_pole) and displacement arrows
/// </summary>
public class DisplacementVisualizer : MonoBehaviour
{
    [Header("Visualization Settings")]
    [SerializeField] private Material anchorMaterial;
    [SerializeField] private Material displacementArrowMaterial;
    [SerializeField] private Material kidneyMaterial;
    [SerializeField] private float anchorSphereRadius = 0.5f;
    [SerializeField] private float arrowScale = 1.0f;
    [SerializeField] private bool showDisplacementText = true;
    [SerializeField] private Color arrowColor = Color.red;
    [SerializeField] private Color anchorColor = Color.blue;
    
    [Header("Coordinate System")]
    [SerializeField] private bool flipX = false;
    [SerializeField] private bool flipY = false;
    [SerializeField] private bool flipZ = false;
    [SerializeField] private float coordinateScale = 1.0f; // Scale factor for measurement system
    
    private Dictionary<string, GameObject> kidneyObjects = new Dictionary<string, GameObject>();
    private Dictionary<string, Dictionary<string, GameObject>> anchorObjects = new Dictionary<string, Dictionary<string, GameObject>>();
    private Dictionary<string, Dictionary<string, GameObject>> arrowObjects = new Dictionary<string, Dictionary<string, GameObject>>();
    
    // Reference to API
    private LaparoscopyAPI api;
    
    private void Awake()
    {
        api = GetComponent<LaparoscopyAPI>();
        if (api == null)
        {
            Debug.LogError("LaparoscopyAPI component required!");
            enabled = false;
        }
        
        // Create default materials if not assigned
        if (anchorMaterial == null)
            anchorMaterial = CreateDefaultMaterial(Color.blue);
        if (displacementArrowMaterial == null)
            displacementArrowMaterial = CreateDefaultMaterial(Color.red);
        if (kidneyMaterial == null)
            kidneyMaterial = CreateDefaultMaterial(Color.white);
    }
    
    /// <summary>
    /// Load and visualize displacement data for a job
    /// </summary>
    public async void LoadAndVisualizeJob(string jobId)
    {
        try
        {
            Debug.Log($"Loading displacement data for job: {jobId}");
            
            // Download all files
            var jobFiles = await api.DownloadAllJobFiles(jobId);
            
            // Clear previous visualization
            ClearVisualization();
            
            // Load and visualize kidneys
            if (!string.IsNullOrEmpty(jobFiles.kidneyLeftPath))
            {
                await LoadAndVisualizeKidney("kidney_left", jobFiles.kidneyLeftPath, jobFiles.metadata);
            }
            
            if (!string.IsNullOrEmpty(jobFiles.kidneyRightPath))
            {
                await LoadAndVisualizeKidney("kidney_right", jobFiles.kidneyRightPath, jobFiles.metadata);
            }
            
            Debug.Log($"Successfully visualized displacement for job {jobId}");
        }
        catch (System.Exception e)
        {
            Debug.LogError($"Failed to visualize job {jobId}: {e.Message}");
        }
    }
    
    /// <summary>
    /// Load kidney STL and create displacement visualization
    /// </summary>
    private async System.Threading.Tasks.Task LoadAndVisualizeKidney(string organName, string stlPath, LaparoscopyAPI.Metadata metadata)
    {
        // Load STL mesh
        Mesh kidneyMesh = await LoadSTLMesh(stlPath);
        if (kidneyMesh == null)
        {
            Debug.LogError($"Failed to load kidney mesh from {stlPath}");
            return;
        }
        
        // Create kidney object
        GameObject kidneyObj = new GameObject($"Kidney_{organName}");
        kidneyObj.transform.SetParent(transform);
        
        var meshFilter = kidneyObj.AddComponent<MeshFilter>();
        var meshRenderer = kidneyObj.AddComponent<MeshRenderer>();
        
        meshFilter.mesh = kidneyMesh;
        meshRenderer.material = kidneyMaterial;
        
        // Position kidney based on coordinate system
        PositionKidneyInMeasurementSpace(kidneyObj, organName);
        
        kidneyObjects[organName] = kidneyObj;
        
        // Create displacement visualization
        if (metadata.organs.ContainsKey(organName))
        {
            CreateDisplacementVisualization(organName, kidneyObj, metadata.organs[organName]);
        }
    }
    
    /// <summary>
    /// Position kidney in measurement coordinate system
    /// </summary>
    private void PositionKidneyInMeasurementSpace(GameObject kidneyObj, string organName)
    {
        // Apply coordinate system transformations
        Vector3 position = Vector3.zero;
        Vector3 scale = Vector3.one * coordinateScale;
        
        if (flipX) scale.x *= -1;
        if (flipY) scale.y *= -1;
        if (flipZ) scale.z *= -1;
        
        // Apply position offset based on organ (left/right)
        if (organName == "kidney_left")
        {
            position.x = -5.0f; // Offset to the left
        }
        else if (organName == "kidney_right")
        {
            position.x = 5.0f; // Offset to the right
        }
        
        kidneyObj.transform.localPosition = position;
        kidneyObj.transform.localScale = scale;
    }
    
    /// <summary>
    /// Create displacement visualization for a kidney
    /// </summary>
    private void CreateDisplacementVisualization(string organName, GameObject kidneyObj, LaparoscopyAPI.OrganData organData)
    {
        if (organData.anchors == null)
        {
            Debug.LogWarning($"No anchors found for {organName}");
            return;
        }
        
        anchorObjects[organName] = new Dictionary<string, GameObject>();
        arrowObjects[organName] = new Dictionary<string, GameObject>();
        
        foreach (var anchorPair in organData.anchors)
        {
            string anchorName = anchorPair.Key;
            var anchorData = anchorPair.Value;
            
            // Convert anchor point from measurement system to Unity world
            Vector3 anchorPoint = ConvertMeasurementToUnity(anchorData.point);
            
            // Create anchor sphere
            GameObject anchorSphere = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            anchorSphere.name = $"Anchor_{anchorName}";
            anchorSphere.transform.SetParent(kidneyObj.transform);
            anchorSphere.transform.localPosition = anchorPoint;
            anchorSphere.transform.localScale = Vector3.one * anchorSphereRadius;
            
            var anchorRenderer = anchorSphere.GetComponent<Renderer>();
            anchorRenderer.material = anchorMaterial;
            
            anchorObjects[organName][anchorName] = anchorSphere;
            
            // Create displacement arrow
            if (anchorData.displacement != null && anchorData.displacement.Length >= 3)
            {
                Vector3 displacement = ConvertMeasurementToUnity(anchorData.displacement);
                
                if (displacement.magnitude > 0.01f) // Only show significant displacements
                {
                    GameObject arrow = CreateDisplacementArrow(anchorPoint, displacement);
                    arrow.transform.SetParent(kidneyObj.transform);
                    arrowObjects[organName][anchorName] = arrow;
                    
                    // Add text label if enabled
                    if (showDisplacementText)
                    {
                        CreateDisplacementLabel(arrow, displacement);
                    }
                }
            }
        }
    }
    
    /// <summary>
    /// Convert measurement system coordinates to Unity world coordinates
    /// </summary>
    private Vector3 ConvertMeasurementToUnity(float[] measurementCoords)
    {
        if (measurementCoords == null || measurementCoords.Length < 3)
            return Vector3.zero;
        
        // Convert from measurement system to Unity
        // Note: This is a simplified conversion - you may need to adjust based on your measurement system
        Vector3 unityCoords = new Vector3(
            measurementCoords[0] * coordinateScale,
            measurementCoords[1] * coordinateScale,
            measurementCoords[2] * coordinateScale
        );
        
        // Apply flips if needed
        if (flipX) unityCoords.x *= -1;
        if (flipY) unityCoords.y *= -1;
        if (flipZ) unityCoords.z *= -1;
        
        return unityCoords;
    }
    
    /// <summary>
    /// Create displacement arrow
    /// </summary>
    private GameObject CreateDisplacementArrow(Vector3 startPoint, Vector3 displacement)
    {
        GameObject arrow = new GameObject("DisplacementArrow");
        
        // Create arrow shaft (cylinder)
        GameObject shaft = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        shaft.name = "ArrowShaft";
        shaft.transform.SetParent(arrow.transform);
        
        // Scale and position shaft
        float shaftLength = displacement.magnitude * arrowScale;
        shaft.transform.localScale = new Vector3(0.1f, shaftLength / 2f, 0.1f);
        
        // Position shaft at midpoint
        Vector3 midPoint = startPoint + displacement / 2;
        shaft.transform.localPosition = midPoint;
        
        // Orient shaft along displacement direction
        shaft.transform.rotation = Quaternion.FromToRotation(Vector3.up, displacement.normalized * arrowScale);
        
        // Create arrow head (cone)
        GameObject head = GameObject.CreatePrimitive(PrimitiveType.Cone);
        head.name = "ArrowHead";
        head.transform.SetParent(arrow.transform);
        
        head.transform.localScale = new Vector3(0.3f, 0.5f, 0.3f);
        head.transform.localPosition = startPoint + displacement;
        head.transform.rotation = Quaternion.FromToRotation(Vector3.up, displacement.normalized * arrowScale);
        
        // Apply materials
        var shaftRenderer = shaft.GetComponent<Renderer>();
        var headRenderer = head.GetComponent<Renderer>();
        shaftRenderer.material = displacementArrowMaterial;
        headRenderer.material = displacementArrowMaterial;
        
        // Set color
        displacementArrowMaterial.color = arrowColor;
        
        return arrow;
    }
    
    /// <summary>
    /// Create displacement label
    /// </summary>
    private void CreateDisplacementLabel(GameObject arrow, Vector3 displacement)
    {
        // This would require a TextMesh or UI Text component
        // For simplicity, we'll just log the displacement
        float magnitude = displacement.magnitude;
        Debug.Log($"Displacement magnitude: {magnitude:F2} mm");
        
        // TODO: Add 3D text label showing displacement magnitude
    }
    
    /// <summary>
    /// Load STL mesh from file
    /// </summary>
    private async System.Threading.Tasks.Task<Mesh> LoadSTLMesh(string stlPath)
    {
        // This is a simplified STL loader
        // In production, you'd want a proper STL parser
        
        try
        {
            byte[] stlData = System.IO.File.ReadAllBytes(stlPath);
            
            // TODO: Implement proper STL parsing
            // For now, create a placeholder mesh
            Mesh mesh = new Mesh();
            mesh.name = $"KidneyMesh_{Path.GetFileNameWithoutExtension(stlPath)}";
            
            // Create a simple kidney-shaped placeholder
            CreatePlaceholderKidneyMesh(mesh);
            
            return mesh;
        }
        catch (System.Exception e)
        {
            Debug.LogError($"Failed to load STL: {e.Message}");
            return null;
        }
    }
    
    /// <summary>
    /// Create placeholder kidney mesh (simplified ellipsoid)
    /// </summary>
    private void CreatePlaceholderKidneyMesh(Mesh mesh)
    {
        // Create a bean-shaped mesh as placeholder
        int segments = 16;
        int rings = 8;
        
        List<Vector3> vertices = new List<Vector3>();
        List<int> triangles = new List<int>();
        
        // Generate vertices
        for (int i = 0; i <= rings; i++)
        {
            float v = (float)i / rings;
            float y = (v - 0.5f) * 4f; // Height
            float radius = Mathf.Sqrt(1f - (v - 0.5f) * (v - 0.5f)) * 2f; // Bean shape
            
            for (int j = 0; j <= segments; j++)
            {
                float u = (float)j / segments;
                float angle = u * 2f * Mathf.PI;
                
                float x = Mathf.Cos(angle) * radius;
                float z = Mathf.Sin(angle) * radius;
                
                vertices.Add(new Vector3(x, y, z));
            }
        }
        
        // Generate triangles
        for (int i = 0; i < rings; i++)
        {
            for (int j = 0; j < segments; j++)
            {
                int current = i * (segments + 1) + j;
                int next = current + segments + 1;
                
                triangles.Add(current);
                triangles.Add(next);
                triangles.Add(current + 1);
                
                triangles.Add(current + 1);
                triangles.Add(next);
                triangles.Add(next + 1);
            }
        }
        
        mesh.vertices = vertices.ToArray();
        mesh.triangles = triangles.ToArray();
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();
    }
    
    /// <summary>
    /// Clear all visualization objects
    /// </summary>
    public void ClearVisualization()
    {
        // Destroy kidney objects
        foreach (var kvp in kidneyObjects)
        {
            if (kvp.Value != null)
            {
                DestroyImmediate(kvp.Value);
            }
        }
        kidneyObjects.Clear();
        
        // Destroy anchor and arrow objects
        foreach (var organAnchors in anchorObjects.Values)
        {
            foreach (var anchor in organAnchors.Values)
            {
                if (anchor != null)
                {
                    DestroyImmediate(anchor);
                }
            }
        }
        anchorObjects.Clear();
        
        foreach (var organArrows in arrowObjects.Values)
        {
            foreach (var arrow in organArrows.Values)
            {
                if (arrow != null)
                {
                    DestroyImmediate(arrow);
                }
            }
        }
        arrowObjects.Clear();
    }
    
    /// <summary>
    /// Toggle visibility of displacement arrows
    /// </summary>
    public void ToggleDisplacementArrows(bool show)
    {
        foreach (var organArrows in arrowObjects.Values)
        {
            foreach (var arrow in organArrows.Values)
            {
                if (arrow != null)
                {
                    arrow.SetActive(show);
                }
            }
        }
    }
    
    /// <summary>
    /// Toggle visibility of anchor points
    /// </summary>
    public void ToggleAnchorPoints(bool show)
    {
        foreach (var organAnchors in anchorObjects.Values)
        {
            foreach (var anchor in organAnchors.Values)
            {
                if (anchor != null)
                {
                    anchor.SetActive(show);
                }
            }
        }
    }
    
    private Material CreateDefaultMaterial(Color color)
    {
        Material mat = new Material(Shader.Find("Standard"));
        mat.color = color;
        return mat;
    }
}
