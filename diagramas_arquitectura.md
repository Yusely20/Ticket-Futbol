# Diagramas de Arquitectura - Ecosistema Ticket Fútbol

Este documento compila de forma exclusiva todos los diagramas de la arquitectura del proyecto, expresados bajo el estándar de **C4 Model** (Contexto y Contenedores), diagramas de secuencia transaccional y diagramas de infraestructura de Kubernetes.

---

## 1. C4 Model - Nivel 1: Diagrama de Contexto
Muestra a los actores del sistema y los sistemas externos que interactúan con el ecosistema.

```mermaid
graph TD
    User["⚽ Cliente / Staff de Acceso"] -->|1. Reserva boletos / Escanea QR| Gateway["🎟️ Ecosistema Ticket Fútbol"]
    Gateway -->|2. Simula Cobro transaccional| PaymentSystem["💳 Pasarela de Pagos (AWS Lambda Sim)"]
    Gateway -->|3. Genera código QR único| QRGenerator["🖼️ Generador de QR (AWS Lambda Sim)"]
```

---

## 2. C4 Model - Nivel 2: Diagrama de Contenedores
Muestra las aplicaciones de software desacopladas que conforman el ecosistema, sus puertos, bases de datos y flujos de comunicación.

```mermaid
graph TB
    subgraph Ecosistema ["🎟️ Ecosistema Ticket Fútbol"]
        API["⚡ API Gateway / Backend <br> (FastAPI / Uvicorn :8000)"]
        DB[(🗄️ Base de Datos <br> PostgreSQL 15 :5432)]
        Redis[(🧠 Broker / Caché <br> Redis 7 :6379)]
        Worker["⚙️ Procesador Asíncrono <br> Celery Worker"]
        LambdaRunner["☁️ AWS Lambda Simulator <br> Python Handler :8001"]
        Flower["📊 Dashboard de Colas <br> Celery Flower :5555"]
    end

    User["⚽ Cliente / Staff"] -->|HTTPS / REST| API
    API -->|SQL queries| DB
    API -->|Check limits / Distributed locks| Redis
    API -->|Enqueue task| Redis
    Redis -->|De-queue task| Worker
    Worker -->|Invoke HTTP| LambdaRunner
    Worker -->|Write QR png| SharedStorage["💾 Volumen Compartido <br> PVC (qrcodes)"]
    API -->|Read QR png| SharedStorage
    Flower -->|Read queue states| Redis
```

---

## 3. Diagrama de Secuencia Transaccional (Flujo de Compra Asíncrono)
Muestra la secuencia cronológica de una compra de boleto por un usuario, demostrando el desacoplamiento temporal de la cola y la lambda serverless.

```mermaid
sequenceDiagram
    autonumber
    actor Cliente as ⚽ Cliente Web
    participant API as ⚡ API Gateway
    participant Redis as 🧠 Redis Cache/Locks
    participant DB as 🗄️ PostgreSQL DB
    participant Celery as ⚙️ Celery Worker
    participant Lambda as ☁️ Lambda Runner

    Cliente->>API: POST /orders/checkout (Asiento A1)
    critical Intentar bloquear asiento
        API->>Redis: Set Lock: asiento:A1 (TTL 10s)
    end
    API->>DB: Validar disponibilidad y registrar Orden (Pnd)
    API->>Redis: Encolar tarea 'generar_boleto'
    API-->>Cliente: 202 Accepted {"order_id": 123, "status": "processing"}
    
    Note over Celery, Redis: El worker toma la tarea de la cola
    Celery->>Redis: Obtener tarea 'generar_boleto'
    
    activate Celery
    Celery->>Lambda: POST /payment (Monto $45)
    Lambda-->>Celery: 200 OK {"success": true, "tx_id": "999"}
    Celery->>Lambda: POST /generate_ticket (ticket_uuid)
    Lambda-->>Celery: 200 OK {"qr_code_url": "/static/qrcodes/uuid.png"}
    Celery->>DB: Actualizar Orden a 'Completada' y Asiento a 'Reservado'
    Celery->>Redis: Liberar Lock: asiento:A1
    deactivate Celery

    Cliente->>API: GET /tickets/uuid
    API->>DB: Consultar boleto y QR
    API-->>Cliente: 200 OK (Renderizar Boleto con QR)
```

---

## 4. Diagrama de Despliegue e Infraestructura (Kubernetes)
Detalla los componentes físicos de hardware y software en Rancher Desktop (Kubernetes local).

```mermaid
graph TB
    subgraph KubernetesCluster ["☸️ Clúster Local (Rancher Desktop / k3s)"]
        subgraph Namespace ["Namespace: ticket-futbol"]
            
            subgraph Services ["LoadBalancers & Services"]
                SvcAPI["Service api <br> (LoadBalancer :8000)"]
                SvcFlower["Service celery-flower <br> (LoadBalancer :5555)"]
                SvcDB["Service db <br> (ClusterIP :5432)"]
                SvcRedis["Service redis <br> (ClusterIP :6379)"]
            end

            subgraph Pods ["Pods Desplegados"]
                PodAPI1["pod: api-replica-1"]
                PodAPI2["pod: api-replica-2"]
                PodAPI3["pod: api-replica-3"]
                
                PodWorker["pod: celery-worker"]
                PodLambda["pod: lambda-runner"]
                PodDB["pod: postgres-db"]
                PodRedis["pod: redis-cache"]
                PodFlower["pod: celery-flower"]
            end
            
            PVC["PersistentVolumeClaim <br> (qrcodes-pvc)"]
        end
    end

    SvcAPI --> PodAPI1 & PodAPI2 & PodAPI3
    SvcFlower --> PodFlower
    PodAPI1 & PodAPI2 & PodAPI3 --> SvcDB & SvcRedis
    PodWorker --> SvcRedis & PodLambda
    
    PodWorker -->|Escribe QR| PVC
    PodAPI1 & PodAPI2 & PodAPI3 -->|Lee QR| PVC
```
