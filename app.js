const wsUrl = "ws://localhost:8765";
let ws;
const maxLogLines = 100;

// DOM Elements
const statusBadge = document.getElementById("connectionStatus");
const eventLog = document.getElementById("eventLog");
const clearBtn = document.getElementById("clearBtn");

// Cards
const cards = {
    keyboard: document.getElementById("hw-keyboard"),
    mouse: document.getElementById("hw-mouse"),
    disk: document.getElementById("hw-disk")
};

// Activity Indicators
const indicators = {
    keyboard: document.getElementById("kb-act"),
    mouse: document.getElementById("ms-act"),
    disk: document.getElementById("ds-act")
};

// Details
const details = {
    kbIrq: document.getElementById("kb-irq"),
    kbDriver: document.getElementById("kb-driver"),
    msIrq: document.getElementById("ms-irq"),
    msDriver: document.getElementById("ms-driver"),
    dsIrq: document.getElementById("ds-irq"),
    dsDriver: document.getElementById("ds-driver")
};

// Pipeline Nodes
const pipeNodes = {
    hw: document.getElementById("pipe-hw"),
    irq: document.getElementById("pipe-irq"),
    kernel: document.getElementById("pipe-kernel"),
    user: document.getElementById("pipe-user")
};

function initWebSocket() {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        statusBadge.textContent = "Conectado al Interceptor OS Reales";
        statusBadge.className = "status-badge connected";
        addLog({ device: "System", action: "Info", details: "WebSocket conectado exitosamente." }, "info");
    };

    ws.onclose = () => {
        statusBadge.textContent = "Desconectado. Reconectando...";
        statusBadge.className = "status-badge disconnected";
        addLog({ device: "System", action: "Error", details: "Conexión perdida con backend_os.py" }, "error");
        setTimeout(initWebSocket, 2000);
    };

    ws.onerror = (err) => {
        console.error("WS Error:", err);
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleIncomingEvent(data);
        } catch(e) {
            console.error("Error parseando mensaje WS:", e);
        }
    };
}

function handleIncomingEvent(data) {
    if (data.action === "Init") {
        updateHardwareInfo(data.details);
        return;
    }

    if (currentFilter !== "all" && data.device && data.device !== currentFilter && data.device !== "System") {
        return; // Drop event completely if not matching strict filter
    }

    // Ping animations
    pingDevice(data.device.toLowerCase());
    animatePipeline();

    // Determine type for CSS
    let typeClass = "info";
    if (data.device === "Keyboard") typeClass = "keyboard-log";
    else if (data.device === "Mouse") typeClass = "mouse-log";
    else if (data.device === "Disk") typeClass = "disk-log";

    // 1. Log the literal Hardware event
    addLog(data, typeClass);

    // 2. Generate detailed simulated micro-traces for OS course
    generateOsMicroTraces(data, typeClass);
}

function generateOsMicroTraces(data, typeClass) {
    if (data.device === "Disk") {
        // Disk DMA traces
        setTimeout(() => addLog({ device: "OS Kernel", action: "HAL", details: `Configurando Controlador DMA para ${data.hardware.dma !== 'Unknown' ? 'CH '+data.hardware.dma : 'PCIe/Bus Master'}...`, timestamp: data.timestamp + 0.001 }, "info"), 100);
        setTimeout(() => addLog({ device: "Hardware", action: "DMA", details: `Transfiriendo bytes directo a RAM (Omite CPU via ${data.hardware.driver})`, timestamp: data.timestamp + 0.003 }, typeClass), 200);
        setTimeout(() => addLog({ device: "OS Kernel", action: "IRQ", details: `Controlador de Disco dispara IRQ ${data.hardware.irq} -> CPU Interrumpida`, timestamp: data.timestamp + 0.005 }, "error"), 300);
        setTimeout(() => addLog({ device: "OS Kernel", action: "ISR", details: `Ejecutando Rutina de Interrupción en ${data.hardware.driver}`, timestamp: data.timestamp + 0.006 }, "info"), 400);
        setTimeout(() => addLog({ device: "User Space", action: "API I/O", details: `NTDLL.dll resolviendo callback de ReadFile/WriteFile async`, timestamp: data.timestamp + 0.008 }, "info"), 500);
    } else if (data.device === "Keyboard" || data.device === "Mouse") {
        // Input IRQ traces
        setTimeout(() => addLog({ device: "OS Kernel", action: "HAL", details: `APIC Enrutando IRQ Físico ${data.hardware.irq} a CPU Core 0`, timestamp: data.timestamp + 0.001 }, "error"), 50);
        setTimeout(() => addLog({ device: "OS Kernel", action: "Cambio de Contexto", details: `CPU Suspende hilo actual -> Transición a Anillo 0`, timestamp: data.timestamp + 0.002 }, "info"), 100);
        setTimeout(() => addLog({ device: "OS Kernel", action: "ISR", details: `El ISR de ${data.hardware.driver} recupera de Puerto I/O HW`, timestamp: data.timestamp + 0.003 }, typeClass), 150);
        setTimeout(() => addLog({ device: "OS Kernel", action: "DPC", details: `Procedimiento Diferido Encolado (Baja a prioridad de IRQL)`, timestamp: data.timestamp + 0.004 }, "info"), 200);
        setTimeout(() => addLog({ device: "User Space", action: "Win32k", details: `Entrada inyectada a la Cola de Mensajes de Interfaz (csrss.exe)`, timestamp: data.timestamp + 0.006 }, "info"), 250);
    }
}

