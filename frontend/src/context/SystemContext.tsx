import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from "react";

export type ObjectCategory = "Metal" | "Plastic" | "Organic" | "Deformed" | "Unknown";
export type SortBin = "Bin A" | "Bin B" | "Reject";
export type LogLevel = "info" | "warning" | "error";
export type ObjectState = "waiting" | "scanning" | "detected" | "moving" | "arm-picking" | "sorted";
export type CameraStatus = "idle" | "scanning" | "detected" | "sorting";

export interface ConveyorObject {
  id: string;
  qrData?: string;
  category: ObjectCategory;
  confidence: number;
  bin: SortBin;
  position: number;
  state: ObjectState;
  timestamp: string;
  material?: string;
  origin?: string;
  damageScore: number;
}

export interface LogEntry {
  id: string;
  level: LogLevel;
  message: string;
  timestamp: string;
}

interface SystemState {
  connected: boolean;
  comPort: string;
  availablePorts: string[];
  conveyorRunning: boolean;
  cameraActive: boolean;
  objects: ConveyorObject[];
  currentProduct: ConveyorObject | null;
  cameraStatus: CameraStatus;
  logs: LogEntry[];
  stats: { total: number; Metal: number; Plastic: number; Organic: number; Deformed: number; Unknown: number };
  armState: "idle" | "picking" | "placing";
  armTargetBin: SortBin | null;
}

interface SystemContextType extends SystemState {
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  setComPort: (port: string) => void;
  toggleConveyor: () => Promise<void>;
  toggleCamera: () => Promise<void>;
  emergencyStop: () => Promise<void>;
  clearLogs: () => void;
  refreshPorts: () => Promise<void>;
  sessionTime: number;
}

const SystemContext = createContext<SystemContextType | null>(null);

const BACKEND_URL = "http://localhost:8000/api";
const WS_URL = "ws://localhost:8000/ws";

const CAMERA_ZONE = 20;
const ARM_ZONE = 65;
const EXIT_ZONE = 95;

