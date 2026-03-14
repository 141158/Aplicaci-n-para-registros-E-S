import asyncio
import json
import psutil
import time
import threading
from websockets import serve

# Import libraries for input hooking and WMI
try:
    import wmi
    import pythoncom
    from pynput import keyboard, mouse
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    exit(1)

# Global variables to cache hardware resources
hw_info = {
    "keyboard": {"irq": "Unknown", "driver": "kbdclass.sys"},
    "mouse": {"irq": "Unknown", "driver": "mouclass.sys"},
    "disk": {"irq": "Unknown", "dma": "Unknown", "driver": "storahci.sys"}
}

clients = set()

def fetch_hardware_config():
    """Fetches real IRQ and DMA configs using WMI"""
    try:
        pythoncom.CoInitialize()
    except Exception:
        pass
    print("Fetching hardware configurations via WMI. This may take a few seconds...")
    try:
        c = wmi.WMI()
        # Find IRQs
        for res in c.Win32_AllocatedResource():
            try:
                antecedent_str = str(res.Antecedent) if res.Antecedent else ""
                dependent_str = str(res.Dependent) if res.Dependent else ""
                
                if "Win32_IRQResource" in antecedent_str:
                    try:
                        irq = antecedent_str.split('IRQNumber=')[1].split('"')[0]
                        dep_id = dependent_str.split('DeviceID="')[1].split('"')[0].replace('\\\\', '\\')
                        
                        if "KBD" in dep_id.upper() or "KEYBOARD" in dep_id.upper():
                            hw_info["keyboard"]["irq"] = irq
                        elif "MOU" in dep_id.upper() or "MOUSE" in dep_id.upper():
                            hw_info["mouse"]["irq"] = irq
                        elif "VEN_8086" in dep_id.upper() or "NVME" in dep_id.upper() or "AHCI" in dep_id.upper() or "STOR" in dep_id.upper():
                            hw_info["disk"]["irq"] = irq
                    except Exception:
                        pass
                        
                if "Win32_DMAChannel" in antecedent_str:
                     try:
                        dma = antecedent_str.split('DMAChannel=')[1].split('"')[0]
                        dep_id = dependent_str.split('DeviceID="')[1].split('"')[0].replace('\\\\', '\\')
                        if "IDE" in dep_id.upper() or "STOR" in dep_id.upper() or "AHCI" in dep_id.upper():
                            hw_info["disk"]["dma"] = dma
                     except Exception:
                        pass
            except Exception:
                pass
    except Exception as e:
        print(f"WMI Error: {e}")
        
    print(f"Hardware Mapped: {hw_info}")

# asyncio event queue
event_queue = asyncio.Queue()

def on_mouse_move(x, y):
    evt = {
        "device": "Mouse",
        "action": "Movimiento",
        "details": f"X:{x} Y:{y}",
        "hardware": hw_info["mouse"],
        "timestamp": time.time()
    }
    asyncio.run_coroutine_threadsafe(event_queue.put(evt), loop)

def on_mouse_click(x, y, button, pressed):
    evt = {
        "device": "Mouse",
        "action": "Clic" if pressed else "Soltar",
        "details": f"Botón:{button}",
        "hardware": hw_info["mouse"],
        "timestamp": time.time()
    }
    asyncio.run_coroutine_threadsafe(event_queue.put(evt), loop)

def on_mouse_scroll(x, y, dx, dy):
    evt = {
        "device": "Mouse",
        "action": "Rueda",
        "details": f"Dir:{'Arriba' if dy > 0 else 'Abajo'} (dy:{dy})",
        "hardware": hw_info["mouse"],
        "timestamp": time.time()
    }
    asyncio.run_coroutine_threadsafe(event_queue.put(evt), loop)

def on_key_press(key):
    try:
        k = key.char
    except AttributeError:
        k = str(key)
    evt = {
        "device": "Keyboard",
        "action": "Tecla",
        "details": f"Valor:{k}",
        "hardware": hw_info["keyboard"],
        "timestamp": time.time()
    }
    asyncio.run_coroutine_threadsafe(event_queue.put(evt), loop)

def start_input_hooks():
    # Start Mouse listener
    mouse_listener = mouse.Listener(on_move=on_mouse_move, on_click=on_mouse_click, on_scroll=on_mouse_scroll)
    mouse_listener.start()
    
    # Start Keyboard listener
    keyboard_listener = keyboard.Listener(on_press=on_key_press)
    keyboard_listener.start()

async def disk_monitor():
    """Polls disk IO and emits events if there's activity"""
    last_io = psutil.disk_io_counters()
    while True:
        await asyncio.sleep(0.5)
        current_io = psutil.disk_io_counters()
        read_bytes = current_io.read_bytes - last_io.read_bytes
        write_bytes = current_io.write_bytes - last_io.write_bytes
        
        if read_bytes > 0 or write_bytes > 0:
            evt = {
                "device": "Disk",
                "action": "Tráfico I/O",
                "details": f"Lectura: {read_bytes} B, Escritura: {write_bytes} B",
                "hardware": hw_info["disk"],
                "timestamp": time.time()
            }
            await event_queue.put(evt)
        last_io = current_io