function updateHardwareInfo(hw) {
    if(hw.keyboard) {
        details.kbIrq.textContent = hw.keyboard.irq;
        details.kbDriver.textContent = hw.keyboard.driver;
    }
    if(hw.mouse) {
        details.msIrq.textContent = hw.mouse.irq;
        details.msDriver.textContent = hw.mouse.driver;
    }
    if(hw.disk) {
        details.dsIrq.textContent = hw.disk.dma !== "Unknown" ? `DMA ${hw.disk.dma}` : `IRQ ${hw.disk.irq}`;
        details.dsDriver.textContent = hw.disk.driver;
    }
}

let pipeTimeout;
function animatePipeline() {
    // Reset
    Object.values(pipeNodes).forEach(n => n.classList.remove("firing"));
    clearTimeout(pipeTimeout);

    // Flow animation
    pipeNodes.hw.classList.add("firing");
    
    setTimeout(() => {
        pipeNodes.hw.classList.remove("firing");
        pipeNodes.irq.classList.add("firing");
    }, 50);

    setTimeout(() => {
        pipeNodes.irq.classList.remove("firing");
        pipeNodes.kernel.classList.add("firing");
    }, 100);

    setTimeout(() => {
        pipeNodes.kernel.classList.remove("firing");
        pipeNodes.user.classList.add("firing");
    }, 150);

    pipeTimeout = setTimeout(() => {
        pipeNodes.user.classList.remove("firing");
    }, 250);
}

function pingDevice(devKey) {
    if(!indicators[devKey] || !cards[devKey]) return;

    // Reset animation
    indicators[devKey].classList.remove("ping");
    void indicators[devKey].offsetWidth; // trigger reflow
    indicators[devKey].classList.add("ping");

    cards[devKey].classList.add("active-hw");
    setTimeout(() => {
        cards[devKey].classList.remove("active-hw");
    }, 200);
}

let currentFilter = "all";

function addLog(data, typeClass, targetLogElement = eventLog) {
    const line = document.createElement("div");
    line.className = `log-line ${typeClass}`;

    if (data.device && data.device !== "System") {
        line.setAttribute("data-device", data.device);
    }

    const tstamp = data.timestamp ? new Date(data.timestamp * 1000).toISOString().split('T')[1].slice(0, 12) : new Date().toISOString().split('T')[1].slice(0, 12);
    
    line.innerHTML = `<span class="time">[${tstamp}]</span>
                      <span class="dev">${data.device || 'OS'} </span>
                      <span class="evt">${data.action || ''}</span>
                      <span class="dtl">${data.details || ''}</span>`;

    targetLogElement.appendChild(line);

    // Auto-scroll
    targetLogElement.scrollTop = targetLogElement.scrollHeight;

    // Limit logs
    while (targetLogElement.childElementCount > maxLogLines) {
        targetLogElement.removeChild(targetLogElement.firstChild);
    }
}

clearBtn.addEventListener("click", () => {
    eventLog.innerHTML = `<div class="log-line info">[System] Log limpiado. Esperando eventos...</div>`;
});

// Setup filter listeners
const filterBtns = document.querySelectorAll(".filter-btn");
filterBtns.forEach(btn => {
    btn.addEventListener("click", (e) => {
        filterBtns.forEach(b => b.classList.remove("active"));
        e.target.classList.add("active");
        
        currentFilter = e.target.getAttribute("data-filter");
        
        // Clear log on switch for maximum order
        eventLog.innerHTML = `<div class="log-line info">[System] Filtro '${currentFilter}' activado. Capturando exclusivamente este dispositivo...</div>`;
    });
});

// ==========================================
// Advanced Disk Capture Logic
// ==========================================

const modal = document.getElementById("diskCaptureModal");
const btnOpenDiskCapture = document.getElementById("btnOpenDiskCapture");
const btnCloseDiskCapture = document.getElementById("btnCloseDiskCapture");
const diskSelect = document.getElementById("diskSelect");
const selectedDiskDetails = document.getElementById("selectedDiskDetails");
const btnTriggerIO = document.getElementById("btnTriggerIO");
const isolatedEventLog = document.getElementById("isolatedEventLog");
const ioStatus = document.getElementById("ioStatus");

