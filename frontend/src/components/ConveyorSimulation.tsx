import { useSystem } from "@/context/SystemContext";
import { Package, ArrowRight, Timer } from "lucide-react";

function fmtTime(s: number) {
  const h = Math.floor(s / 3600).toString().padStart(2, "0");
  const m = Math.floor((s % 3600) / 60).toString().padStart(2, "0");
  const sec = (s % 60).toString().padStart(2, "0");
  return `${h}:${m}:${sec}`;
}

const categoryColor: Record<string, string> = {
  Metal: "text-accent",
  Plastic: "text-primary",
  Organic: "text-warning",
  Deformed: "text-destructive",
  Unknown: "text-muted-foreground",
};

const stateColor: Record<string, string> = {
  waiting: "bg-secondary",
  scanning: "bg-warning/30 border-warning",
  detected: "bg-primary/30 border-primary",
  moving: "bg-secondary border-border",
  "arm-picking": "bg-accent/20 border-accent",
  sorted: "bg-primary/20 border-primary/50",
};

const ConveyorSimulation = () => {
  const { objects, conveyorRunning, armState, armTargetBin, sessionTime } = useSystem();

  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-header">
        <span>Conveyor Belt & Robotic Arm</span>
        <div className="flex items-center gap-3">
          <span className={`flex items-center gap-1 text-xs font-mono ${conveyorRunning ? "text-success" : "text-muted-foreground"}`}>
            <Timer className={`w-3 h-3 ${conveyorRunning ? "animate-pulse" : ""}`} />
            {fmtTime(sessionTime)}
          </span>
          <span className={`text-xs ${conveyorRunning ? "text-success" : "text-muted-foreground"}`}>
            {conveyorRunning ? "● RUNNING" : "○ STOPPED"}
          </span>
        </div>
      </div>

      <div className="flex-1 relative p-4 overflow-hidden min-h-[160px]">
        {/* Zone Labels */}
        <div className="absolute top-2 left-2 text-xs text-muted-foreground font-mono">INPUT →</div>
        <div className="absolute top-2 right-2 flex gap-3 text-xs font-mono">
          <span className="text-success">BIN A ↖</span>
          <span className="text-warning">BIN B ↙</span>
          <span className="text-destructive">REJECT →</span>
        </div>

        {/* Belt track */}
        <div className="absolute bottom-14 left-4 right-4 h-14 rounded">
          <div className={`w-full h-full conveyor-belt rounded ${conveyorRunning ? "animate-conveyor" : ""}`} />
          <div className="absolute top-0 left-0 right-0 h-px bg-border" />
          <div className="absolute bottom-0 left-0 right-0 h-px bg-border" />

          {/* Camera / Scan zone at ~20% */}
          <div
            className="scan-zone absolute top-0 bottom-0 animate-scan-pulse"
            style={{ left: "17%", width: "10%" }}
          >
            <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-[10px] font-mono text-primary animate-blink whitespace-nowrap">
              ▼ CAMERA ▼
            </div>
          </div>

          {/* Arm / Sorting zone at ~65% */}
          <div
            className="absolute top-0 bottom-0 border-l-2 border-r-2 border-dashed border-accent/40"
            style={{ left: "62%", width: "10%" }}
          >
            <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-[10px] font-mono text-accent animate-blink whitespace-nowrap">
              ▼ ARM ZONE ▼
            </div>
          </div>

          {/* Robotic Arm SVG */}
          <svg
            className="absolute transition-all duration-300 ease-in-out"
            style={{
              left: "64%",
              bottom: "100%",
              width: "60px",
              height: "90px",
              transform: armState === "picking"
                ? "rotate(-15deg) translateY(-4px)"
                : armState === "placing"
                ? `rotate(${armTargetBin === "Bin A" ? "-40" : armTargetBin === "Reject" ? "30" : "10"}deg) translateY(-8px)`
                : "rotate(0deg)",
              transformOrigin: "50% 100%",
            }}
            viewBox="0 0 60 90"
          >
            {/* Base */}
            <rect x="22" y="80" width="16" height="10" rx="2" fill="hsl(220, 15%, 25%)" stroke="hsl(220, 15%, 35%)" strokeWidth="1" />
            {/* Lower arm */}
            <rect x="27" y="40" width="6" height="42" rx="3" fill="hsl(220, 15%, 30%)" stroke="hsl(var(--accent) / 0.6)" strokeWidth="1" />
            {/* Joint */}
            <circle cx="30" cy="40" r="5" fill="hsl(220, 15%, 22%)" stroke="hsl(var(--accent))" strokeWidth="1.5" />
            {/* Upper arm */}
            <rect x="27" y="10" width="6" height="32" rx="3" fill="hsl(220, 15%, 28%)" stroke="hsl(var(--accent) / 0.6)" strokeWidth="1" />
            {/* Shoulder joint */}
            <circle cx="30" cy="10" r="4" fill="hsl(220, 15%, 22%)" stroke="hsl(var(--accent))" strokeWidth="1.5" />
            {/* Gripper */}
            <path
              d={armState === "picking" ? "M24,2 L24,8 L20,12 M36,2 L36,8 L40,12" : "M25,2 L25,8 L22,10 M35,2 L35,8 L38,10"}
              fill="none"
              stroke="hsl(var(--primary))"
              strokeWidth="2"
              strokeLinecap="round"
            />
            {/* Gripper connector */}
            <rect x="24" y="0" width="12" height="4" rx="1" fill="hsl(220, 15%, 25%)" />
            {/* Status LED */}
            <circle
              cx="30" cy="42"
              r="2.5"
              fill={armState === "idle" ? "hsl(var(--muted-foreground))" : armState === "picking" ? "hsl(var(--warning))" : "hsl(var(--success))"}
              className={armState !== "idle" ? "animate-blink" : ""}
            />
          </svg>

          {/* Arm status label */}
          {armState !== "idle" && (
            <div
              className="absolute text-[9px] font-mono text-accent whitespace-nowrap"
              style={{ left: "62%", bottom: "calc(100% + 70px)" }}
            >
              {armState === "picking" ? `PICKING → ${armTargetBin}` : `PLACING → ${armTargetBin}`}
            </div>
          )}

          {/* Objects on belt */}
          {objects.map((obj) => {
            const isSorted = obj.state === "sorted";
            const armZone = 65; // Fixed arm zone percentage

            // When sorted, apply CSS transforms to simulate flying into a distinct bin bucket
            let animationTransform = "translateX(-50%)";
            let opacity = 1;

            if (isSorted) {
              if (obj.bin === "Bin A") {
                // Sort "Left" (Upwards in 2D view)
                animationTransform = "translate(-40px, -120px) scale(0.6) rotate(-45deg)";
                opacity = 0;
              } else if (obj.bin === "Bin B") {
                // Sort "Right" (Downwards in 2D view)
                animationTransform = "translate(-40px, 120px) scale(0.6) rotate(45deg)";
                opacity = 0;
              } else {
                // Reject: Move forward without sorting
                animationTransform = "translate(100px, 0px) scale(0.8)";
                opacity = 0;
              }
            }

            const binColor = obj.bin === "Bin A" ? "bg-success/30 border-success" 
                           : obj.bin === "Bin B" ? "bg-warning/30 border-warning"
                           : "bg-destructive/30 border-destructive";

            return (
              <div
                key={obj.id}
                className={`absolute -top-2 flex flex-col items-center transition-all ${
                  isSorted ? "ease-out" : "ease-linear"
                }`}
                style={{
                  left: isSorted ? `${armZone}%` : `${obj.position}%`,
                  transform: animationTransform,
                  opacity: opacity,
                  zIndex: isSorted ? 20 : 10,
                  transitionDuration: isSorted ? "1200ms" : "60ms",
                }}
              >
                <span className={`text-[9px] font-mono mb-0.5 max-w-[80px] truncate text-center ${categoryColor[obj.category]}`}>
                  {obj.qrData || ""}
                </span>
                <div
                  className={`w-9 h-9 rounded border flex items-center justify-center transition-colors ${
                    isSorted ? binColor : stateColor[obj.state]
                  }`}
                >
                  <Package className={`w-4 h-4 ${
                    obj.bin === "Bin A" ? "text-success" : 
                    obj.bin === "Bin B" ? "text-warning" : "text-destructive"
                  }`} />
                </div>
                <span className={`text-[8px] font-mono mt-0.5 ${categoryColor[obj.category]}`}>
                  {obj.bin}
                </span>
              </div>
            );
          })}
        </div>

        {/* Direction arrow */}
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1 text-muted-foreground">
          <ArrowRight className="w-4 h-4" />
          <span className="text-[10px] font-mono">DIRECTION OF TRAVEL</span>
        </div>

        {!conveyorRunning && objects.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/40 backdrop-blur-sm">
            <span className="text-muted-foreground text-sm font-mono">WAITING FOR DETECTIONS</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default ConveyorSimulation;
