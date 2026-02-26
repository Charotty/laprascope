using UnityEngine;
using UnityEngine.UI;
using TMPro;
using System.Threading.Tasks;
using System.Collections;

/// <summary>
/// UI controller for AR Laparoscopy application
/// Handles file upload, job monitoring, and visualization controls
/// </summary>
public class LaparoscopyUI : MonoBehaviour
{
    [Header("UI Components")]
    [SerializeField] private Button uploadButton;
    [SerializeField] private Button refreshButton;
    [SerializeField] private Button clearButton;
    [SerializeField] private TMP_InputField patientFioInput;
    [SerializeField] private TMP_Text statusText;
    [SerializeField] private TMP_Text jobIdText;
    [SerializeField] private Slider progressSlider;
    [SerializeField] private TMP_Text progressText;
    
    [Header("Visualization Controls")]
    [SerializeField] private Toggle showArrowsToggle;
    [SerializeField] private Toggle showAnchorsToggle;
    [SerializeField] private Button resetViewButton;
    
    [Header("File Selection")]
    [SerializeField] private Button selectFileButton;
    [SerializeField] private TMP_Text selectedFileText;
    
    [Header("Error Display")]
    [SerializeField] private GameObject errorPanel;
    [SerializeField] private TMP_Text errorText;
    [SerializeField] private Button dismissErrorButton;
    
    // References
    private LaparoscopyAPI api;
    private DisplacementVisualizer visualizer;
    
    // State
    private string selectedFilePath;
    private string currentJobId;
    private bool isProcessing = false;
    
    private void Awake()
    {
        // Get references
        api = FindObjectOfType<LaparoscopyAPI>();
        visualizer = FindObjectOfType<DisplacementVisualizer>();
        
        if (api == null)
        {
            ShowError("LaparoscopyAPI component not found!");
            return;
        }
        
        if (visualizer == null)
        {
            ShowError("DisplacementVisualizer component not found!");
            return;
        }
        
        // Setup UI event listeners
        SetupUIListeners();
        
        // Initialize UI state
        UpdateUIState();
    }
    
    private void SetupUIListeners()
    {
        uploadButton.onClick.AddListener(OnUploadClicked);
        refreshButton.onClick.AddListener(OnRefreshClicked);
        clearButton.onClick.AddListener(OnClearClicked);
        selectFileButton.onClick.AddListener(OnSelectFileClicked);
        resetViewButton.onClick.AddListener(OnResetViewClicked);
        dismissErrorButton.onClick.AddListener(OnDismissErrorClicked);
        
        showArrowsToggle.onValueChanged.AddListener(OnShowArrowsToggled);
        showAnchorsToggle.onValueChanged.AddListener(OnShowAnchorsToggled);
    }
    
    private void Start()
    {
        // Clean up old cache
        api.CleanupCache();
        
        // Initialize toggles
        showArrowsToggle.isOn = true;
        showAnchorsToggle.isOn = true;
        
        UpdateStatusText("Ready. Select a DICOM ZIP file to begin.");
    }
    
    private void OnSelectFileClicked()
    {
        // Open file dialog (simplified for web build)
        // In a real implementation, you'd use native file dialogs
        #if UNITY_EDITOR || UNITY_STANDALONE
        string path = UnityEditor.EditorUtility.OpenFilePanel(
            "Select DICOM ZIP file",
            "",
            "zip"
        );
        
        if (!string.IsNullOrEmpty(path))
        {
            SelectFile(path);
        }
        #else
        ShowError("File selection not supported in this build. Please use a standalone build.");
        #endif
    }
    
    private void SelectFile(string filePath)
    {
        selectedFilePath = filePath;
        selectedFileText.text = System.IO.Path.GetFileName(filePath);
        UpdateUIState();
    }
    
    private async void OnUploadClicked()
    {
        if (isProcessing || string.IsNullOrEmpty(selectedFilePath))
        {
            return;
        }
        
        await StartUploadProcess();
    }
    
    private async Task StartUploadProcess()
    {
        isProcessing = true;
        UpdateUIState();
        
        try
        {
            string patientFio = patientFioInput.text.Trim();
            
            UpdateStatusText("Uploading file...");
            SetProgress(0.1f, "Uploading");
            
            // Upload file
            currentJobId = await api.UploadDicomZip(selectedFilePath, patientFio);
            
            jobIdText.text = $"Job ID: {currentJobId}";
            UpdateStatusText("File uploaded. Starting processing...");
            SetProgress(0.2f, "Processing started");
            
            // Poll for completion
            await PollJobCompletion();
            
        }
        catch (System.Exception e)
        {
            ShowError($"Upload failed: {e.Message}");
            UpdateStatusText("Upload failed");
        }
        finally
        {
            isProcessing = false;
            UpdateUIState();
        }
    }
    
    private async Task PollJobCompletion()
    {
        if (string.IsNullOrEmpty(currentJobId))
        {
            return;
        }
        
        try
        {
            SetProgress(0.3f, "Processing...");
            
            var jobInfo = await api.PollJobUntilComplete(currentJobId, OnJobStatusUpdate);
            
            SetProgress(0.8f, "Downloading results...");
            UpdateStatusText("Processing complete. Downloading results...");
            
            // Load and visualize
            await LoadAndVisualizeResults();
            
            SetProgress(1.0f, "Complete");
            UpdateStatusText($"Complete! Job {currentJobId} processed successfully.");
            
        }
        catch (System.Exception e)
        {
            ShowError($"Processing failed: {e.Message}");
            UpdateStatusText("Processing failed");
        }
    }
    