async def broadcast_events():
    """Reads from event queue and broadcasts to all websocket clients"""
    while True:
        evt = await event_queue.get()
        if clients:
            message = json.dumps(evt)
            # Send to all connected clients
            await asyncio.gather(*(client.send(message) for client in clients))

async def trigger_isolated_io(target_drive, websocket):
    """Triggers an isolated file write/read seq to demonstrate DMA without background noise"""
    try:
        # 1. Provide disks list logic if asked
        if target_drive == "GET_DISKS":
            disks = []
            c = wmi.WMI()
            
            # Use MSFT_PhysicalDisk for accurate MediaType/BusType
            physical_disks_info = {}
            try:
                c_storage = wmi.WMI(namespace='root\\Microsoft\\Windows\\Storage')
                for pd in c_storage.MSFT_PhysicalDisk():
                    physical_disks_info[pd.Model.strip()] = {
                        "MediaType": pd.MediaType, # 4=SSD, 3=HDD
                        "BusType": pd.BusType      # 17=NVMe, 11=SATA
                    }
            except Exception:
                pass
            
            # Map physical to logical
            # This is a bit complex in WMI, we'll do an approximation for pedagogical purposes
            for disk in c.Win32_DiskDrive():
                model = disk.Model.strip()
                pd_info = physical_disks_info.get(model, {})
                
                # Better NVMe detection via Microsoft Storage WMI
                is_nvme = (pd_info.get("BusType") == 17) or ("NVME" in model.upper())
                is_ssd = (pd_info.get("MediaType") == 4) or ("SSD" in model.upper())
                
                if is_nvme:
                    media_type = "SSD/NVMe"
                elif is_ssd:
                    media_type = "SSD/SATA" 
                else:
                    media_type = "HDD/SATA"
                 
                expected_driver = "stornvme.sys" if is_nvme else "storahci.sys"
                
                # Try finding drive letters associated
                drive_letters = []
                for partition in disk.associators ("Win32_DiskDriveToDiskPartition"):
                    for logical_disk in partition.associators ("Win32_LogicalDiskToPartition"):
                        drive_letters.append(logical_disk.DeviceID)
                
                if not drive_letters:
                    # Fallback for some virtual or unmapped drives
                    drive_letters = ["PhysicalDrive" + str(disk.Index)]

                disks.append({
                    "id": drive_letters[0] if drive_letters else "Unknown",
                    "model": model,
                    "type": media_type,
                    "driver": expected_driver,
                    "size_gb": round(int(disk.Size) / (1024**3), 2) if disk.Size else 0
                })
            
            await websocket.send(json.dumps({
                "action": "DiskList",
                "disks": disks,
                "timestamp": time.time()
            }))
            return

        # 2. ISOLATED IO TRIGGER
        import os
        import tempfile
        
        # Determine a safe path to write on the target drive
        if "C:" in target_drive.upper():
            # Force use of the user's guaranteed temp directory for C:
            base_dir = tempfile.gettempdir()
        else:
            # For other drives, try a temp folder
            base_dir = f"{target_drive}\\Temp" if "\\" not in target_drive else f"{target_drive}\\Temp"
            try:
                os.makedirs(base_dir, exist_ok=True)
            except Exception:
                base_dir = tempfile.gettempdir() # Ultimate fallback
        
        # Create a 50MB dummy file safely
        dummy_path = os.path.join(base_dir, "test_dma_io.tmp")

        print(f"Triggering Isolated IO on {dummy_path}")
        
        # Send Start Signal
        await websocket.send(json.dumps({
            "action": "IsolatedIOStart",
            "target": target_drive,
            "timestamp": time.time()
        }))
        
        # Perform actual IO
        
        # Determine specific driver for this selected drive dynamically
        selected_driver = "storahci.sys" # Default
        try:
            c = wmi.WMI()
            c_storage = wmi.WMI(namespace='root\\Microsoft\\Windows\\Storage')
            
            physical_disks_info = {}
            for pd in c_storage.MSFT_PhysicalDisk():
                physical_disks_info[pd.Model.strip()] = pd.BusType

            for disk in c.Win32_DiskDrive():
                model = disk.Model.strip()
                is_nvme = (physical_disks_info.get(model) == 17) or ("NVME" in model.upper())
                
                for partition in disk.associators("Win32_DiskDriveToDiskPartition"):
                    for logical_disk in partition.associators("Win32_LogicalDiskToPartition"):
                        if logical_disk.DeviceID == target_drive:
                            selected_driver = "stornvme.sys" if is_nvme else "storahci.sys"
        except Exception:
            pass # fallback to default if WMI fails mid-flight

        # Write 50MB to force some actual flush to disk
        data = os.urandom(1024 * 1024 * 50)
        start_time = time.time()
        with open(dummy_path, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno()) # Force to hardware
            
        write_time = time.time() - start_time
        
        # Read it back
        start_time = time.time()
        with open(dummy_path, "rb") as f:
            _ = f.read()
            
        read_time = time.time() - start_time
        
        # Delete dummy
        os.remove(dummy_path)
        
        # Send Sequence (this simulates the physical events that just happened)
        # We send these synthetic events because PSUtil is too general, and we want
        # to show the exact pipeline for THIS specific file op.
        
        seq_start = time.time()
        events = [
            {"device": "User Space", "action": "API I/O", "details": f"ntdll.dll!NtWriteFile({dummy_path}) - 50MB Async", "timestamp": seq_start},
            {"device": "OS Kernel", "action": "IRP", "details": "I/O Manager crea IRP_MJ_WRITE y lo envía al driver de la pila de almacenamiento", "timestamp": seq_start + 0.001},
            {"device": "OS Kernel", "action": "HAL", "details": f"Configurando DMA/SGL para Controlador {selected_driver}", "timestamp": seq_start + 0.002},
            {"device": "Hardware", "action": "DMA", "details": f"Transferencia Maestra a RAM (Buffer {target_drive}) -> 50MB/s (Aprox {round(50/write_time, 1)}MB/s real)", "timestamp": seq_start + 0.003},
            {"device": "OS Kernel", "action": "IRQ", "details": f"Controlador dispara {hw_info['disk'].get('irq', 'IRQ')} -> Transferencia de Escritura OK", "timestamp": seq_start + 0.020},
            {"device": "OS Kernel", "action": "ISR", "details": f"ISR en {selected_driver} atendiendo interrupción y marcando IRP como completado", "timestamp": seq_start + 0.021},
            
            {"device": "User Space", "action": "API I/O", "details": f"ntdll.dll!NtReadFile({dummy_path}) - 50MB Async", "timestamp": seq_start + 0.100},
            {"device": "OS Kernel", "action": "IRP", "details": "I/O Manager crea IRP_MJ_READ y lo envía al driver de la pila de almacenamiento", "timestamp": seq_start + 0.101},
            {"device": "OS Kernel", "action": "HAL", "details": f"Configurando DMA/SGL para Controlador {selected_driver}", "timestamp": seq_start + 0.102},
            {"device": "Hardware", "action": "DMA", "details": f"Transferencia Maestra RAM a CPU -> 50MB/s (Aprox {round(50/read_time, 1)}MB/s real)", "timestamp": seq_start + 0.103},
            {"device": "OS Kernel", "action": "IRQ", "details": f"Controlador dispara {hw_info['disk'].get('irq', 'IRQ')} -> Transferencia LECTURA OK", "timestamp": seq_start + 0.120},
            {"device": "OS Kernel", "action": "ISR", "details": f"ISR en {selected_driver} completando DPC I/O y marcando IRP", "timestamp": seq_start + 0.121},
            {"device": "System", "action": "IsolatedIOClear", "details": "Secuencia Completada", "timestamp": seq_start + 0.150}
        ]
        
        for e in events:
            await websocket.send(json.dumps(e))
            await asyncio.sleep(0.02) # Small delay for visual effect

    except Exception as e:
        print(f"Error in isolated IO: {e}")
        await websocket.send(json.dumps({
            "action": "IsolatedIOError",
            "details": str(e),
            "timestamp": time.time()
        }))

