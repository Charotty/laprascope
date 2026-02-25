using UnityEngine;

public class ModelController : MonoBehaviour
{
    [Header("Rotation")]
    public bool enableRotation = true;
    public float rotationSpeed = 45f;
    public bool autoRotate = false;
    public Vector3 autoRotationAxis = Vector3.up;
    
    [Header("Zoom")]
    public bool enableZoom = true;
    public float zoomSpeed = 1f;
    public float minZoom = 0.5f;
    public float maxZoom = 3f;
    
    [Header("Pan")]
    public bool enablePan = true;
    public float panSpeed = 0.01f;
    
    [Header("Touch")]
    public bool enableTouchControls = true;
    
    [Header("Debug")]
    public bool enableDebugLogs = true;
    
    private Vector3 lastMousePosition;
    private float currentZoom = 1f;
    private bool isDragging = false;
    
    void Start()
    {
        currentZoom = transform.localScale.x;
        
        if (enableDebugLogs)
            Debug.Log("ModelController initialized");
    }
    
    void Update()
    {
        HandleMouseInput();
        HandleTouchInput();
        
        if (autoRotate && !isDragging)
        {
            AutoRotate();
        }
    }
    
    /// <summary>
    /// Обрабатывает ввод с мыши
    /// </summary>
    private void HandleMouseInput()
    {
        // Вращение
        if (enableRotation && Input.GetMouseButton(0))
        {
            if (!isDragging)
            {
                isDragging = true;
                lastMousePosition = Input.mousePosition;
            }
            else
            {
                Vector3 deltaPosition = Input.mousePosition - lastMousePosition;
                
                // Вращаем вокруг Y и X осей
                transform.Rotate(Vector3.up, -deltaPosition.x * rotationSpeed * Time.deltaTime, Space.World);
                transform.Rotate(Vector3.right, deltaPosition.y * rotationSpeed * Time.deltaTime, Space.World);
                
                lastMousePosition = Input.mousePosition;
            }
        }
        else
        {
            isDragging = false;
        }
        
        // Zoom (колесо мыши)
        if (enableZoom)
        {
            float scroll = Input.GetAxis("Mouse ScrollWheel");
            if (scroll != 0)
            {
                Zoom(-scroll * zoomSpeed);
            }
        }
        
        // Pan (правая кнопка мыши)
        if (enablePan && Input.GetMouseButton(1))
        {
            Vector3 deltaPosition = Input.mousePosition - lastMousePosition;
            
            // Перемещаем в плоскости экрана
            Vector3 panDirection = new Vector3(-deltaPosition.x, -deltaPosition.y, 0);
            panDirection = Camera.main.transform.TransformDirection(panDirection);
            panDirection.y = 0; // Ограничиваем перемещение горизонтальной плоскостью
            
            transform.position += panDirection * panSpeed;
            
            lastMousePosition = Input.mousePosition;
        }
    }
    
    /// <summary>
    /// Обрабатывает сенсорный ввод для мобильных устройств
    /// </summary>
    private void HandleTouchInput()
    {
        if (!enableTouchControls) return;
        
        if (Input.touchCount == 1)
        {
            // Вращение одним пальцем
            Touch touch = Input.GetTouch(0);
            
            if (touch.phase == TouchPhase.Began)
            {
                isDragging = true;
                lastMousePosition = touch.position;
            }
            else if (touch.phase == TouchPhase.Moved && isDragging)
            {
                Vector2 deltaPosition = touch.position - (Vector2)lastMousePosition;
                
                transform.Rotate(Vector3.up, -deltaPosition.x * rotationSpeed * Time.deltaTime, Space.World);
                transform.Rotate(Vector3.right, deltaPosition.y * rotationSpeed * Time.deltaTime, Space.World);
                
                lastMousePosition = touch.position;
            }
            else if (touch.phase == TouchPhase.Ended)
            {
                isDragging = false;
            }
        }
        else if (Input.touchCount == 2)
        {
            // Zoom двумя пальцами
            Touch touch1 = Input.GetTouch(0);
            Touch touch2 = Input.GetTouch(1);
            
            if (touch1.phase == TouchPhase.Moved || touch2.phase == TouchPhase.Moved)
            {
                Vector2 currentDistance = touch1.position - touch2.position;
                Vector2 previousDistance = (touch1.position - touch1.deltaPosition) - (touch2.position - touch2.deltaPosition);
                
                float deltaDistance = currentDistance.magnitude - previousDistance.magnitude;
                
                Zoom(deltaDistance * zoomSpeed * 0.01f);
            }
        }
    }
    
    /// <summary>
    /// Автоматическое вращение модели
    /// </summary>
    private void AutoRotate()
    {
        transform.Rotate(autoRotationAxis, rotationSpeed * Time.deltaTime, Space.World);
    }
    
    /// <summary>
    /// Изменяет масштаб модели
    /// </summary>
    public void Zoom(float delta)
    {
        currentZoom = Mathf.Clamp(currentZoom + delta, minZoom, maxZoom);
        transform.localScale = Vector3.one * currentZoom;
        
        if (enableDebugLogs)
            Debug.Log($"Zoom changed: {currentZoom}");
    }
    
    /// <summary>
    /// Устанавливает масштаб модели
    /// </summary>
    public void SetZoom(float zoom)
    {
        currentZoom = Mathf.Clamp(zoom, minZoom, maxZoom);
        transform.localScale = Vector3.one * currentZoom;
    }
    
    /// <summary>
    /// Сбрасывает позицию и вращение модели
    /// </summary>
    public void ResetTransform()
    {
        transform.localPosition = Vector3.zero;
        transform.localRotation = Quaternion.identity;
        SetZoom(1f);
        
        if (enableDebugLogs)
            Debug.Log("Transform reset");
    }
    
    /// <summary>
    /// Включает/выключает автоматическое вращение
    /// </summary>
    public void SetAutoRotate(bool enable)
    {
        autoRotate = enable;
        
        if (enableDebugLogs)
            Debug.Log($"Auto rotate set to: {enable}");
    }
    
    /// <summary>
    /// Устанавливает скорость вращения
    /// </summary>
    public void SetRotationSpeed(float speed)
    {
        rotationSpeed = Mathf.Max(0, speed);
        
        if (enableDebugLogs)
            Debug.Log($"Rotation speed set to: {rotationSpeed}");
    }
    
    /// <summary>
    /// Устанавливает ось автоматического вращения
    /// </summary>
    public void SetAutoRotationAxis(Vector3 axis)
    {
        autoRotationAxis = axis.normalized;
        
        if (enableDebugLogs)
            Debug.Log($"Auto rotation axis set to: {axis}");
    }
    
    /// <summary>
    /// Получает текущий масштаб
    /// </summary>
    public float GetCurrentZoom()
    {
        return currentZoom;
    }
    
    /// <summary>
    /// Получает информацию о текущем состоянии
    /// </summary>
    public string GetStateInfo()
    {
        return $"Zoom: {currentZoom:F2}, AutoRotate: {autoRotate}, RotationSpeed: {rotationSpeed}";
    }
    
    void OnDrawGizmos()
    {
        // Рисуем bounds для отладки
        if (enableDebugLogs && GetComponent<Renderer>() != null)
        {
            Gizmos.color = Color.green;
            Gizmos.DrawWireCube(transform.position, GetComponent<Renderer>().bounds.size);
        }
    }
}
