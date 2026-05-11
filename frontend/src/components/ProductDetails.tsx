import { useSystem } from "@/context/SystemContext";
import { Box, Tag, Percent, Clock, ArrowRightLeft, BarChart3, Barcode, RefreshCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";

const ProductDetails = () => {
  const { currentProduct, stats, connected } = useSystem();
  const prevIdRef = useRef<string | undefined>(undefined);
  const [isNewScan, setIsNewScan] = useState(false);

  // Flash indicator whenever product ID changes (new scan arrived)
  useEffect(() => {
    if (currentProduct?.id && currentProduct.id !== prevIdRef.current) {
      prevIdRef.current = currentProduct.id;
      setIsNewScan(true);
      const t = setTimeout(() => setIsNewScan(false), 1500);
      return () => clearTimeout(t);
    }
  }, [currentProduct?.id]);

  const details = [
    { icon: Box, label: "Product ID", value: currentProduct?.id ?? "—" },
    { icon: Barcode, label: "QR Data", value: currentProduct?.qrData ?? "—" },
    { icon: Tag, label: "Category", value: currentProduct?.category ?? "—" },
    { icon: Box, label: "Material", value: currentProduct?.material ?? "—" },
    { icon: ArrowRightLeft, label: "Origin", value: currentProduct?.origin ?? "—" },
    { icon: Percent, label: "Confidence", value: currentProduct ? `${(currentProduct.confidence * 100).toFixed(1)}%` : "—" },
    { icon: Clock, label: "Timestamp", value: currentProduct?.timestamp ?? "—" },
    { icon: ArrowRightLeft, label: "Sort Decision", value: currentProduct?.bin ?? "—" },
  ];


  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-header">
        <span>Product Details</span>
        {isNewScan && (
          <span className="flex items-center gap-1 text-[10px] font-mono text-success bg-success/10 border border-success/30 px-2 py-0.5 rounded animate-pulse">
            <RefreshCw className="w-3 h-3" />
            NEW SCAN
          </span>
        )}
        {!isNewScan && currentProduct && (
          <span className="text-[10px] font-mono text-muted-foreground">LAST SCAN</span>
        )}
      </div>

      <div className="flex-1 p-3 space-y-2 overflow-y-auto">
        {details.map(({ icon: Icon, label, value }) => (
          <div
            key={label}
            className={`flex items-start gap-3 p-2 rounded border transition-colors duration-500 ${
              label === "Product ID" && isNewScan
                ? "bg-success/10 border-success/40"
                : "bg-secondary/50 border-border/50"
            }`}
          >
            <Icon className={`w-4 h-4 mt-0.5 shrink-0 transition-colors duration-500 ${
              label === "Product ID" && isNewScan ? "text-success" : "text-primary"
            }`} />
            <div className="min-w-0">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
              <div className={`text-sm font-mono font-semibold truncate transition-colors duration-500 ${
                label === "Product ID" && isNewScan ? "text-success" : "text-foreground"
              }`}>{value}</div>
            </div>
          </div>
        ))}

        {/* AI Damage Detection Bar */}
        <div className="pt-2 border-t border-border">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Box className="w-4 h-4 text-primary" />
              <span className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">AI Damage Analysis</span>
            </div>
            {currentProduct && (
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                currentProduct.damageScore > 15 ? "bg-destructive/20 text-destructive" : "bg-success/20 text-success"
              }`}>
                {currentProduct.damageScore > 15 ? "DEFECTIVE" : "INTACT"}
              </span>
            )}
          </div>
          
          <div className="space-y-1.5">
            <div className="flex justify-between text-[10px] font-mono">
              <span className="text-muted-foreground">Structural Integrity</span>
              <span className={currentProduct?.damageScore && currentProduct.damageScore > 15 ? "text-destructive" : "text-success"}>
                {currentProduct ? `${currentProduct.damageScore}% stress` : "0%"}
              </span>
            </div>
            <div className="h-2 w-full bg-secondary rounded-full overflow-hidden border border-border/50">
              <div 
                className={`h-full transition-all duration-500 ease-out ${
                  !currentProduct ? "w-0" : 
                  currentProduct.damageScore > 50 ? "bg-destructive" : 
                  currentProduct.damageScore > 15 ? "bg-warning" : "bg-success"
                }`}
                style={{ width: currentProduct ? `${currentProduct.damageScore}%` : '0%' }}
              />
            </div>
            <div className="text-[9px] text-muted-foreground italic leading-tight">
              {currentProduct ? 
                (currentProduct.damageScore > 15 ? "⚠ Irregular surface patterns detected. Flagged for review." : "✓ No structural deformities identified.") 
                : "Awaiting product scan..."}
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="pt-2 border-t border-border">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="w-4 h-4 text-accent" />
            <span className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Statistics</span>
          </div>
          {!connected && (
            <div className="mb-2 text-[10px] text-warning bg-warning/10 px-2 py-1 rounded border border-warning/20 text-center">
              HARDWARE OFFLINE - SHOWING CAMERA DATA
            </div>
          )}
          <div className="grid grid-cols-3 gap-1.5">
            <StatBox label="Total" value={stats.total} color="text-foreground" />
            <StatBox label="Metal" value={stats.Metal} color="text-accent" />
            <StatBox label="Plastic" value={stats.Plastic} color="text-primary" />
            <StatBox label="Organic" value={stats.Organic} color="text-warning" />
            <StatBox label="Deformed" value={stats.Deformed} color="text-destructive" />
            <StatBox label="Unknown" value={stats.Unknown} color="text-muted-foreground" />
          </div>
        </div>
      </div>
    </div>
  );
};

const StatBox = ({ label, value, color }: { label: string; value: number; color: string }) => (
  <div className="bg-muted/50 rounded p-1.5 text-center border border-border/30">
    <div className={`text-base font-mono font-bold ${color}`}>{value}</div>
    <div className="text-[8px] uppercase tracking-wider text-muted-foreground">{label}</div>
  </div>
);

export default ProductDetails;