let availableDisks = [];
let isCapturingIsolated = false;

btnOpenDiskCapture.addEventListener("click", () => {
    modal.classList.remove("hidden");
    // Request disks from backend
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ command: "trigger_isolated_io", target_disk: "GET_DISKS" }));
    }
});

btnCloseDiskCapture.addEventListener("click", () => {
    modal.classList.add("hidden");
});

diskSelect.addEventListener("change", (e) => {
    const selectedId = e.target.value;
    if (!selectedId) {
        selectedDiskDetails.classList.add("hidden");
        btnTriggerIO.disabled = true;
        return;
    }

    const diskInfo = availableDisks.find(d => d.id === selectedId);
    if (diskInfo) {
        document.getElementById("metaModel").textContent = diskInfo.model;
        document.getElementById("metaType").textContent = diskInfo.type;
        document.getElementById("metaSize").textContent = diskInfo.size_gb;
        selectedDiskDetails.classList.remove("hidden");
        btnTriggerIO.disabled = false;
    }
});

btnTriggerIO.addEventListener("click", () => {
    const targetDrive = diskSelect.value;
    if (!targetDrive) return;

    btnTriggerIO.disabled = true;
    diskSelect.disabled = true;
    isCapturingIsolated = true;
    
    // Clear isolated log
    isolatedEventLog.innerHTML = `<div class="log-line info">[System] Iniciando operación I/O en ${targetDrive}...</div>`;
    ioStatus.textContent = "Ejecutando operación física...";
    ioStatus.style.color = "#f1e05a";

    // Send command
    ws.send(JSON.stringify({ command: "trigger_isolated_io", target_disk: targetDrive }));
});

// We need to intercept messages in handleIncomingEvent or before
// Let's modify the ws.onmessage slightly to handle special actions first:

const originalOnMessage = ws ? ws.onmessage : null; // Will set this in initWebSocket properly

// Updating initWebSocket
function initWebSocket() {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        statusBadge.textContent = "Conectado al Interceptor OS Reales";
        statusBadge.className = "status-badge connected";
        addLog({ device: "System", action: "Info", details: "WebSocket conectado exitosamente." }, "info");
    };

    ws.onclose = () => {
        statusBadge.textContent = "Desconectado. Reconectando...";
        statusBadge.className = "status-badge disconnected";
        addLog({ device: "System", action: "Error", details: "Conexión perdida con backend_os.py" }, "error");
        setTimeout(initWebSocket, 2000);
    };

    ws.onerror = (err) => {
        console.error("WS Error:", err);
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            
            // Handle Advanced Disk Payload
            if (data.action === "DiskList") {
                availableDisks = data.disks;
                diskSelect.innerHTML = '<option value="">-- Seleccione un Disco --</option>';
                availableDisks.forEach(disk => {
                    const opt = document.createElement("option");
                    opt.value = disk.id;
                    opt.textContent = `${disk.id} - ${disk.model} (${disk.type})`;
                    diskSelect.appendChild(opt);
                });
                return;
            }
            
            // Handle Isolated Sequence
            if (data.action === "IsolatedIOStart") {
                addLog(data, "disk-log", isolatedEventLog);
                return;
            }
            if (data.action === "IsolatedIOClear" || data.action === "IsolatedIOError") {
                btnTriggerIO.disabled = false;
                diskSelect.disabled = false;
                isCapturingIsolated = false;
                ioStatus.textContent = data.action === "IsolatedIOError" ? "Error" : "Completado";
                ioStatus.style.color = data.action === "IsolatedIOError" ? "#ff3366" : "#7ee787";
                addLog(data, data.action === "IsolatedIOError" ? "error" : "info", isolatedEventLog);
                return;
            }
            
            // If we are capturing isolated, and this is a synthetic kernel event directed to the modal
            if (isCapturingIsolated && (data.device === "OS Kernel" || data.device === "Hardware" || data.device === "User Space")) {
                // Determine CSS
                let tClass = "info";
                if(data.action === "IRQ") tClass = "error"; // red
                else if(data.action === "DMA") tClass = "disk-log"; // purple
                else if(data.action === "IRP") tClass = "info"; // gray/italic for packet creation
                else if(data.action === "ISR") tClass = "keyboard-log"; // blueish
                
                addLog(data, tClass, isolatedEventLog);
                
                // Do NOT send these synthetic events to main log
                return; 
            }

            // Normal flow
            handleIncomingEvent(data);
        } catch(e) {
            console.error("Error parseando mensaje WS:", e);
        }
    };
}

// Initial Call to setup WS
initWebSocket();