function now(): string {
  return new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

// Map backend decisions to frontend friendly UI categories
function mapCategory(backendCat: string): ObjectCategory {
  if (backendCat === "A") return "Metal";
  if (backendCat === "B") return "Plastic";
  if (backendCat === "DEFORMED") return "Deformed";
  return "Unknown";
}

function mapBin(decision: string): SortBin {
  if (decision === "SORT_LEFT") return "Bin A";
  if (decision === "SORT_RIGHT") return "Bin B";
  return "Reject";
}

export const SystemProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [connected, setConnected] = useState(false);
  const [comPort, setComPort] = useState("COM3");
  const [availablePorts, setAvailablePorts] = useState<string[]>(["COM1", "COM2", "COM3", "COM4", "COM5"]);
  const [conveyorRunning, setConveyorRunning] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [objects, setObjects] = useState<ConveyorObject[]>([]);
  const [currentProduct, setCurrentProduct] = useState<ConveyorObject | null>(null);
  const [cameraStatus, setCameraStatus] = useState<CameraStatus>("idle");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [stats, setStats] = useState({ total: 0, Metal: 0, Plastic: 0, Organic: 0, Deformed: 0, Unknown: 0 });
  const [armState, setArmState] = useState<"idle" | "picking" | "placing">("idle");
  const [armTargetBin, setArmTargetBin] = useState<SortBin | null>(null);
  const [sessionTime, setSessionTime] = useState(0); // seconds since conveyor started

  // Declared early so WS onmessage closure captures the live setter (not a stale one)
  const [lastSelectedProduct, setLastSelectedProduct] = useState<ConveyorObject | null>(null);
  const retentionTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const sessionTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const processedIds = useRef<Set<string>>(new Set());

  const addLog = useCallback((level: LogLevel, message: string) => {
    setLogs((prev) => [{ id: crypto.randomUUID(), level, message, timestamp: now() }, ...prev].slice(0, 200));
  }, []);

  // Sync available ports
  const refreshPorts = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/ports`);
      const ports = await res.json();
      if (ports && ports.length > 0) {
        setAvailablePorts(ports);
        // If current comPort is not in the list, set to first available
        setComPort((current) => (ports.includes(current) ? current : ports[0]));
      }
    } catch (err) {
      console.error("Failed to fetch ports:", err);
    }
  }, []);

  useEffect(() => {
    refreshPorts();
  }, [refreshPorts]);

  const connect = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/connect?port=${comPort}`, { method: "POST" });
      const data = await res.json();
      
      if (res.ok) {
        setConnected(true);
        addLog("info", `✓ Connected to Arduino on ${comPort}`);
      } else {
        const errorMsg = data.detail || "Unknown error";
        addLog("error", `Failed connection: ${errorMsg}`);
      }
    } catch (err) {
      addLog("error", `Backend server offline`);
      console.error("Connection error:", err);
    }
  }, [comPort, addLog]);

  const disconnect = useCallback(async () => {
    try {
      await fetch(`${BACKEND_URL}/disconnect`, { method: "POST" });
    } catch {}
    setConnected(false);
    setConveyorRunning(false);
    setCameraActive(false);
    setObjects([]);
    setCurrentProduct(null);
    setCameraStatus("idle");
    setArmState("idle");
    setArmTargetBin(null);
    if(wsRef.current) wsRef.current.close();
    addLog("warning", `Disconnected system`);
  }, [addLog]);

  const toggleConveyor = useCallback(async () => {
    const newState = !conveyorRunning;
    try {
      if (newState) {
        await fetch(`${BACKEND_URL}/start`, { method: "POST" });
        setConveyorRunning(true);
        setCameraActive(true);
        setSessionTime(0); // reset timer on every fresh start
        addLog("info", "▶ System started — conveyor + camera active");
      } else {
        await fetch(`${BACKEND_URL}/stop`, { method: "POST" });
        setConveyorRunning(false);
        setCameraActive(false);
        setObjects([]);
        addLog("warning", "◼ System stopped");
      }
    } catch (err) {
      addLog("error", `Unable to communicate with backend`);
      console.error("Conveyor toggle error:", err);
    }
  }, [conveyorRunning, addLog]);

  const toggleCamera = useCallback(async () => {
    try {
      if (!cameraActive) {
        await fetch(`${BACKEND_URL}/start`, { method: "POST" });
        setCameraActive(true);
      } else {
        // We shouldn't stop the backend if conveyor is still running, 
        // but for simplicity we will just toggle the visual feed here.
        setCameraActive(false);
      }
    } catch {
      addLog("error", "Unable to hit camera backend");
    }
  }, [cameraActive, addLog]);

  const emergencyStop = useCallback(async () => {
    await fetch(`${BACKEND_URL}/stop`, { method: "POST" });
    setConveyorRunning(false);
    setCameraActive(false);
    setCameraStatus("idle");
    setArmState("idle");
    setArmTargetBin(null);
    setObjects([]);
    setSessionTime(0);
    addLog("error", "⚠ EMERGENCY STOP ACTIVATED");
  }, [addLog]);

  const clearLogs = useCallback(() => setLogs([]), []);

  // WebSocket Listener Hook
  useEffect(() => {
    let ws: WebSocket | null = null;

    function connectWs() {
      // Prevent multiple connections
      if (ws && ws.readyState === WebSocket.OPEN) {
        return;
      }

      ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      addLog("info", "WebSocket connecting...");

      ws.onopen = () => {
        addLog("info", "✓ WebSocket connection established.");
      };

      ws.onclose = (event) => {
        addLog("warning", `WebSocket connection closed. Code: ${event.code}. Reconnecting in 3s...`);
        wsRef.current = null;
        // Automatically try to reconnect after a delay
        setTimeout(connectWs, 3000);
      };
      
      ws.onerror = (error) => {
        addLog("error", "WebSocket error. See browser console for details.");
        console.error("WebSocket Error:", error);
        // The onclose event will usually fire after an error, triggering reconnection.
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.event === "log_update") {
            const data = msg.data;
            // Show all log levels including INFO so 'rescanning started...' and
            // 'send data to arduino:' appear on the dashboard immediately
            addLog(data.level.toLowerCase() as LogLevel, data.message);
          }

          if (msg.event === "system_state") {
            const data = msg.data;
            setConveyorRunning(data.conveyor_running);
            setCameraActive(data.conveyor_running); // Use same flag
            addLog("info", "✓ Synced system state with backend");
          }

          if (msg.event === "conveyor_started") {
            setConveyorRunning(true);
            setCameraActive(true);
            addLog("info", "Conveyor started by backend");
          }

          if (msg.event === "conveyor_stopped") {
            setConveyorRunning(false);
            setCameraActive(false);
            addLog("warning", "Conveyor stopped by backend");
          }

          if (msg.event === "sorting_triggered") {
            const result = msg.data;

            if (!result?.qr_data || result?.sorting_decision === "ERROR") {
              return;
            }

            // Auto-start: belt was off, first scan just arrived — start the belt and reset timer
            const wasOff = !conveyorRunning;
            setConveyorRunning(true);
            if (wasOff) setSessionTime(0);

            const cat = mapCategory(result.category);
            const isHighDamage = result.qr_data?.includes("Furniture");
            const mockDamage = isHighDamage
              ? 40 + Math.floor(Math.random() * 20)
              : Math.floor(Math.random() * 7);
            const bin = isHighDamage ? "Reject" : mapBin(result.sorting_decision);

            const newObj: ConveyorObject = {
              id: result.id,
              qrData: result.qr_data,
              category: cat,
              confidence: result.confidence_score,
              bin: bin,
              position: CAMERA_ZONE,
              state: "moving", // Skip 'detected' intermediate state — go straight to moving for zero lag
              timestamp: now(),
              material: result.material,
              origin: result.origin,
              damageScore: mockDamage,
            };

            // Immediately update the details panel with the latest scan
            setLastSelectedProduct(newObj);
            // Clear any pending retention timer so the new item shows right away
            if (retentionTimerRef.current) {
              clearTimeout(retentionTimerRef.current);
              retentionTimerRef.current = null;
            }

            setObjects((prev) => {
              const existingIndex = prev.findIndex((o) => o.id === result.id);
              if (existingIndex >= 0) {
                const updated = [...prev];
                updated[existingIndex] = { ...newObj, position: prev[existingIndex].position, state: prev[existingIndex].state };
                return updated;
              }
              return [...prev, newObj];
            });
          }
        } catch (e) {
          console.error("Failed to parse WebSocket message:", e, event.data);
        }
      };
    }

    connectWs(); // Initial connection attempt

    // Cleanup on component unmount
    return () => {
      if (ws) {
        // Remove the onclose handler to prevent reconnection attempts on unmount
        ws.onclose = null; 
        ws.close();
        addLog("info", "WebSocket connection intentionally closed.");
      }
    };
  }, [addLog]);


  // Session timer — ticks every second while the conveyor is running
  useEffect(() => {
    if (conveyorRunning) {
      sessionTimerRef.current = setInterval(() => {
        setSessionTime((t) => t + 1);
      }, 1000);
    } else {
      if (sessionTimerRef.current) {
        clearInterval(sessionTimerRef.current);
        sessionTimerRef.current = null;
      }
    }
    return () => {
      if (sessionTimerRef.current) {
        clearInterval(sessionTimerRef.current);
        sessionTimerRef.current = null;
      }
    };
  }, [conveyorRunning]);

  // Movement Simulation Tick Loop
  // Uses a ref map to track per-object arm-hold timers so the sort animation
  // has a natural hold time before the fly-away transition fires.
  const armHoldTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const sortedAtRef = useRef<Map<string, number>>(new Map()); // id → timestamp when sorted

  useEffect(() => {
    if (!conveyorRunning) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }

    intervalRef.current = setInterval(() => {
      const now_ms = Date.now();
      setObjects((prev) => {
        if (prev.length === 0) return prev;

        const updated = prev.map((obj) => {
          // Already sorted — just let the CSS transition play
          if (obj.state === "sorted") return obj;

          // Arm zone: hold for 800ms before marking as sorted
          if (obj.position >= ARM_ZONE && obj.position < ARM_ZONE + 3 && obj.state === "moving") {
            if (!armHoldTimers.current.has(obj.id)) {
              const t = setTimeout(() => {
                armHoldTimers.current.delete(obj.id);
                sortedAtRef.current.set(obj.id, Date.now());
                setObjects((p) =>
                  p.map((o) => (o.id === obj.id ? { ...o, state: "sorted" as ObjectState } : o))
                );
              }, 800);
              armHoldTimers.current.set(obj.id, t);
            }
            return { ...obj, state: "arm-picking" as ObjectState, position: ARM_ZONE };
          }

          // Already in arm-picking hold — don't move
          if (obj.state === "arm-picking") return obj;

          // Move forward: ~0.5 units per 30ms
          return { ...obj, position: Math.min(obj.position + 0.5, 100) };
        });

        // Remove sorted objects only after the 1400ms CSS fly-away transition completes
        return updated.filter((o) => {
          if (o.state === "sorted") {
            const sortedAt = sortedAtRef.current.get(o.id) ?? 0;
            if (now_ms - sortedAt > 1400) {
              sortedAtRef.current.delete(o.id);
              return false;
            }
            return true;
          }
          return o.position < 100;
        });
      });
    }, 30); // 30ms ≈ 33 fps

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      // Clean up any pending arm-hold timers
      armHoldTimers.current.forEach((t) => clearTimeout(t));
      armHoldTimers.current.clear();
    };
  }, [conveyorRunning]);

  // DERIVED STATE: Compute UI indicators from object list to avoid state-mismatch lag
  useEffect(() => {
    const armObj = objects.find((o) => o.state === "arm-picking");
    const detectedObj = objects.find((o) => o.state === "detected");
    const scanningObj = objects.find((o) => o.state === "scanning");
    const sortedObj = objects.find((o) => o.state === "sorted");

    // Keep details panel in sync with the currently active belt object
    // (WS onmessage is the primary updater; this is a belt-state fallback)
    const activeObj = armObj || detectedObj || scanningObj || objects.find(o => o.state === "moving");
    if (activeObj) {
      setLastSelectedProduct((prev) =>
        // Only update if belt object has a newer scan (different id)
        prev?.id !== activeObj.id ? activeObj : prev
      );
    }
    // No timeout / null reset — last scanned product stays visible until next scan

    if (armObj) {
      if (armState === "idle") {
        setArmState("picking");
        setArmTargetBin(armObj.bin);
      }
      if (!processedIds.current.has(armObj.id)) {
        processedIds.current.add(armObj.id);
        setStats((s) => ({
          ...s,
          total: s.total + 1,
          [armObj.category]: s[armObj.category as keyof typeof s] + 1,
        }));
      }
    } else if (sortedObj && armState === "picking") {
      setArmState("placing");
      const timer = setTimeout(() => {
        setArmState("idle");
        setArmTargetBin(null);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [objects, armState]);

  // Derived visuals (Computed every render for zero lag)
  const derivedCameraStatus = (() => {
    if (objects.some(o => o.state === "arm-picking")) return "sorting";
    if (objects.some(o => o.state === "detected")) return "detected";
    if (objects.some(o => o.state === "scanning")) return "scanning";
    return cameraActive ? "idle" : "idle";
  })();


  return (
    <SystemContext.Provider
      value={{
        connected, comPort, availablePorts, conveyorRunning, cameraActive,
        objects, currentProduct: lastSelectedProduct, cameraStatus: derivedCameraStatus, logs, stats, armState, armTargetBin,
        connect, disconnect, setComPort, toggleConveyor, toggleCamera, emergencyStop, clearLogs, refreshPorts,
        sessionTime,
      }}
    >
      {children}
    </SystemContext.Provider>
  );
};

export const useSystem = () => {
  const ctx = useContext(SystemContext);
  if (!ctx) throw new Error("useSystem must be used within SystemProvider");
  return ctx;
};
