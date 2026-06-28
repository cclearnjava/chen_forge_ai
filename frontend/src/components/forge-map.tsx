"use client";

import { useEffect, useRef } from "react";

export default function ForgeMap() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const points = Array.from({ length: 26 }, (_, index) => ({
      angle: (Math.PI * 2 * index) / 26,
      radius: 120 + (index % 5) * 34,
      speed: 0.00055 + (index % 7) * 0.00008,
      size: 2 + (index % 3),
    }));

    let animationId: number;

    function resize() {
      if (!canvas) return;
      canvas.width = canvas.offsetWidth * window.devicePixelRatio;
      canvas.height = canvas.offsetHeight * window.devicePixelRatio;
      ctx!.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
    }

    function draw(time: number) {
      if (!canvas) return;
      const width = canvas.offsetWidth;
      const height = canvas.offsetHeight;
      const centerX = width * 0.63;
      const centerY = height * 0.42;
      ctx!.clearRect(0, 0, width, height);

      ctx!.strokeStyle = "rgba(49, 92, 111, 0.13)";
      ctx!.lineWidth = 1;
      for (let i = 0; i < 9; i += 1) {
        ctx!.beginPath();
        ctx!.rect(centerX - 170 - i * 26, centerY - 118 - i * 16, 340 + i * 52, 236 + i * 32);
        ctx!.stroke();
      }

      const rendered = points.map((point) => {
        const angle = point.angle + time * point.speed;
        return {
          x: centerX + Math.cos(angle) * point.radius,
          y: centerY + Math.sin(angle * 1.3) * point.radius * 0.56,
          size: point.size,
        };
      });

      ctx!.strokeStyle = "rgba(184, 95, 54, 0.18)";
      rendered.forEach((point, index) => {
        for (let j = index + 1; j < rendered.length; j += 1) {
          const other = rendered[j];
          const distance = Math.hypot(point.x - other.x, point.y - other.y);
          if (distance < 145) {
            ctx!.beginPath();
            ctx!.moveTo(point.x, point.y);
            ctx!.lineTo(other.x, other.y);
            ctx!.stroke();
          }
        }
      });

      rendered.forEach((point, index) => {
        ctx!.fillStyle = index % 4 === 0 ? "rgba(184, 95, 54, 0.74)" : "rgba(37, 35, 30, 0.58)";
        ctx!.beginPath();
        ctx!.fillRect(point.x - point.size, point.y - point.size, point.size * 2, point.size * 2);
        ctx!.fill();
      });

      animationId = requestAnimationFrame(draw);
    }

    resize();
    window.addEventListener("resize", resize);
    animationId = requestAnimationFrame(draw);

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(animationId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="forge-map"
      aria-label="Animated ChenForge agent operating map"
    />
  );
}
