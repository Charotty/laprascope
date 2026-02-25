using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using Newtonsoft.Json;
using System;

public class NetworkManager : MonoBehaviour
{
    [Header("API Configuration")]
    public string baseUrl = "http://localhost:8000/api/v1";
    public float statusCheckInterval = 2f;
    
    [Header("Debug")]
    public bool enableDebugLogs = true;
    
    // События для UI
    public System.Action<string> OnUploadStarted;
    public System.Action<string> OnUploadCompleted;
    public System.Action<string, string> OnUploadFailed;
    public System.Action<string, int> OnStatusUpdated;
    public System.Action<string> OnProcessingCompleted;
    public System.Action<string> OnProcessingFailed;
    public System.Action<string> OnSTLDownloaded;
    public System.Action<string, string> OnSTLDownloadFailed;
    
    private Coroutine statusCheckCoroutine;
    private string currentJobId;
    
    void Start()
    {
        if (enableDebugLogs)
            Debug.Log("NetworkManager initialized");
    }
    
    /// <summary>
    /// Загружает ZIP архив с DICOM файлами на сервер
    /// </summary>
    /// <param name="zipData">Данные ZIP файла в виде байтов</param>
    public void UploadDICOM(byte[] zipData)
    {
        StartCoroutine(UploadDICOMCoroutine(zipData));
    }
    
    private IEnumerator UploadDICOMCoroutine(byte[] zipData)
    {
        OnUploadStarted?.Invoke("Uploading DICOM files...");
        
        if (enableDebugLogs)
            Debug.Log($"Starting DICOM upload. File size: {zipData.Length} bytes");
        
        // Создаем WWWForm для загрузки файла
        WWWForm form = new WWWForm();
        form.AddBinaryData("file", zipData, "dicom_files.zip", "application/zip");
        
        using (UnityWebRequest request = UnityWebRequest.Post($"{baseUrl}/upload", form))
        {
            request.SetRequestHeader("Accept", "application/json");
            
            if (enableDebugLogs)
                Debug.Log($"Sending request to: {request.url}");
            
            yield return request.SendWebRequest();
            
            if (request.result == UnityWebRequest.Result.Success)
            {
                try
                {
                    var response = JsonConvert.DeserializeObject<UploadResponse>(request.downloadHandler.text);
                    currentJobId = response.job_id;
                    
                    if (enableDebugLogs)
                        Debug.Log($"Upload successful. Job ID: {currentJobId}");
                    
                    OnUploadCompleted?.Invoke(currentJobId);
                    
                    // Начинаем проверку статуса
                    StartStatusCheck();
                }
                catch (System.Exception e)
                {
                    string error = $"Failed to parse upload response: {e.Message}";
                    Debug.LogError(error);
                    OnUploadFailed?.Invoke("upload_parse_error", error);
                }
            }
            else
            {
                string error = $"Upload failed: {request.error} (Code: {request.responseCode})";
                Debug.LogError(error);
                OnUploadFailed?.Invoke("upload_failed", error);
            }
        }
    }
    
    /// <summary>
    /// Начинает периодическую проверку статуса задачи
    /// </summary>
    public void StartStatusCheck()
    {
        if (string.IsNullOrEmpty(currentJobId))
        {
            Debug.LogError("Cannot start status check: no job ID available");
            return;
        }
        
        // Останавливаем предыдущую проверку если была
        StopStatusCheck();
        
        if (enableDebugLogs)
            Debug.Log($"Starting status check for job: {currentJobId}");
        
        statusCheckCoroutine = StartCoroutine(StatusCheckCoroutine());
    }
    
    /// <summary>
    /// Останавливает проверку статуса
    /// </summary>
    public void StopStatusCheck()
    {
        if (statusCheckCoroutine != null)
        {
            StopCoroutine(statusCheckCoroutine);
            statusCheckCoroutine = null;
            
            if (enableDebugLogs)
                Debug.Log("Status check stopped");
        }
    }
    
    /// <summary>
    /// Проверяет статус конкретной задачи
    /// </summary>
    /// <param name="jobId">ID задачи</param>
    public void CheckStatus(string jobId)
    {
        StartCoroutine(CheckStatusCoroutine(jobId));
    }
    
    private IEnumerator StatusCheckCoroutine()
    {
        while (!string.IsNullOrEmpty(currentJobId))
        {
            yield return CheckStatusCoroutine(currentJobId);
            yield return new WaitForSeconds(statusCheckInterval);
        }
    }
    