async def handle_client(websocket):
    clients.add(websocket)
    print(f"Client connected. Total clients: {len(clients)}")
    try:
        # Send initial hardware info
        await websocket.send(json.dumps({
            "device": "System",
            "action": "Init",
            "details": hw_info,
            "timestamp": time.time()
        }))
        
        # Listen for commands from frontend (new functionality)
        async for message in websocket:
            try:
                data = json.loads(message)
                if data.get("command") == "trigger_isolated_io":
                    # Start IO in background task so we don't block the websocket loop
                    asyncio.create_task(trigger_isolated_io(data.get("target_disk"), websocket))
            except json.JSONDecodeError:
                pass
                
        await websocket.wait_closed()
    except Exception as e:
        print(f"Websocket error: {e}")
    finally:
        clients.remove(websocket)
        print("Client disconnected.")

async def main():
    print("Starting OS Real E/S Event Capture Server...")
    
    # Run WMI fetch in a separate thread so it doesn't block async setup
    wmi_thread = threading.Thread(target=fetch_hardware_config)
    wmi_thread.start()
    
    start_input_hooks()
    
    print("Starting WebSocket Server on ws://localhost:8765")
    async with serve(handle_client, "localhost", 8765):
        # Start disk monitor loop and event broadcaster
        await asyncio.gather(
            disk_monitor(),
            broadcast_events()
        )

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Server shutdown.")
