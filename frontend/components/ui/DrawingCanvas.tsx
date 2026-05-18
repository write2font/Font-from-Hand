"use client";

import { useRef, forwardRef, useImperativeHandle } from "react";
import { ReactSketchCanvas, ReactSketchCanvasRef, CanvasPath } from "react-sketch-canvas";
import { Undo2, Trash2 } from "lucide-react";

interface DrawingCanvasProps {
  strokeWidth?: number;
}

export interface DrawingCanvasHandle {
  exportImage: () => Promise<string>;
  exportPaths: () => Promise<CanvasPath[]>;
  loadPaths: (paths: CanvasPath[]) => void;
  clearCanvas: () => void;
}

const DrawingCanvas = forwardRef<DrawingCanvasHandle, DrawingCanvasProps>(
  ({ strokeWidth = 4 }, ref) => {
    const canvasRef = useRef<ReactSketchCanvasRef>(null);

    useImperativeHandle(ref, () => ({
      exportImage: async () => {
        const data = await canvasRef.current?.exportImage("png");
        return data ?? "";
      },
      exportPaths: async () => {
        const paths = await canvasRef.current?.exportPaths();
        return paths ?? [];
      },
      loadPaths: (paths: CanvasPath[]) => {
        canvasRef.current?.loadPaths(paths);
      },
      clearCanvas: () => canvasRef.current?.clearCanvas(),
    }));

    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => canvasRef.current?.undo()}
            className="flex items-center gap-1.5 px-4 py-2 bg-gray-100 text-gray-600 hover:bg-gray-200 rounded-xl text-sm font-medium transition"
          >
            <Undo2 size={16} />
            되돌리기
          </button>
          <button
            onClick={() => canvasRef.current?.clearCanvas()}
            className="flex items-center gap-1.5 px-4 py-2 bg-gray-100 text-gray-600 hover:bg-gray-200 rounded-xl text-sm font-medium transition"
          >
            <Trash2 size={16} />
            전체 지우기
          </button>
        </div>

        <div className="border-2 border-gray-200 rounded-2xl overflow-hidden">
          <ReactSketchCanvas
            ref={canvasRef}
            width="100%"
            height="500px"
            strokeWidth={strokeWidth}
            strokeColor="#1a1a1a"
            canvasColor="#ffffff"
            style={{ borderRadius: 0 }}
          />
        </div>
        <p className="text-xs text-gray-400 text-center">
          마우스 또는 태블릿 펜으로 자유롭게 작성하세요
        </p>
      </div>
    );
  }
);

DrawingCanvas.displayName = "DrawingCanvas";
export default DrawingCanvas;
