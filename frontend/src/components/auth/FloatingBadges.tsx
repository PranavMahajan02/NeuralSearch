import { useEffect } from "react";
import { motion, useMotionValue, useSpring, useTransform, type MotionValue } from "motion/react";
import { FileCode, FileImage, FileSpreadsheet, FileText } from "lucide-react";

// Purely decorative file-type chips drifting behind the login card (aria-hidden).
interface Badge {
  id: number;
  type: "pdf" | "docx" | "pptx" | "jpg" | "png";
  x: number;
  y: number;
  scale: number;
  color: string;
  factor: number;
}

const BADGES: Badge[] = [
  {
    id: 1,
    type: "pdf",
    x: 12,
    y: 15,
    scale: 1.1,
    color: "text-red-700 bg-red-50 border-red-200/50",
    factor: 25,
  },
  {
    id: 2,
    type: "docx",
    x: 80,
    y: 18,
    scale: 0.95,
    color: "text-blue-700 bg-blue-50 border-blue-200/50",
    factor: -35,
  },
  {
    id: 3,
    type: "pptx",
    x: 75,
    y: 70,
    scale: 1.05,
    color: "text-orange-700 bg-orange-50 border-orange-200/50",
    factor: 40,
  },
  {
    id: 4,
    type: "jpg",
    x: 20,
    y: 75,
    scale: 1.0,
    color: "text-emerald-700 bg-emerald-50 border-emerald-200/50",
    factor: -20,
  },
  {
    id: 5,
    type: "png",
    x: 85,
    y: 45,
    scale: 1.15,
    color: "text-purple-700 bg-purple-50 border-purple-200/50",
    factor: 30,
  },
  {
    id: 6,
    type: "pdf",
    x: 8,
    y: 50,
    scale: 0.9,
    color: "text-rose-700 bg-rose-50 border-rose-200/50",
    factor: -15,
  },
  {
    id: 7,
    type: "docx",
    x: 50,
    y: 10,
    scale: 1.05,
    color: "text-sky-700 bg-sky-50 border-sky-200/50",
    factor: 20,
  },
  {
    id: 8,
    type: "pptx",
    x: 45,
    y: 85,
    scale: 0.95,
    color: "text-amber-700 bg-amber-50 border-amber-200/50",
    factor: -25,
  },
];

const ICON = { pdf: FileText, docx: FileSpreadsheet, pptx: FileCode, jpg: FileImage, png: FileImage };

function FloatingBadge({
  badge,
  springX,
  springY,
}: {
  badge: Badge;
  springX: MotionValue<number>;
  springY: MotionValue<number>;
}) {
  const x = useTransform(springX, (v) => v * badge.factor * 1.5);
  const y = useTransform(springY, (v) => v * badge.factor * 1.5);
  const Icon = ICON[badge.type];

  return (
    <motion.div
      className="absolute hidden sm:block"
      style={{ left: `${badge.x}%`, top: `${badge.y}%`, x, y, scale: badge.scale }}
    >
      <motion.div
        animate={{ y: [0, -12, 0] }}
        transition={{ duration: 5 + (badge.id % 3) * 1.5, repeat: Infinity, ease: "easeInOut" }}
      >
        <div
          className={`flex items-center gap-1.5 rounded-xl border border-neutral-100/40 px-3 py-2 shadow-xs backdrop-blur-md ${badge.color}`}
        >
          <Icon className="h-5 w-5 md:h-6 md:w-6" />
          <span className="font-mono text-[10px] font-bold tracking-wider">{badge.type.toUpperCase()}</span>
        </div>
      </motion.div>
    </motion.div>
  );
}

export function FloatingBadges() {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 45, damping: 20 });
  const springY = useSpring(mouseY, { stiffness: 45, damping: 20 });

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      mouseX.set(e.clientX / window.innerWidth - 0.5);
      mouseY.set(e.clientY / window.innerHeight - 0.5);
    };
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, [mouseX, mouseY]);

  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 z-0">
      {BADGES.map((badge) => (
        <FloatingBadge key={badge.id} badge={badge} springX={springX} springY={springY} />
      ))}
    </div>
  );
}
