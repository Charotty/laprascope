using UnityEngine;
using TriLib;
using System.Collections;
using System.IO;

public class ModelLoader : MonoBehaviour
{
    [Header("Model Loading")]
    public Material defaultMaterial;
    public Transform modelParent;
    public bool autoCenter = true;
    public bool autoScale = true;
    public float scaleFactor = 0.1f;
    
    [Header("Debug")]
    public bool enableDebugLogs = true;
    
    // События для UI
    public System.Action<GameObject> OnModelLoaded;
    public System.Action<string> OnModelLoadFailed;
    public System.Action OnModelUnloaded;
    
    private GameObject currentModel;
    private AssetLoaderAsset assetLoader;
    
    void Start()
    {
        // Инициализируем TriLib asset loader
        assetLoader = AssetLoaderAsset.CreateInstance<AssetLoaderAsset>();
        
        if (enableDebugLogs)
            Debug.Log("ModelLoader initialized");
    }
    
    /// <summary>
    /// Загружает STL модель из файла
    /// </summary>
    /// <param name="filePath">Путь к STL файлу</param>
    public void LoadSTLModel(string filePath)
    {
        StartCoroutine(LoadSTLModelCoroutine(filePath));
    }
    
    private IEnumerator LoadSTLModelCoroutine(string filePath)
    {
        if (enableDebugLogs)
            Debug.Log($"Loading STL model: {filePath}");
        
        // Проверяем существование файла
        if (!File.Exists(filePath))
        {
            string error = $"STL file not found: {filePath}";
            Debug.LogError(error);
            OnModelLoadFailed?.Invoke(error);
            yield break;
        }
        
        // Удаляем предыдущую модель если есть
        UnloadModel();
        
        // Загружаем модель с помощью TriLib
        var assetLoaderOptions = AssetLoaderOptions.CreateInstance();
        assetLoaderOptions.AddAllLoaders = false;
        assetLoaderOptions.AddMeshLoaders = true;
        assetLoaderOptions.AnimationType = AnimationType.None;
        assetLoaderOptions.GenerateAnimations = false;
        
        // Устанавливаем материал по умолчанию
        if (defaultMaterial != null)
        {
            assetLoaderOptions.DefaultMaterial = defaultMaterial;
        }
        
        // Начинаем загрузку
        var loadCoroutine = assetLoader.LoadFromFileCoroutine(
            filePath,
            assetLoaderOptions,
            null,
            null,
            OnModelLoadComplete,
            OnModelLoadError,
            null
        );
        
        yield return StartCoroutine(loadCoroutine);
    }
    
    /// <summary>
    /// Вызывается при успешной загрузке модели
    /// </summary>
    private void OnModelLoadComplete(AssetLoaderContext assetLoaderContext)
    {
        if (assetLoaderContext.RootGameObject != null)
        {
            currentModel = assetLoaderContext.RootGameObject;
            
            // Устанавливаем родителя
            if (modelParent != null)
            {
                currentModel.transform.SetParent(modelParent, false);
            }
            
            // Центрируем модель
            if (autoCenter)
            {
                CenterModel();
            }
            
            // Масштабируем модель
            if (autoScale)
            {
                ScaleModel();
            }
            
            // Добавляем компонент для взаимодействия
            AddModelInteraction();
            
            if (enableDebugLogs)
            {
                Debug.Log($"Model loaded successfully: {currentModel.name}");
                Debug.Log($"Model bounds: {GetModelBounds()}");
            }
            
            OnModelLoaded?.Invoke(currentModel);
        }
        else
        {
            string error = "Model loading completed but no GameObject was created";
            Debug.LogError(error);
            OnModelLoadFailed?.Invoke(error);
        }
    }
    
    /// <summary>
    /// Вызывается при ошибке загрузки модели
    /// </summary>
    private void OnModelLoadError(IAssetLoaderContext assetLoaderContext, string exception)
    {
        string error = $"Model loading failed: {exception}";
        Debug.LogError(error);
        OnModelLoadFailed?.Invoke(error);
    }
    