    private void OnJobStatusUpdate(LaparoscopyAPI.JobInfo status)
    {
        // Update UI with job status
        UpdateStatusText($"Status: {status.status}");
        
        // Update progress based on status
        float progress = 0.3f;
        string progressText = "Processing...";
        
        switch (status.status?.ToLower())
        {
            case "pending":
                progress = 0.2f;
                progressText = "Queued";
                break;
            case "processing":
                progress = 0.4f;
                progressText = "Processing...";
                break;
            case "segmentation_done":
                progress = 0.6f;
                progressText = "Segmentation complete";
                break;
            case "conversion_done":
                progress = 0.7f;
                progressText = "Conversion complete";
                break;
            case "completed":
                progress = 0.9f;
                progressText = "Complete";
                break;
            case "error":
                progress = 0.0f;
                progressText = "Error";
                break;
        }
        
        SetProgress(progress, progressText);
    }
    
    private async Task LoadAndVisualizeResults()
    {
        if (string.IsNullOrEmpty(currentJobId))
        {
            return;
        }
        
        try
        {
            UpdateStatusText("Loading visualization...");
            
            // Load and visualize
            visualizer.LoadAndVisualizeJob(currentJobId);
            
            UpdateStatusText("Visualization loaded");
        }
        catch (System.Exception e)
        {
            ShowError($"Visualization failed: {e.Message}");
            UpdateStatusText("Visualization failed");
        }
    }
    
    private void OnRefreshClicked()
    {
        if (string.IsNullOrEmpty(currentJobId))
        {
            return;
        }
        
        _ = RefreshJobStatus();
    }
    
    private async Task RefreshJobStatus()
    {
        try
        {
            var status = await api.GetJobStatus(currentJobId);
            OnJobStatusUpdate(status);
        }
        catch (System.Exception e)
        {
            ShowError($"Failed to refresh status: {e.Message}");
        }
    }
    
    private void OnClearClicked()
    {
        // Clear current job
        currentJobId = null;
        selectedFilePath = null;
        selectedFileText.text = "No file selected";
        jobIdText.text = "Job ID: None";
        
        // Clear visualization
        visualizer.ClearVisualization();
        
        // Reset UI
        SetProgress(0.0f, "");
        UpdateStatusText("Ready. Select a DICOM ZIP file to begin.");
        UpdateUIState();
    }
    
    private void OnResetViewClicked()
    {
        // Reset camera view
        Camera.main.transform.position = new Vector3(0, 0, -10);
        Camera.main.transform.rotation = Quaternion.identity;
    }
    
    private void OnShowArrowsToggled(bool value)
    {
        visualizer.ToggleDisplacementArrows(value);
    }
    
    private void OnShowAnchorsToggled(bool value)
    {
        visualizer.ToggleAnchorPoints(value);
    }
    
    private void OnDismissErrorClicked()
    {
        errorPanel.SetActive(false);
    }
    
    private void UpdateUIState()
    {
        // Update button states
        uploadButton.interactable = !isProcessing && !string.IsNullOrEmpty(selectedFilePath);
        refreshButton.interactable = !isProcessing && !string.IsNullOrEmpty(currentJobId);
        clearButton.interactable = !isProcessing;
        selectFileButton.interactable = !isProcessing;
        patientFioInput.interactable = !isProcessing;
        
        // Update toggle states
        showArrowsToggle.interactable = !string.IsNullOrEmpty(currentJobId);
        showAnchorsToggle.interactable = !string.IsNullOrEmpty(currentJobId);
    }
    
    private void UpdateStatusText(string text)
    {
        if (statusText != null)
        {
            statusText.text = text;
        }
    }
    
    private void SetProgress(float progress, string text)
    {
        if (progressSlider != null)
        {
            progressSlider.value = progress;
        }
        
        if (progressText != null)
        {
            progressText.text = text;
        }
    }
    
    private void ShowError(string message)
    {
        if (errorText != null)
        {
            errorText.text = message;
        }
        
        if (errorPanel != null)
        {
            errorPanel.SetActive(true);
        }
        
        Debug.LogError($"UI Error: {message}");
    }
    
    // Public methods for external control
    public void SelectFileFromPath(string filePath)
    {
        if (System.IO.File.Exists(filePath))
        {
            SelectFile(filePath);
        }
        else
        {
            ShowError($"File not found: {filePath}");
        }
    }
    
    public void SetPatientFio(string fio)
    {
        if (patientFioInput != null)
        {
            patientFioInput.text = fio;
        }
    }
    
    public async void ProcessJobId(string jobId)
    {
        currentJobId = jobId;
        jobIdText.text = $"Job ID: {jobId}";
        
        isProcessing = true;
        UpdateUIState();
        
        try
        {
            await PollJobCompletion();
        }
        finally
        {
            isProcessing = false;
            UpdateUIState();
        }
    }
}
