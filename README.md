# ⚽ Ticket Fútbol - Plataforma de Boletería Deportiva

Ticket Fútbol es una solución transaccional premium para la venta y control de acceso a partidos de fútbol, diseñada con una arquitectura moderna de microservicios, procesamiento de colas asíncronas y simulación serverless.

## 🌟 Características Clave
* **Próximos Eventos (Mundial 2026)**: Vista cliente precargada con partidos mundialistas icónicos (Argentina vs Francia, Brasil vs Alemania, España vs Italia) y selección dinámica de asientos en estadio elíptico.
* **Control de Acceso con Cámara**: Escáner en tiempo real integrado para el Personal de Acceso (Staff). Lee códigos QR directamente usando la cámara del celular y valida la autenticidad al instante.
* **Limpiador de UUID Inteligente**: Si se copia el enlace completo del boleto (`/t/uuid`), el escáner extrae el UUID de manera automática para evitar errores humanos.
* **Historial y Gestión de Eventos**: Panel para Organizadores (Admin) para ver todos los partidos creados, editarlos, eliminarlos en cascada, o alternar su visibilidad (Visible/Oculto) para los clientes.
* **Simulador de Roles**: Selector superior dinámico que permite a la cuenta `admin` alternar su rol simulado en tiempo real entre Organizador y Staff.

---

## 🛠️ Stack Tecnológico
1. **API Gateway & Router**: FastAPI (Python 3.10) + Uvicorn.
2. **Base de Datos**: PostgreSQL 15 (Eventos, Usuarios, Órdenes, Asientos y Boletos).
3. **Caché y Colas**: Redis 7 (Límites transaccionales con Locks en memoria y bróker de Celery).
4. **Colas Asíncronas**: Celery Worker (Generación diferida de imágenes QR).
5. **Serverless (AWS Lambdas simuladas)**:
   - `PaymentProcessor`: Simula la captura en pasarela de pagos.
   - `TicketGenerator`: Genera los QRs vinculados al enlace único del boleto.
6. **Frontend**: Dashboard con estilo glassmorphism (HTML5/Jinja2/Vanilla CSS/JS) y librerías HTML5-QRCode.

---

## 🚀 Cómo Correr el Proyecto en tu Computadora

### Requisitos Previos
Tener instalado **Rancher Desktop** (con Kubernetes habilitado) y **kubectl** en tu sistema.

---

### Opción A: Despliegue en Kubernetes (Recomendado / Producción)

1. **Crear archivo de secretos**:
   Crea un archivo llamado `docker/k8s-secrets.yaml` (este archivo está excluido de Git por seguridad) con el siguiente contenido:
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

2. **Construir imágenes locales**:
   ```bash
   # Si usas dockerd en Rancher:
   docker build -t ticket_lambda_runner:latest -f docker/Dockerfile.lambda .
   docker build -t ticket_api_gateway:latest -f docker/Dockerfile.api .
   docker build -t ticket_celery_worker:latest -f docker/Dockerfile.celery .
   ```

3. **Desplegar en Kubernetes**:
   ```bash
   kubectl apply -f docker/k8s-secrets.yaml
   kubectl apply -f docker/k8s-manifests.yaml
   ```

4. **Reenvío de puertos (Port-Forward)**:
   Para acceder localmente, expón los puertos del clúster a tu máquina:
   ```bash
   kubectl port-forward svc/api 8000:8000 -n ticket-futbol
   kubectl port-forward svc/lambda-runner 8001:8001 -n ticket-futbol
   kubectl port-forward svc/celery-flower 5555:5555 -n ticket-futbol
   ```

5. **Monitoreo adicional (Prometheus & Grafana en Docker)**:
   Levanta las herramientas de observabilidad:
   ```bash
   docker compose -f docker/monitoring-compose.yml up -d
   ```

---

### Opción B: Despliegue con Docker Compose (Desarrollo Rápido)

1. Crea o configura tu archivo `.env` en la raíz.
2. Inicia los servicios:
   ```bash
   docker compose -f docker/docker-compose.yml up --build -d
   docker compose -f docker/monitoring-compose.yml up -d
   ```

---

### 🌐 Enlaces del Ecosistema

Una vez corriendo, abre estos enlaces en tu navegador:
* **Portal de Boletería y API Gateway**: [http://localhost:8000/](http://localhost:8000/)
* **Documentación (Swagger Hub)**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Simulador de AWS Lambdas**: [http://localhost:8001/docs](http://localhost:8001/docs)
* **Gestor de Colas (Celery Flower)**: [http://localhost:5555/](http://localhost:5555/)
* **Monitoreo de Telemetría (Grafana)**: [http://localhost:3000/](http://localhost:3000/)
* **Recolector de Métricas (Prometheus)**: [http://localhost:9090/](http://localhost:9090/)

---


## 🧪 Pruebas Unitarias Locales (Opcional)

Si deseas correr los tests lógicos locales de integración sin usar Docker:
1. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Ejecuta el suite de pruebas de flujo:
   ```bash
   python -m unittest tests/test_flow.py
   ```
