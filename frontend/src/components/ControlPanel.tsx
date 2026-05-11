import { useSystem } from "@/context/SystemContext";
import { Play, Square, OctagonX, Timer } from "lucide-react";

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600).toString().padStart(2, "0");
  const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${h}:${m}:${s}`;
}

const ControlPanel = () => {
  const { conveyorRunning, toggleConveyor, emergencyStop, sessionTime } = useSystem();

  return (
    <div className="flex items-center gap-3">
      {/* Session timer */}
      <div
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded border font-mono text-xs transition-all ${
          conveyorRunning
            ? "bg-success/10 border-success/30 text-success"
            : "bg-muted/30 border-border/40 text-muted-foreground"
        }`}
      >
        <Timer className={`w-3 h-3 ${conveyorRunning ? "animate-pulse" : ""}`} />
        {formatTime(sessionTime)}
      </div>

      {/* Start / Stop system button */}
      <button
        onClick={toggleConveyor}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold transition-all ${
          conveyorRunning
            ? "bg-warning/20 text-warning border border-warning/30 hover:bg-warning/30"
            : "bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30"
        }`}
      >
        {conveyorRunning ? <Square className="w-3 h-3" /> : <Play className="w-3 h-3" />}
        {conveyorRunning ? "Stop System" : "Start System"}
      </button>

      {/* Emergency stop */}
      <button
        onClick={emergencyStop}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold bg-destructive/20 text-destructive border border-destructive/30 hover:bg-destructive/30 transition-all"
      >
        <OctagonX className="w-3 h-3" />
        E-STOP
      </button>
    </div>
  );
};

export default ControlPanel;
