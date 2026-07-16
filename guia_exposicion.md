# Guía de Exposición y Defensa del Proyecto Integrador

Este documento sirve como tu guía personal para la exposición oral del proyecto **Ticket Fútbol** ante el tribunal de evaluación de la **Facultad de Ingeniería y Ciencias Aplicadas (UDLA)**.

---

## 1. Guía Diapositiva por Diapositiva

### Diapositiva 1: Portada y Presentación
* **Qué decir**: "Buenas tardes ingenieros, hoy les presento el ecosistema Ticket Fútbol, una plataforma transaccional de alto rendimiento para el control de acceso y compra de boletos para el Mundial 2026. Este proyecto demuestra una arquitectura desacoplada en microservicios, procesamiento asíncrono en colas, y su despliegue en un entorno local altamente disponible usando Kubernetes".

### Diapositiva 2: Descripción General del Ecosistema
* **Qué decir**: "La solución está formada por un ecosistema de tres aplicaciones desacopladas de software:
  1. Un **API Gateway** en FastAPI que unifica la entrada del tráfico externo y aplica límites de seguridad.
  2. Un **Celery Worker** que procesa la lógica asíncrona pesada en colas.
  3. Un **Simulador Serverless** que expone micro-funciones independientes para pagos y creación de QR.
  Cada una corre de forma independiente y aislada."

### Diapositiva 3: Capa de Datos y Docker
* **Qué decir**: "De acuerdo a los requerimientos técnicos, desacoplamos totalmente la capa de datos en contenedores Docker independientes:
  * **PostgreSQL 15** maneja la persistencia y la integridad relacional de eventos, compras y asientos.
  * **Redis 7** en memoria funciona como caché y broker de mensajería rápido para coordinar las tareas asíncronas."

### Diapositiva 4: Procesamiento Asíncrono (Colas)
* **Qué decir**: "Generar imágenes QR en tiempo real es una tarea costosa. Para evitar tiempos de espera altos en el navegador del cliente (latencia), implementamos un patrón de colas. La API registra la compra, encola la tarea en Redis y responde al cliente de inmediato en menos de 5 ms. El Celery Worker consume la cola y genera el boleto en segundo plano. Monitoreamos este proceso con Flower, el cual nos da métricas en tiempo real idénticas a RabbitMQ".

### Diapositiva 5: Monitoreo y Observabilidad
* **Qué decir**: "Para cumplir con el principio operacional 'Design to Be Monitored', integramos **Prometheus** y **Grafana**. Prometheus recolecta la latencia y la tasa de peticiones del API Gateway de forma continua. En Grafana, importamos un tablero profesional que nos muestra que el sistema responde con una latencia de 3.5 ms y una disponibilidad del 100% en las peticiones HTTP."

### Diapositiva 6: Despliegue en Kubernetes y Seguridad
* **Qué decir**: "Para simular un entorno real de producción, desplegamos todo en un clúster de Kubernetes usando Rancher Desktop. Implementamos redundancia con 3 réplicas de la API. Además, aplicamos estrictamente principios de seguridad: ninguna contraseña o llave API está escrita en el código de los manifiestos, sino que se inyectan en caliente desde el almacén seguro de Kubernetes Secrets (`k8s-secrets.yaml`), el cual está excluido de nuestro control de versiones Git en `.gitignore`."

---

## 2. Guía para la Demostración en Vivo (Demo Script)

Sigue estos pasos ordenados durante la parte práctica de tu exposición para demostrar la funcionalidad del sistema:

1. **Mostrar el Portal de Clientes**:
   * Abre **`http://localhost:8000/`**.
   * Explica que es una interfaz interactiva con estilos de vidrio translúcido (Glassmorphism) para ofrecer una experiencia premium.
   * Haz clic en el partido *Argentina vs Francia*.
   * Selecciona un asiento libre en el mapa de estadio interactivo.

2. **Mostrar el Monitoreo de la Cola en Flower**:
   * Abre **`http://localhost:5555/`** en otra pestaña.
   * Ve a la sección **Workers** y haz clic en tu worker activo.
   * Deja la pestaña abierta para ver el contador en vivo de tareas.

3. **Ejecutar la Compra**:
   * Regresa al portal de clientes y presiona **"Reservar Boleto"**.
   * Regresa inmediatamente a la pestaña de **Flower** y verás cómo el contador de tareas exitosas sube a `1` y la gráfica dibuja el pico de procesamiento de la cola.
   * Regresa al portal de clientes: la compra se habrá completado y mostrará el ticket con el código QR único generado.

4. **Demostrar el Monitoreo en Grafana**:
   * Abre **`http://localhost:3000/`**.
   * Muestra las gráficas del API Gateway: el contador de peticiones HTTP totales habrá aumentado, la disponibilidad se mantendrá al 100% y la latencia promedio se mostrará en un rango de milisegundos mínimos.

5. **Demostrar los Logs en Rancher Desktop**:
   * Abre la interfaz gráfica de **Rancher Desktop**.
   * Ve a **Containers**, despliega el namespace `ticket-futbol` y abre los logs de `celery-worker` o `api` para mostrar la auditoría y traza en caliente de la solicitud de compra.
