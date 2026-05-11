import { useSystem } from "@/context/SystemContext";
import { useEffect, useState } from "react";
import { Wifi, WifiOff, Zap } from "lucide-react";

const TopNavBar = () => {
  const { connected, comPort, availablePorts, setComPort, connect, disconnect, refreshPorts } = useSystem();
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  return (
    <nav className="panel flex items-center justify-between px-5 py-3 gap-4">
      <div className="flex items-center gap-3">
        <Zap className="w-5 h-5 text-primary" />
        <h1 className="text-base font-bold tracking-wide neon-text">ROBOTIC SORTING SYSTEM</h1>
      </div>

      <div className="flex items-center gap-4">
        {/* Status */}
        <div className="flex items-center gap-2 text-sm">
          <span className={`status-dot ${connected ? "status-dot-connected" : "status-dot-disconnected"}`} />
          <span className={connected ? "text-success" : "text-destructive"}>
            {connected ? "Connected" : "Disconnected"}
          </span>
        </div>

        {/* COM Port */}
        <div className="flex items-center gap-1">
          <select
            value={comPort}
            onChange={(e) => setComPort(e.target.value)}
            disabled={connected}
            className="bg-secondary text-secondary-foreground border border-border rounded-l px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
          >
            {availablePorts.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <button
            onClick={() => refreshPorts()}
            disabled={connected}
            className="bg-secondary hover:bg-secondary/80 border border-l-0 border-border rounded-r px-2 py-1.5 text-muted-foreground disabled:opacity-50 transition-colors"
            title="Refresh Ports"
          >
            <Zap className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Connect Button */}
        <button
          onClick={connected ? disconnect : connect}
          className={`flex items-center gap-2 px-4 py-1.5 rounded text-sm font-semibold transition-all ${connected
            ? "bg-destructive/20 text-destructive border border-destructive/30 hover:bg-destructive/30"
            : "bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30"
            }`}
        >
          {connected ? <WifiOff className="w-4 h-4" /> : <Wifi className="w-4 h-4" />}
          {connected ? "Disconnect" : "Connect"}
        </button>

        {/* Time */}
        <div className="font-mono text-sm text-muted-foreground tabular-nums">
          {time.toLocaleTimeString("en-US", { hour12: false })}
        </div>
      </div>
    </nav>
  );
};
export default TopNavBar;
