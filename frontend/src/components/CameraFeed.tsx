import { Camera } from "lucide-react";
import { useState, useRef } from "react";

const MJPEG_URL = "http://localhost:8000/api/video_feed";

const CameraFeed = () => {
  const [live, setLive] = useState(false);
  const [error, setError] = useState(false);
  const retryCountRef = useRef(0);

  const handleError = () => {
    setLive(false);
    setError(true);
    // Auto-retry up to 5 times with increasing delay
    if (retryCountRef.current < 5) {
      const delay = 2000 * (retryCountRef.current + 1);
      retryCountRef.current += 1;
      setTimeout(() => setError(false), delay);
    }
  };

  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-header">
        <span>Live Camera Feed</span>
        {live && (
          <div className="flex items-center gap-1.5 text-xs text-success font-mono">
            <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
            LIVE
          </div>
        )}
      </div>

      <div className="flex-1 relative bg-muted/30 min-h-[200px] overflow-hidden rounded-b">
        {/* MJPEG stream — always mounted so the browser keeps the connection open */}
        {!error && (
          <img
            key={retryCountRef.current} // re-mounts on retry
            src={`${MJPEG_URL}?t=${retryCountRef.current}`}
            className="absolute inset-2 w-[calc(100%-1rem)] h-[calc(100%-1rem)] object-contain rounded"
            alt="Live USB Camera Feed"
            onLoad={() => { setLive(true); setError(false); }}
            onError={handleError}
          />
        )}

        {/* Overlay: shown until first frame arrives */}
        {!live && (
          <div className="absolute inset-0 flex items-center justify-center bg-muted/30 z-10">
            <div className="text-center">
              {error ? (
                <>
                  <Camera className="w-12 h-12 text-destructive/40 mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground font-mono">CAMERA ERROR</p>
                  <p className="text-xs text-muted-foreground/60 mt-1">Retrying...</p>
                </>
              ) : (
                <>
                  <Camera className="w-12 h-12 text-muted-foreground/30 mx-auto mb-2 animate-pulse" />
                  <p className="text-sm text-muted-foreground font-mono">WAITING FOR FEED...</p>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CameraFeed;
