import { useSystem, LogLevel } from "@/context/SystemContext";
import { useState, useRef, useEffect } from "react";
import { Trash2, Info, AlertTriangle, XCircle } from "lucide-react";

const levelConfig: Record<LogLevel, { icon: typeof Info; color: string; badge: string }> = {
  info: { icon: Info, color: "text-accent", badge: "bg-accent/15 text-accent" },
  warning: { icon: AlertTriangle, color: "text-warning", badge: "bg-warning/15 text-warning" },
  error: { icon: XCircle, color: "text-destructive", badge: "bg-destructive/15 text-destructive" },
};

const LogPanel = () => {
  const { logs, clearLogs } = useSystem();
  const [filter, setFilter] = useState<LogLevel | "all">("all");
  const scrollRef = useRef<HTMLDivElement>(null);

  const filtered = filter === "all" ? logs : logs.filter((l) => l.level === filter);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [logs]);

  const filters: Array<{ key: LogLevel | "all"; label: string }> = [
    { key: "all", label: "All" },
    { key: "info", label: "Info" },
    { key: "warning", label: "Warn" },
    { key: "error", label: "Error" },
  ];

  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-header">
        <div className="flex items-center gap-3">
          <span>System Logs</span>
          <div className="flex gap-1">
            {filters.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setFilter(key)}
                className={`text-[10px] px-2 py-0.5 rounded font-mono transition-colors ${
                  filter === key ? "bg-primary/20 text-primary" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <button onClick={clearLogs} className="text-muted-foreground hover:text-foreground transition-colors">
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto max-h-[200px]">
        {filtered.length === 0 ? (
          <div className="text-center text-muted-foreground text-xs font-mono py-8">No logs</div>
        ) : (
          filtered.map((entry) => {
            const config = levelConfig[entry.level] || levelConfig.info;
            const Icon = config.icon;
            return (
              <div key={entry.id} className="log-entry flex items-start gap-2">
                <span className="text-muted-foreground font-mono shrink-0">{entry.timestamp}</span>
                <span className={`${config.badge} text-[10px] px-1.5 py-0 rounded font-mono uppercase shrink-0`}>
                  {entry.level}
                </span>
                <Icon className={`w-3 h-3 mt-0.5 ${config.color} shrink-0`} />
                <span className="text-foreground/80 break-all">{entry.message}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default LogPanel;
