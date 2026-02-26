using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System;
using Newtonsoft.Json;
using System.Threading.Tasks;

/// <summary>
/// API client for AR Laparoscopy backend
/// Handles upload, status polling, and download of STL + metadata
/// </summary>
public class LaparoscopyAPI : MonoBehaviour
{
    [Header("API Configuration")]
    [SerializeField] private string baseUrl = "http://5.42.97.143:8000";
    [SerializeField] private float statusPollInterval = 2.0f;
    [SerializeField] private int maxRetries = 3;
    [SerializeField] private float requestTimeout = 30.0f;
    
    [Header("Cache Configuration")]
    [SerializeField] private string cacheFolder = "LaparoscopyCache";
    [SerializeField] private float cacheMaxAgeHours = 24.0f;
    
    private string cachePath;
    
    // Job status types
    public enum JobStatus
    {
        Pending,
        Processing,
        SegmentationDone,
        ConversionDone,
        Completed,
        Error,
        Unknown
    }
    
    // Data structures
    [System.Serializable]
    public class JobInfo
    {
        public string job_id;
        public string status;
        public string created_at;
        public string updated_at;
        public string patient_fio;
        public Dictionary<string, object> results;
        public Dictionary<string, object> metadata;
        public string error;
    }
    
    [System.Serializable]
    public class Metadata
    {
        public string job_id;
        public string generated_at;
        public string units;
        public string coordinate_system;
        public Dictionary<string, string> axis_meaning;
        public Dictionary<string, OrganData> organs;
    }
    
    [System.Serializable]
    public class OrganData
    {
        public Dictionary<string, AnchorData> anchors;
    }
    
    [System.Serializable]
    public class AnchorData
    {
        public float[] point;
        public float[] displacement;
    }
    
    private void Awake()
    {
        // Initialize cache path
        cachePath = Path.Combine(Application.persistentDataPath, cacheFolder);
        if (!Directory.Exists(cachePath))
        {
            Directory.CreateDirectory(cachePath);
        }
        
        Debug.Log($"LaparoscopyAPI initialized with cache at: {cachePath}");
    }
    
    /// <summary>
    /// Upload DICOM ZIP file to server
    /// </summary>
    public async Task<string> UploadDicomZip(string zipFilePath, string patientFio = null)
    {
        if (!File.Exists(zipFilePath))
        {
            throw new FileNotFoundException($"ZIP file not found: {zipFilePath}");
        }
        
        string url = $"{baseUrl}/api/v1/upload";
        
        // Create form data
        WWWForm form = new WWWForm();
        byte[] fileData = File.ReadAllBytes(zipFilePath);
        form.AddBinaryData("file", fileData, Path.GetFileName(zipFilePath), "application/zip");
        
        if (!string.IsNullOrEmpty(patientFio))
        {
            form.AddField("patient_fio", patientFio);
        }
        
        using (UnityWebRequest request = UnityWebRequest.Post(url, form))
        {
            request.timeout = (int)requestTimeout;
            
            var operation = request.SendWebRequest();
            
            while (!operation.isDone)
            {
                await Task.Yield();
            }
            
            if (request.result == UnityWebRequest.Result.Success)
            {
                string responseText = request.downloadHandler.text;
                var response = JsonConvert.DeserializeObject<Dictionary<string, object>>(responseText);
                
                if (response.ContainsKey("job_id"))
                {
                    string jobId = response["job_id"].ToString();
                    Debug.Log($"Upload successful. Job ID: {jobId}");
                    return jobId;
                }
                else
                {
                    throw new System.Exception("No job_id in response");
                }
            }
            else
            {
                throw new System.Exception($"Upload failed: {request.error}");
            }
        }
    }
    
    /// <summary>
    /// Get job status
    /// </summary>
    public async Task<JobInfo> GetJobStatus(string jobId)
    {
        string url = $"{baseUrl}/api/v1/status/{jobId}";
        
        using (UnityWebRequest request = UnityWebRequest.Get(url))
        {
            request.timeout = (int)requestTimeout;
            
            var operation = request.SendWebRequest();
            
            while (!operation.isDone)
            {
                await Task.Yield();
            }
            
            if (request.result == UnityWebRequest.Result.Success)
            {
                string responseText = request.downloadHandler.text;
                return JsonConvert.DeserializeObject<JobInfo>(responseText);
            }
            else
            {
                throw new System.Exception($"Status request failed: {request.error}");
            }
        }
    }
    
    /// <summary>
    /// Poll job status until completion or error
    /// </summary>
    public async Task<JobInfo> PollJobUntilComplete(string jobId, System.Action<JobInfo> onStatusUpdate = null)
    {
        int attempts = 0;
        
        while (attempts < maxRetries * 60) // Max ~2 hours with 2s interval
        {
            try
            {
                JobInfo status = await GetJobStatus(jobId);
                onStatusUpdate?.Invoke(status);
                
                JobStatus jobStatus = ParseJobStatus(status.status);
                
                if (jobStatus == JobStatus.Completed)
                {
                    Debug.Log($"Job {jobId} completed successfully");
                    return status;
                }
                else if (jobStatus == JobStatus.Error)
                {
                    throw new System.Exception($"Job {jobId} failed: {status.error}");
                }
                
                // Wait before next poll
                await Task.Delay((int)(statusPollInterval * 1000));
                attempts++;
            }
            catch (Exception e)
            {
                attempts++;
                if (attempts >= maxRetries)
                {
                    throw;
                }
                
                Debug.LogWarning($"Status poll attempt {attempts} failed: {e.Message}");
                await Task.Delay((int)(statusPollInterval * 1000));
            }
        }
        
        throw new TimeoutException($"Job {jobId} did not complete within timeout");
    }
    