    /// <summary>
    /// Удаляет текущую модель
    /// </summary>
    public void UnloadModel()
    {
        if (currentModel != null)
        {
            if (enableDebugLogs)
                Debug.Log($"Unloading model: {currentModel.name}");
            
            DestroyImmediate(currentModel);
            currentModel = null;
            
            OnModelUnloaded?.Invoke();
        }
    }
    
    /// <summary>
    /// Центрирует модель относительно родителя
    /// </summary>
    private void CenterModel()
    {
        if (currentModel == null) return;
        
        // Получаем bounds модели
        var renderer = currentModel.GetComponentInChildren<Renderer>();
        if (renderer != null)
        {
            var bounds = renderer.bounds;
            var center = bounds.center;
            
            // Сдвигаем модель так чтобы центр был в (0,0,0)
            currentModel.transform.position = -center;
            
            if (enableDebugLogs)
                Debug.Log($"Model centered. Original center: {center}");
        }
    }
    
    /// <summary>
    /// Масштабирует модель до подходящего размера
    /// </summary>
    private void ScaleModel()
    {
        if (currentModel == null) return;
        
        // Получаем bounds модели
        var renderer = currentModel.GetComponentInChildren<Renderer>();
        if (renderer != null)
        {
            var bounds = renderer.bounds;
            var maxDimension = Mathf.Max(bounds.size.x, bounds.size.y, bounds.size.z);
            
            // Рассчитываем масштаб
            var scale = scaleFactor / maxDimension;
            currentModel.transform.localScale = Vector3.one * scale;
            
            if (enableDebugLogs)
                Debug.Log($"Model scaled. Original size: {bounds.size}, Scale: {scale}");
        }
    }
    
    /// <summary>
    /// Добавляет компонент для взаимодействия с моделью
    /// </summary>
    private void AddModelInteraction()
    {
        if (currentModel == null) return;
        
        // Добавляем Rigidbody для физического взаимодействия
        var rigidbody = currentModel.AddComponent<Rigidbody>();
        rigidbody.useGravity = false;
        rigidbody.isKinematic = true;
        
        // Добавляем коллайдеры если их нет
        AddColliders(currentModel);
        
        // Добавляем скрипт для вращения и масштабирования
        var modelController = currentModel.AddComponent<ModelController>();
        modelController.enableDebugLogs = enableDebugLogs;
    }
    
    /// <summary>
    /// Рекурсивно добавляет коллайдеры ко всем мешам
    /// </summary>
    private void AddColliders(GameObject obj)
    {
        // Добавляем MeshCollider если есть MeshFilter
        var meshFilter = obj.GetComponent<MeshFilter>();
        if (meshFilter != null && obj.GetComponent<MeshCollider>() == null)
        {
            var collider = obj.AddComponent<MeshCollider>();
            collider.convex = true; // Для лучшей производительности
        }
        
        // Рекурсивно обрабатываем дочерние объекты
        for (int i = 0; i < obj.transform.childCount; i++)
        {
            AddColliders(obj.transform.GetChild(i).gameObject);
        }
    }
    
    /// <summary>
    /// Получает bounds текущей модели
    /// </summary>
    public Bounds GetModelBounds()
    {
        if (currentModel == null) return new Bounds();
        
        var renderer = currentModel.GetComponentInChildren<Renderer>();
        return renderer != null ? renderer.bounds : new Bounds();
    }
    
    /// <summary>
    /// Устанавливает материал для модели
    /// </summary>
    public void SetModelMaterial(Material material)
    {
        if (currentModel == null) return;
        
        var renderers = currentModel.GetComponentsInChildren<Renderer>();
        foreach (var renderer in renderers)
        {
            renderer.material = material;
        }
        
        if (enableDebugLogs)
            Debug.Log($"Material set for model: {material.name}");
    }
    
    /// <summary>
    /// Включает/выключает видимость модели
    /// </summary>
    public void SetModelVisibility(bool visible)
    {
        if (currentModel == null) return;
        
        currentModel.SetActive(visible);
        
        if (enableDebugLogs)
            Debug.Log($"Model visibility set to: {visible}");
    }
    
    void OnDestroy()
    {
        UnloadModel();
        
        // Очищаем TriLib ресурсы
        if (assetLoader != null)
        {
            DestroyImmediate(assetLoader);
        }
    }
}
