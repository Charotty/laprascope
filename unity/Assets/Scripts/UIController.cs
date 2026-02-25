using UnityEngine;
using UnityEngine.UI;
using TMPro;
using System.Collections;
using System.IO;

public class UIController : MonoBehaviour
{
    [Header("UI Elements")]
    public Button uploadButton;
    public Button leftKidneyButton;
    public Button rightKidneyButton;
    public Button resetButton;
    public Button autoRotateButton;
    
    public Slider zoomSlider;
    public Slider rotationSpeedSlider;
    
    public TextMeshProUGUI statusText;
    public TextMeshProUGUI progressText;
    public TextMeshProUGUI infoText;
    
    public GameObject loadingPanel;
    public Slider progressBar;
    public TextMeshProUGUI loadingText;
    
    public GameObject errorPanel;
    public TextMeshProUGUI errorText;
    public Button errorCloseButton;
    
    [Header("References")]
    public NetworkManager networkManager;
    public ModelLoader modelLoader;
    
    [Header("Settings")]
    public float minZoom = 0.5f;
    public float maxZoom = 3f;
    public float minRotationSpeed = 0f;
    public float maxRotationSpeed = 180f;
    
    [Header("Debug")]
    public bool enableDebugLogs = true;
    
    private string currentJobId;
    private bool autoRotateEnabled = false;
    
    void Start()
    {
        InitializeUI();
        SetupEventListeners();
        
        if (enableDebugLogs)
            Debug.Log("UIController initialized");
    }
    
    /// <summary>
    /// Инициализирует UI элементы
    /// </summary>
    private void InitializeUI()
    {
        // Устанавливаем начальные значения
        zoomSlider.minValue = minZoom;
        zoomSlider.maxValue = maxZoom;
        zoomSlider.value = 1f;
        
        rotationSpeedSlider.minValue = minRotationSpeed;
        rotationSpeedSlider.maxValue = maxRotationSpeed;
        rotationSpeedSlider.value = 45f;
        
        // Скрываем панели
        loadingPanel.SetActive(false);
        errorPanel.SetActive(false);
        
        // Устанавливаем начальный текст
        UpdateStatus("Ready to upload DICOM files");
        UpdateProgress(0);
        UpdateInfo("Select a DICOM ZIP file to begin");
    }
    
    /// <summary>
    /// Устанавливает обработчики событий
    /// </summary>
    private void SetupEventListeners()
    {
        // Кнопки
        uploadButton.onClick.AddListener(OnUploadButtonClicked);
        leftKidneyButton.onClick.AddListener(() => OnKidneyButtonClicked("kidney_left"));
        rightKidneyButton.onClick.AddListener(() => OnKidneyButtonClicked("kidney_right"));
        resetButton.onClick.AddListener(OnResetButtonClicked);
        autoRotateButton.onClick.AddListener(OnAutoRotateButtonClicked);
        
        // Слайдеры
        zoomSlider.onValueChanged.AddListener(OnZoomSliderChanged);
        rotationSpeedSlider.onValueChanged.AddListener(OnRotationSpeedSliderChanged);
        
        // Панели
        errorCloseButton.onClick.AddListener(CloseErrorPanel);
        
        // NetworkManager события
        networkManager.OnUploadStarted += OnUploadStarted;
        networkManager.OnUploadCompleted += OnUploadCompleted;
        networkManager.OnUploadFailed += OnUploadFailed;
        networkManager.OnStatusUpdated += OnStatusUpdated;
        networkManager.OnProcessingCompleted += OnProcessingCompleted;
        networkManager.OnProcessingFailed += OnProcessingFailed;
        networkManager.OnSTLDownloaded += OnSTLDownloaded;
        networkManager.OnSTLDownloadFailed += OnSTLDownloadFailed;
        
        // ModelLoader события
        modelLoader.OnModelLoaded += OnModelLoaded;
        modelLoader.OnModelLoadFailed += OnModelLoadFailed;
    }
    
