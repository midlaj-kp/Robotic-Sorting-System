import { useState, useEffect } from "react";
import { Barcode, RefreshCw, CheckCircle2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSystem } from "@/context/SystemContext";

interface QRData {
  data: string;
  category?: string;
  timestamp: number;
}

const QRScanner = () => {
  const { connected } = useSystem();
  const [qrData, setQrData] = useState<QRData | null>(null);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastScanned, setLastScanned] = useState<string | null>(null);

  // Poll for QR data every 500ms
  useEffect(() => {
    if (!connected) return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch("http://localhost:8000/api/qr/latest");
        const result = await response.json();

        if (result.detected && result.qr_data) {
          const newQR: QRData = {
            data: result.qr_data,
            category: result.qr_data.includes("A") ? "A" : "B",
            timestamp: Date.now(),
          };

          // Only update if QR data changed
          if (newQR.data !== lastScanned) {
            setQrData(newQR);
            setLastScanned(newQR.data);
            setError(null);
          }
        }
      } catch (e) {
        // Silent fail, backend might be down
      }
    }, 500);

    return () => clearInterval(interval);
  }, [connected, lastScanned]);

  const handleManualScan = async () => {
    if (!connected) {
      setError("Not connected to backend");
      return;
    }

    setScanning(true);
    setError(null);

    try {
      const response = await fetch("http://localhost:8000/api/qr/scan", {
        method: "POST",
      });
      const result = await response.json();

      if (result.found && result.data) {
        const newQR: QRData = {
          data: result.data,
          category: result.category || (result.data.includes("A") ? "A" : "B"),
          timestamp: Date.now(),
        };
        setQrData(newQR);
        setLastScanned(newQR.data);
        setError(null);
      } else {
        setError("No QR code detected in frame");
        setQrData(null);
      }
    } catch (e) {
      setError("Failed to scan QR code");
      setQrData(null);
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-header">
        <span>QR Code Scanner</span>
        {qrData && (
          <div className="flex items-center gap-1.5 text-xs text-success font-mono">
            <CheckCircle2 className="w-3 h-3" />
            DETECTED
          </div>
        )}
      </div>

      <div className="flex-1 flex flex-col gap-3 p-4 overflow-y-auto">
        {/* Scan Button */}
        <Button
          onClick={handleManualScan}
          disabled={!connected || scanning}
          className="w-full gap-2"
          variant={scanning ? "secondary" : "default"}
        >
          <RefreshCw className={`w-4 h-4 ${scanning ? "animate-spin" : ""}`} />
          {scanning ? "Scanning..." : "Scan QR Code"}
        </Button>

        {/* QR Data Display */}
        {qrData && (
          <div className="bg-primary/10 border border-primary rounded-lg p-3 space-y-2">
            <div className="flex items-start gap-2">
              <Barcode className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-muted-foreground font-mono">QR DATA</p>
                <p className="text-sm font-mono text-primary break-all font-semibold mt-1">
                  {qrData.data}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-primary/20">
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wide">
                  Category
                </p>
                <p className={`text-sm font-mono font-bold mt-1 ${
                  qrData.category === "A" ? "text-accent" : "text-warning"
                }`}>
                  {qrData.category === "A" ? "Type A" : "Type B"}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wide">
                  Timestamp
                </p>
                <p className="text-xs font-mono text-muted-foreground mt-1">
                  {new Date(qrData.timestamp).toLocaleTimeString("en-US", {
                    hour12: false,
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="bg-destructive/10 border border-destructive rounded-lg p-3 flex gap-2">
            <AlertCircle className="w-4 h-4 text-destructive flex-shrink-0 mt-0.5" />
            <p className="text-xs text-destructive">{error}</p>
          </div>
        )}

        {/* Status Message */}
        {!connected && (
          <div className="bg-muted/30 border border-border rounded-lg p-3 text-center">
            <p className="text-xs text-muted-foreground">
              Connect to backend to enable QR scanning
            </p>
          </div>
        )}

        {connected && !qrData && !error && (
          <div className="bg-secondary/20 border border-border rounded-lg p-3 text-center">
            <p className="text-xs text-muted-foreground">
              Click "Scan QR Code" to detect QR codes from the camera feed
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default QRScanner;
