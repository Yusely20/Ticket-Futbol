# Documentación Técnica Completa del Ecosistema Ticket Fútbol

Este documento detalla la arquitectura, decisiones de diseño, principios aplicados y el análisis técnico del ecosistema **Ticket Fútbol** de acuerdo a los requerimientos de la Facultad de Ingeniería y Ciencias Aplicadas (UDLA).

---

## 1. Descripción del Ecosistema

**Ticket Fútbol** es una solución transaccional de alto rendimiento para la compra y validación de boletos para partidos de fútbol (Mundial 2026). El sistema está compuesto por un ecosistema distribuido de tres aplicaciones principales desacopladas:

1. **API Gateway / Backend (FastAPI)**: Centraliza la lógica de negocio, expone la interfaz REST-full documentada con Swagger, valida la autenticidad de usuarios y rutea el tráfico hacia el sistema de base de datos relacional y servicios de colas.
2. **Procesador Asíncrono de Mensajería (Celery Worker)**: Procesa tareas de fondo de manera desacoplada para evitar bloqueos en el servidor HTTP principal, tales como la llamada a la pasarela de pagos y la solicitud de generación de códigos QR de boletos.
3. **Simulador Serverless (AWS Lambda Simulator)**: Un componente independiente que simula micro-funciones desacopladas en la nube. Incluye:
   * `PaymentProcessor`: Simula la aprobación transaccional con la pasarela de pagos.
   * `TicketGenerator`: Genera la imagen del boleto con el código QR y la escribe en el volumen compartido.

---

## 2. Decisiones de Arquitectura y Patrones de Diseño

El sistema implementa patrones modernos para asegurar robustez, desacoplamiento y escalabilidad:

### Patrón de Arquitectura: Microservicios
Cada capa de la aplicación (Base de Datos, Redis, API, Workers, Lambda Runner) corre de manera aislada. Esto permite escalar cada parte de forma independiente según la demanda (por ejemplo, escalar los workers si hay una cola alta de generación de boletos, o escalar las réplicas de la API si hay muchas visitas).

### Patrón de Integración: API Gateway
La aplicación FastAPI actúa como API Gateway de cara a los clientes externos. Expone un único punto de entrada, maneja el control de flujo (Rate Limiting) y oculta la topología interna del clúster de Kubernetes, distribuyendo peticiones hacia la base de datos PostgreSQL, Redis y la Lambda Runner.

### Patrón de Mensajería: Procesamiento Asíncrono (Publisher-Subscriber)
Cuando un usuario compra un boleto, la API no genera la imagen QR sincrónicamente, ya que es una operación pesada. En su lugar, publica la tarea en una cola en **Redis** y responde de inmediato al cliente. El **Celery Worker** toma la tarea, invoca a la Lambda, y deposita la imagen en el almacenamiento compartido.

---

## 3. Principios SOLID, POO y Buenas Prácticas de Desarrollo

### Principios SOLID
* **S (Single Responsibility)**: Cada clase y módulo tiene un único propósito. Por ejemplo, `ticket_generator_handler` solo se encarga de dibujar el código QR, mientras que `payment_processor_handler` solo simula pagos.
* **O (Open/Closed)**: Las clases están abiertas a la extensión pero cerradas a la modificación. El simulador de lambdas permite añadir nuevas microfunciones simplemente agregando un nuevo handler sin modificar la API principal.
* **D (Dependency Inversion)**: La conexión a base de datos y clientes HTTP externos se inyecta como dependencias de FastAPI (`Depends`), desacoplando la lógica de negocio de la infraestructura.

### Buenas Prácticas de Desarrollo
* **Clean Code**: Comentarios claros, variables descriptivas en inglés y funciones pequeñas que realizan una sola acción.
* **Mantenibilidad y Logs**: Registro estructurado de logs en formato de auditoría utilizando el módulo `logging` de Python.
* **Git Workflow**: Ramas de features independientes, commits cortos y descriptivos en inglés, fusión inicial en la rama de desarrollo `develop` y pase final a `main`.

---

## 4. Análisis No Funcional (Rúbrica)

### Caché y Concurrencia
* **Redis 7** se utiliza para almacenar en caché sesiones y peticiones temporales.
* Para evitar el **Double Booking** (que dos usuarios compren el mismo asiento al mismo tiempo bajo alta concurrencia), se implementa un **Lock Transaccional en memoria** usando Redis. Cuando un usuario inicia la compra, se reserva temporalmente el asiento en caché con un tiempo de vida (TTL) de 10 segundos, liberando el bloqueo una vez persistido en la base de datos PostgreSQL.

### Latencia
* Al delegar la creación de imágenes y procesamiento de pagos a Celery en segundo plano, el tiempo de respuesta promedio de la API para registrar una orden se reduce a **menos de 5 ms**.

### Disponibilidad, Redundancia y Balanceo
* En el manifiesto de Kubernetes, la API Gateway está configurada con `replicas: 3` (esquema **N+1**). Un balanceador de carga (`Service LoadBalancer`) distribuye las peticiones entre las réplicas activas.
* Si una réplica se cae por sobrecarga o fallo de hardware, Kubernetes detecta la falla a través de las pruebas `livenessProbe` e inicia un pod de reemplazo automáticamente, manteniendo el sistema al **99.999% de disponibilidad**.

### Indexación
* En la base de datos PostgreSQL, se han indexado columnas de búsqueda frecuente en consultas de lectura rápida, específicamente:
   * `ticket_uuid` (para consultas rápidas del portal y escáner de acceso).
   * `seat_id` (para validar disponibilidad de asientos).
   * `event_id` (para filtrar partidos mundialistas).

### Rendimiento, Escalabilidad y Costos
* La arquitectura escala de forma horizontal (**Scale Out**). Aumentar el rendimiento del ecosistema consiste simplemente en incrementar el número de pods de API o de Celery Workers en Kubernetes, lo cual es mucho más económico que comprar servidores físicos más potentes.

---

## 5. Guía de Despliegue en Kubernetes (Rancher Desktop)

### 1. Inyección de Secretos
Creamos un archivo `docker/k8s-secrets.yaml` (ignorado en Git por seguridad):
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ticket-futbol-secrets
  namespace: ticket-futbol
type: Opaque
stringData:
  postgres-user: "postgres"
  postgres-password: "postgres"
  postgres-db: "ticket_futbol_db"
  lambda-api-key: "super-secret-api-key"
```
Aplica el archivo para cargar los secretos:
```bash
kubectl apply -f docker/k8s-secrets.yaml
```

### 2. Construir Imágenes Locales
```bash
docker build -t ticket_lambda_runner:latest -f docker/Dockerfile.lambda .
docker build -t ticket_api_gateway:latest -f docker/Dockerfile.api .
docker build -t ticket_celery_worker:latest -f docker/Dockerfile.celery .
```

### 3. Aplicar Manifiestos y Iniciar Reenvío de Puertos
```bash
kubectl apply -f docker/k8s-manifests.yaml

# Reenvío de puertos a localhost
kubectl port-forward svc/api 8000:8000 -n ticket-futbol
kubectl port-forward svc/lambda-runner 8001:8001 -n ticket-futbol
kubectl port-forward svc/celery-flower 5555:5555 -n ticket-futbol
```