    /// <summary>
    /// Вызывается при нажатии кнопки загрузки
    /// </summary>
    private void OnUploadButtonClicked()
    {
        // Открываем диалог выбора файла
        string path = StandaloneFileBrowser.OpenFilePanel("Select DICOM ZIP file", "", "zip");
        
        if (!string.IsNullOrEmpty(path))
        {
            if (enableDebugLogs)
                Debug.Log($"Selected file: {path}");
            
            // Читаем файл и отправляем на сервер
            byte[] fileData = File.ReadAllBytes(path);
            networkManager.UploadDICOM(fileData);
        }
    }
    
    /// <summary>
    /// Вызывается при нажатии кнопки органа
    /// </summary>
    private void OnKidneyButtonClicked(string organ)
    {
        if (string.IsNullOrEmpty(currentJobId))
        {
            ShowError("No job available. Please upload DICOM files first.");
            return;
        }
        
        UpdateStatus($"Downloading {organ} STL...");
        networkManager.DownloadSTL(currentJobId, organ);
    }
    
    /// <summary>
    /// Вызывается при нажатии кнопки сброса
    /// </summary>
    private void OnResetButtonClicked()
    {
        modelLoader.UnloadModel();
        currentJobId = "";
        UpdateStatus("Ready to upload DICOM files");
        UpdateProgress(0);
        UpdateInfo("Select a DICOM ZIP file to begin");
    }
    
    /// <summary>
    /// Вызывается при нажатии кнопки авто-вращения
    /// </summary>
    private void OnAutoRotateButtonClicked()
    {
        autoRotateEnabled = !autoRotateEnabled;
        
        if (modelLoader.currentModel != null)
        {
            var controller = modelLoader.currentModel.GetComponent<ModelController>();
            if (controller != null)
            {
                controller.SetAutoRotate(autoRotateEnabled);
            }
        }
        
        UpdateAutoRotateButton();
    }
    
    /// <summary>
    /// Вызывается при изменении слайдера zoom
    /// </summary>
    private void OnZoomSliderChanged(float value)
    {
        if (modelLoader.currentModel != null)
        {
            var controller = modelLoader.currentModel.GetComponent<ModelController>();
            if (controller != null)
            {
                controller.SetZoom(value);
            }
        }
    }
    
    /// <summary>
    /// Вызывается при изменении слайдера скорости вращения
    /// </summary>
    private void OnRotationSpeedSliderChanged(float value)
    {
        if (modelLoader.currentModel != null)
        {
            var controller = modelLoader.currentModel.GetComponent<ModelController>();
            if (controller != null)
            {
                controller.SetRotationSpeed(value);
            }
        }
    }
    
    // NetworkManager обработчики событий
    
    private void OnUploadStarted(string message)
    {
        ShowLoading("Uploading files...");
        UpdateStatus(message);
    }
    
    private void OnUploadCompleted(string jobId)
    {
        currentJobId = jobId;
        UpdateStatus($"Processing... Job ID: {jobId}");
        UpdateInfo("Processing DICOM files. This may take a few minutes.");
    }
    
    private void OnUploadFailed(string errorType, string error)
    {
        HideLoading();
        ShowError($"Upload failed: {error}");
        UpdateStatus("Upload failed");
    }
    
    private void OnStatusUpdated(string jobId, int progress)
    {
        UpdateProgress(progress);
        UpdateStatus($"Processing... {progress}%");
    }
    
    private void OnProcessingCompleted(string jobId)
    {
        HideLoading();
        UpdateStatus("Processing completed! Ready to download STL files.");
        UpdateInfo("Select kidney to download and view 3D model.");
        
        // Активируем кнопки органов
        leftKidneyButton.interactable = true;
        rightKidneyButton.interactable = true;
    }
    
    private void OnProcessingFailed(string jobId)
    {
        HideLoading();
        ShowError("Processing failed. Please check your DICOM files and try again.");
        UpdateStatus("Processing failed");
    }
    