    /// <summary>
    /// Get metadata for a job
    /// </summary>
    public async Task<Metadata> GetMetadata(string jobId)
    {
        // Check cache first
        string cacheFile = Path.Combine(cachePath, $"{jobId}_metadata.json");
        
        if (File.Exists(cacheFile))
        {
            var fileInfo = new FileInfo(cacheFile);
            if (DateTime.Now - fileInfo.LastWriteTime < TimeSpan.FromHours(cacheMaxAgeHours))
            {
                string cachedJson = File.ReadAllText(cacheFile);
                return JsonConvert.DeserializeObject<Metadata>(cachedJson);
            }
        }
        
        // Download from server
        string url = $"{baseUrl}/api/v1/metadata/{jobId}";
        
        using (UnityWebRequest request = UnityWebRequest.Get(url))
        {
            request.timeout = (int)requestTimeout;
            
            var operation = request.SendWebRequest();
            
            while (!operation.isDone)
            {
                await Task.Yield();
            }
            
            if (request.result == UnityWebRequest.Result.Success)
            {
                string responseText = request.downloadHandler.text;
                var metadata = JsonConvert.DeserializeObject<Metadata>(responseText);
                
                // Cache the metadata
                File.WriteAllText(cacheFile, responseText);
                
                return metadata;
            }
            else
            {
                throw new System.Exception($"Metadata request failed: {request.error}");
            }
        }
    }
    
    /// <summary>
    /// Download STL file for a specific organ
    /// </summary>
    public async Task<string> DownloadSTL(string jobId, string organ)
    {
        // Check cache first
        string cacheFile = Path.Combine(cachePath, $"{jobId}_{organ}.stl");
        
        if (File.Exists(cacheFile))
        {
            var fileInfo = new FileInfo(cacheFile);
            if (DateTime.Now - fileInfo.LastWriteTime < TimeSpan.FromHours(cacheMaxAgeHours))
            {
                Debug.Log($"Using cached STL: {cacheFile}");
                return cacheFile;
            }
        }
        
        // Download from server
        string url = $"{baseUrl}/api/v1/stl/{jobId}/{organ}";
        
        using (UnityWebRequest request = UnityWebRequest.Get(url))
        {
            request.timeout = (int)requestTimeout;
            
            var operation = request.SendWebRequest();
            
            while (!operation.isDone)
            {
                await Task.Yield();
            }
            
            if (request.result == UnityWebRequest.Result.Success)
            {
                // Save to cache
                File.WriteAllBytes(cacheFile, request.downloadHandler.data);
                Debug.Log($"Downloaded STL to: {cacheFile}");
                return cacheFile;
            }
            else
            {
                throw new System.Exception($"STL download failed: {request.error}");
            }
        }
    }
    
    /// <summary>
    /// Download all files for a job (STL + metadata)
    /// </summary>
    public async Task<JobFiles> DownloadAllJobFiles(string jobId)
    {
        var jobFiles = new JobFiles();
        
        try
        {
            // Get metadata
            jobFiles.metadata = await GetMetadata(jobId);
            
            // Download STL files for available organs
            if (jobFiles.metadata.organs.ContainsKey("kidney_left"))
            {
                jobFiles.kidneyLeftPath = await DownloadSTL(jobId, "kidney_left");
            }
            
            if (jobFiles.metadata.organs.ContainsKey("kidney_right"))
            {
                jobFiles.kidneyRightPath = await DownloadSTL(jobId, "kidney_right");
            }
            
            Debug.Log($"Downloaded all files for job {jobId}");
            return jobFiles;
        }
        catch (Exception e)
        {
            Debug.LogError($"Failed to download job files: {e.Message}");
            throw;
        }
    }
    
    /// <summary>
    /// Link patient to existing job
    /// </summary>
    public async Task<bool> LinkPatientToJob(string jobId, string patientFio)
    {
        string url = $"{baseUrl}/api/v1/metadata/{jobId}/link-patient";
        
        WWWForm form = new WWWForm();
        form.AddField("patient_fio", patientFio);
        
        using (UnityWebRequest request = UnityWebRequest.Post(url, form))
        {
            request.timeout = (int)requestTimeout;
            
            var operation = request.SendWebRequest();
            
            while (!operation.isDone)
            {
                await Task.Yield();
            }
            
            if (request.result == UnityWebRequest.Result.Success)
            {
                Debug.Log($"Linked patient '{patientFio}' to job {jobId}");
                return true;
            }
            else
            {
                Debug.LogError($"Failed to link patient: {request.error}");
                return false;
            }
        }
    }
    
    /// <summary>
    /// Clean up old cache files
    /// </summary>
    public void CleanupCache()
    {
        if (!Directory.Exists(cachePath))
            return;
        
        var cutoffTime = DateTime.Now - TimeSpan.FromHours(cacheMaxAgeHours);
        
        foreach (var file in Directory.GetFiles(cachePath))
        {
            var fileInfo = new FileInfo(file);
            if (fileInfo.LastWriteTime < cutoffTime)
            {
                file.Delete();
                Debug.Log($"Deleted old cache file: {file}");
            }
        }
    }
    
    // Helper methods
    private JobStatus ParseJobStatus(string status)
    {
        switch (status?.ToLower())
        {
            case "pending":
                return JobStatus.Pending;
            case "processing":
            case "segmentation_done":
            case "conversion_done":
                return JobStatus.Processing;
            case "completed":
                return JobStatus.Completed;
            case "error":
                return JobStatus.Error;
            default:
                return JobStatus.Unknown;
        }
    }
    
    // Data structures
    [System.Serializable]
    public class JobFiles
    {
        public Metadata metadata;
        public string kidneyLeftPath;
        public string kidneyRightPath;
    }
}
