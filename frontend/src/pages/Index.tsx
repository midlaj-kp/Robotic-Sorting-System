import { SystemProvider } from "@/context/SystemContext";
import TopNavBar from "@/components/TopNavBar";
import ConveyorSimulation from "@/components/ConveyorSimulation";
import CameraFeed from "@/components/CameraFeed";
import ProductDetails from "@/components/ProductDetails";
import LogPanel from "@/components/LogPanel";
import ControlPanel from "@/components/ControlPanel";

const Index = () => {
  return (
    <SystemProvider>
      <div className="h-screen flex flex-col bg-background p-2 gap-2 overflow-hidden">
        {/* Top Nav */}
        <TopNavBar />

        {/* Main Conveyor Panel */}
        <div className="flex-[1.2] min-h-0">
          <ConveyorSimulation />
        </div>

        {/* Sub Panels: Camera + Product Details */}
        <div className="flex-1 grid grid-cols-[1fr_1fr] gap-2 min-h-0">
          <CameraFeed />
          <ProductDetails />
        </div>

        {/* Bottom */}
        <div className="flex gap-2 items-stretch">
          <div className="flex-1">
            <LogPanel />
          </div>
          <div className="flex items-center">
            <ControlPanel />
          </div>
        </div>
      </div>
    </SystemProvider>
  );
};

export default Index;