    private void OnSTLDownloaded(string filePath)
    {
        UpdateStatus("Loading 3D model...");
        modelLoader.LoadSTLModel(filePath);
    }
    
    private void OnSTLDownloadFailed(string jobId, string error)
    {
        ShowError($"Failed to download STL file: {error}");
        UpdateStatus("Download failed");
    }
    
    // ModelLoader обработчики событий
    
    private void OnModelLoaded(GameObject model)
    {
        HideLoading();
        UpdateStatus("3D model loaded successfully!");
        UpdateInfo("Use mouse to rotate, scroll to zoom, right-click to pan.");
        
        // Настраиваем контроллер модели
        var controller = model.GetComponent<ModelController>();
        if (controller != null)
        {
            controller.SetAutoRotate(autoRotateEnabled);
            controller.SetRotationSpeed(rotationSpeedSlider.value);
        }
        
        // Обновляем слайдеры
        zoomSlider.value = controller.GetCurrentZoom();
    }
    
    private void OnModelLoadFailed(string error)
    {
        HideLoading();
        ShowError($"Failed to load 3D model: {error}");
        UpdateStatus("Model loading failed");
    }
    
    // UI вспомогательные методы
    
    private void UpdateStatus(string message)
    {
        if (statusText != null)
            statusText.text = message;
        
        if (enableDebugLogs)
            Debug.Log($"Status: {message}");
    }
    
    private void UpdateProgress(int progress)
    {
        if (progressBar != null)
            progressBar.value = progress;
        
        if (progressText != null)
            progressText.text = $"{progress}%";
    }
    
    private void UpdateInfo(string message)
    {
        if (infoText != null)
            infoText.text = message;
    }
    
    private void ShowLoading(string message)
    {
        if (loadingPanel != null)
        {
            loadingPanel.SetActive(true);
            
            if (loadingText != null)
                loadingText.text = message;
        }
    }
    
    private void HideLoading()
    {
        if (loadingPanel != null)
            loadingPanel.SetActive(false);
    }
    
    private void ShowError(string message)
    {
        if (errorPanel != null)
        {
            errorPanel.SetActive(true);
            
            if (errorText != null)
                errorText.text = message;
        }
        
        if (enableDebugLogs)
            Debug.LogError($"Error: {message}");
    }
    
    private void CloseErrorPanel()
    {
        if (errorPanel != null)
            errorPanel.SetActive(false);
    }
    
    private void UpdateAutoRotateButton()
    {
        if (autoRotateButton != null)
        {
            var buttonText = autoRotateButton.GetComponentInChildren<TextMeshProUGUI>();
            if (buttonText != null)
            {
                buttonText.text = autoRotateEnabled ? "Stop Auto-Rotate" : "Start Auto-Rotate";
            }
            
            var buttonColors = autoRotateButton.colors;
            buttonColors.normalColor = autoRotateEnabled ? Color.green : Color.white;
            autoRotateButton.colors = buttonColors;
        }
    }
    
    void OnDestroy()
    {
        // Отписываемся от событий
        if (networkManager != null)
        {
            networkManager.OnUploadStarted -= OnUploadStarted;
            networkManager.OnUploadCompleted -= OnUploadCompleted;
            networkManager.OnUploadFailed -= OnUploadFailed;
            networkManager.OnStatusUpdated -= OnStatusUpdated;
            networkManager.OnProcessingCompleted -= OnProcessingCompleted;
            networkManager.OnProcessingFailed -= OnProcessingFailed;
            networkManager.OnSTLDownloaded -= OnSTLDownloaded;
            networkManager.OnSTLDownloadFailed -= OnSTLDownloadFailed;
        }
        
        if (modelLoader != null)
        {
            modelLoader.OnModelLoaded -= OnModelLoaded;
            modelLoader.OnModelLoadFailed -= OnModelLoadFailed;
        }
    }
}