    private IEnumerator CheckStatusCoroutine(string jobId)
    {
        using (UnityWebRequest request = UnityWebRequest.Get($"{baseUrl}/status/{jobId}"))
        {
            request.SetRequestHeader("Accept", "application/json");
            
            yield return request.SendWebRequest();
            
            if (request.result == UnityWebRequest.Result.Success)
            {
                try
                {
                    var response = JsonConvert.DeserializeObject<StatusResponse>(request.downloadHandler.text);
                    
                    if (enableDebugLogs)
                        Debug.Log($"Status update: {response.status} (Progress: {response.progress}%)");
                    
                    OnStatusUpdated?.Invoke(jobId, response.progress);
                    
                    // Проверяем завершение
                    if (response.status == "completed")
                    {
                        OnProcessingCompleted?.Invoke(jobId);
                        StopStatusCheck();
                    }
                    else if (response.status == "error")
                    {
                        OnProcessingFailed?.Invoke(jobId);
                        StopStatusCheck();
                    }
                }
                catch (System.Exception e)
                {
                    Debug.LogError($"Failed to parse status response: {e.Message}");
                }
            }
            else
            {
                Debug.LogWarning($"Status check failed: {request.error}");
            }
        }
    }
    
    /// <summary>
    /// Скачивает STL файл конкретного органа
    /// </summary>
    /// <param name="jobId">ID задачи</param>
    /// <param name="organ">Название органа ('kidney_left' или 'kidney_right')</param>
    public void DownloadSTL(string jobId, string organ)
    {
        StartCoroutine(DownloadSTLCoroutine(jobId, organ));
    }
    
    private IEnumerator DownloadSTLCoroutine(string jobId, string organ)
    {
        string url = $"{baseUrl}/stl/{jobId}/{organ}";
        
        if (enableDebugLogs)
            Debug.Log($"Downloading STL: {url}");
        
        using (UnityWebRequest request = UnityWebRequest.Get(url))
        {
            yield return request.SendWebRequest();
            
            if (request.result == UnityWebRequest.Result.Success)
            {
                try
                {
                    // Сохраняем STL файл
                    string fileName = $"{jobId}_{organ}.stl";
                    string filePath = System.IO.Path.Combine(Application.persistentDataPath, fileName);
                    System.IO.File.WriteAllBytes(filePath, request.downloadHandler.data);
                    
                    if (enableDebugLogs)
                        Debug.Log($"STL downloaded and saved: {filePath}");
                    
                    OnSTLDownloaded?.Invoke(filePath);
                }
                catch (System.Exception e)
                {
                    string error = $"Failed to save STL file: {e.Message}";
                    Debug.LogError(error);
                    OnSTLDownloadFailed?.Invoke(jobId, error);
                }
            }
            else
            {
                string error = $"STL download failed: {request.error} (Code: {request.responseCode})";
                Debug.LogError(error);
                OnSTLDownloadFailed?.Invoke(jobId, error);
            }
        }
    }
    
    /// <summary>
    /// Получает список всех задач
    /// </summary>
    public void GetJobs(System.Action<JobsResponse> callback)
    {
        StartCoroutine(GetJobsCoroutine(callback));
    }
    
    private IEnumerator GetJobsCoroutine(System.Action<JobsResponse> callback)
    {
        using (UnityWebRequest request = UnityWebRequest.Get($"{baseUrl}/jobs"))
        {
            request.SetRequestHeader("Accept", "application/json");
            
            yield return request.SendWebRequest();
            
            if (request.result == UnityWebRequest.Result.Success)
            {
                try
                {
                    var response = JsonConvert.DeserializeObject<JobsResponse>(request.downloadHandler.text);
                    callback?.Invoke(response);
                }
                catch (System.Exception e)
                {
                    Debug.LogError($"Failed to parse jobs response: {e.Message}");
                    callback?.Invoke(null);
                }
            }
            else
            {
                Debug.LogError($"Failed to get jobs: {request.error}");
                callback?.Invoke(null);
            }
        }
    }
    
    void OnDestroy()
    {
        StopStatusCheck();
    }
    
    // JSON классы для ответов API
    [System.Serializable]
    public class UploadResponse
    {
        public string job_id;
        public string status;
        public string message;
        public int files_count;
    }
    
    [System.Serializable]
    public class StatusResponse
    {
        public string job_id;
        public string status;
        public int progress;
        public string created_at;
        public string updated_at;
        public Dictionary<string, object> segmentation;
        public Dictionary<string, object> conversion;
    }
    
    [System.Serializable]
    public class JobsResponse
    {
        public Dictionary<string, StatusResponse> jobs;
        public int total;
    }
}
