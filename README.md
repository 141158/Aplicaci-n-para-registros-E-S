<<<<<<< HEAD
# Aplicaci-n-para-registros-E-S
=======
# Monitor Integral de Eventos de E/S del Sistema Operativo

Esta aplicación es una herramienta educativa, de visualización y análisis, diseñada para inspeccionar en tiempo real cómo el Sistema Operativo interactúa con el hardware subyacente (Teclado, Ratón y Discos de Almacenamiento HDD/NVMe). Fue desarrollada para ilustrar conceptos avanzados de la arquitectura de la computadora.

## Autor
* **Cesar Andersson Saire Hancco**
* **Código de Estudiante:** 141158

## Componentes del Proyecto

El proyecto está dividido en dos partes principales impulsadas por WebSockets para comunicación en tiempo-real:

1. **Backend (Python):** `backend_os.py`
2. **Frontend (HTML/JS/CSS):** `index.html`, `app.js`, `styles.css`

## Características Principales

*   **Detección Dinámica de Hardware (WMI):** Escanea el hardware instalado usando las APIs nativas de Windows (`Win32` y `MSFT_PhysicalDisk`) para descubrir líneas de interrupción (IRQ), modelo de discos físicos, y el subsistema de bus real (ej. `SATA` vs `NVMe`).
*   **Monitoreo Transparente (Hooking):** Intercepta de manera asíncrona la actividad de los periféricos de entrada (Teclados y Ratones) usando la biblioteca `pynput`, sin estorbar el flujo normal de las aplicaciones.
*   **Visualizador Glassmorphism:** Una interfaz web moderna que muestra el registro de eventos en una consola que imita terminales, separando por categorías.
*   **Cámara de Captura de Disco Aislada:** Un módulo diseñado para forzar cargas físicas (eludiendo cachés como el sistema de archivos de Windows a través de `os.fsync`) en el almacenamiento seleccionado, para luego reconstruir el pipeline de eventos arquitectónicos, exponiendo:
    * Llamadas a la API del ESPACIO DE USUARIO (`NtWriteFile` / `NtReadFile`).
    * Creación de un **Paquete IRP** en el Kernel.
    * Configuración de la capa **HAL** y uso activo de **DMA** adaptado al driver correcto (`stornvme.sys` vs `storahci.sys`).
    * Retorno de **Línea de Interrupción (IRQ)** del hardware físico a la CPU.
    * Respuesta de la Rutina de Servicio de Interrupción **(ISR)** para despertar a la aplicación llamante y completar el ciclo.
    * Tasa de transferencia calculada del ancho de banda nativo del hardware (MB/s).

## Requisitos de Instalación

Para ejecutar esta aplicación en un entorno local, necesitas tener Python 3.7+ instalado y ejecutar los siguientes comandos para las dependencias:

```bash
pip install asyncio
pip install websockets
pip install psutil
pip install pynput
pip install wmi
pip install pypiwin32
```

## Instrucciones de Uso

1.  Abre una terminal de línea de comandos en la ruta de este repositorio.
2.  Ejecuta el servidor de Python como Administrador (Se recomienda para lectura profunda WMI):
    ```bash
    python backend_os.py
    ```
3.  Abre el archivo de interfaz `index.html` en cualquier navegador web moderno.
4.  Interactúa con tu teclado y mouse, y observa cómo los eventos se visualizan en tiempo real.
5.  Abre la característica **Cámara de Captura Avanzada**, selecciona tu almacenamiento principal, y fuerza una carga de I/O para observar detalladamente la cascada de interacciones del Kernel.

## Licencia & Créditos

Este proyecto es de uso académico y está diseñado para profundizar el análisis técnico de subrutinas de la arquitectura del PC y de los Sistemas Operativos bajo plataformas Windows NT.
>>>>>>> a5b250f (first commit)
