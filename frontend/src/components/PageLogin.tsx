import React, { useState, useEffect } from "react";
import { motion, useMotionValue, useSpring, useTransform, AnimatePresence } from "motion/react";
import { FileText, FileSpreadsheet, FileImage, FileCode, PlaySquare, ArrowRight, Github, Mail, Search, Sun, Moon, User, Lock, ArrowLeft, CheckCircle2 } from "lucide-react";
import {
  login,
  register
} from "../services/auth";

interface PageLoginProps {
  onLoginSuccess: () => void;
  theme: "light" | "dark";
  onToggleTheme: () => void;
}

// Subtly drifting floating icon definitions
interface FloatingBadge {
  id: number;
  type: "pdf" | "docx" | "pptx" | "jpg" | "png";
  x: number; // base percentage X
  y: number; // base percentage Y
  scale: number;
  color: string;
  factor: number; // parallax response factor
}

const MOCK_BADGES: FloatingBadge[] = [
  { id: 1, type: "pdf", x: 12, y: 15, scale: 1.1, color: "text-red-500 bg-red-50 border-red-200/50", factor: 25 },
  { id: 2, type: "docx", x: 80, y: 18, scale: 0.95, color: "text-blue-500 bg-blue-50 border-blue-200/50", factor: -35 },
  { id: 3, type: "pptx", x: 75, y: 70, scale: 1.05, color: "text-orange-500 bg-orange-50 border-orange-200/50", factor: 40 },
  { id: 4, type: "jpg", x: 20, y: 75, scale: 1.0, color: "text-emerald-500 bg-emerald-50 border-emerald-200/50", factor: -20 },
  { id: 5, type: "png", x: 85, y: 45, scale: 1.15, color: "text-purple-500 bg-purple-50 border-purple-200/50", factor: 30 },
  { id: 6, type: "pdf", x: 8, y: 50, scale: 0.9, color: "text-rose-500 bg-rose-50 border-rose-200/50", factor: -15 },
  { id: 7, type: "docx", x: 50, y: 10, scale: 1.05, color: "text-sky-500 bg-sky-50 border-sky-200/50", factor: 20 },
  { id: 8, type: "pptx", x: 45, y: 85, scale: 0.95, color: "text-amber-500 bg-amber-50 border-amber-200/50", factor: -25 },
];

interface FloatingBadgeItemProps {
  key?: any;
  badge: FloatingBadge;
  springX: any;
  springY: any;
  renderIcon: (type: string) => any;
  getLabel: (type: string) => string;
}

function FloatingBadgeItem({ badge, springX, springY, renderIcon, getLabel }: FloatingBadgeItemProps) {
  const x = useTransform(springX, (val: number) => val * badge.factor * 1.5);
  const y = useTransform(springY, (val: number) => val * badge.factor * 1.5);
  const offsetX = `${badge.x}%`;
  const offsetY = `${badge.y}%`;

  return (
    <motion.div
      className="absolute hidden sm:block"
      style={{
        left: offsetX,
        top: offsetY,
        x,
        y,
        scale: badge.scale,
      }}
    >
      <motion.div
        animate={{
          y: [0, -12, 0],
        }}
        transition={{
          duration: 5 + (badge.id % 3) * 1.5,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      >
        <div
          id={`floating_badge_${badge.id}`}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-xl shadow-xs border border-neutral-100/40 backdrop-blur-md cursor-default pointer-events-auto hover:shadow-md transition-shadow duration-300 ${badge.color}`}
        >
          {renderIcon(badge.type)}
          <span className="font-mono text-[10px] font-bold tracking-wider">{getLabel(badge.type)}</span>
        </div>
      </motion.div>
    </motion.div>
  );
}

export default function PageLogin({ onLoginSuccess, theme, onToggleTheme }: PageLoginProps) {
  // Springs for gravity offset cursor reaction
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 45, damping: 20 });
  const springY = useSpring(mouseY, { stiffness: 45, damping: 20 });

  // Auth View State: "options" | "sign_in" | "sign_up"
  const [authView, setAuthView] = useState<"options" | "sign_in" | "sign_up">("options");

  // Registration & Login Form State
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      // Calculate normalized offset from screen center (-0.5 to 0.5)
      const x = (e.clientX / window.innerWidth) - 0.5;
      const y = (e.clientY / window.innerHeight) - 0.5;
      mouseX.set(x);
      mouseY.set(y);
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [mouseX, mouseY]);

  // Reset errors when view changes
  useEffect(() => {
    setErrorMessage("");
    setName("");
    setEmail("");
    setPassword("");
    setSuccess(false);
  }, [authView]);

  const renderIcon = (type: string) => {
    switch (type) {
      case "pdf":
        return <FileText className="w-5 h-5 md:w-6 md:h-6" />;
      case "docx":
        return <FileSpreadsheet className="w-5 h-5 md:w-6 md:h-6" />;
      case "pptx":
        return <FileCode className="w-5 h-5 md:w-6 md:h-6" />;
      case "jpg":
      case "png":
        return <FileImage className="w-5 h-5 md:w-6 md:h-6" />;
      default:
        return <FileText className="w-5 h-5 md:w-6 md:h-6" />;
    }
  };

  const getLabel = (type: string) => {
    return type.toUpperCase();
  };

  const handleRegisterSubmit = async (
    e: React.FormEvent
  ) => {

    e.preventDefault();

    setErrorMessage("");

    if (!name.trim()) {

      setErrorMessage(
        "Please enter your full name."
      );

      return;

    }

    if (!email.trim() || !email.includes("@")) {

      setErrorMessage(
        "Please enter a valid email address."
      );

      return;

    }

    if (password.length < 6) {

      setErrorMessage(
        "Password must be at least 6 characters."
      );

      return;

    }

    try {

      setIsSubmitting(true);

      await register(
        name,
        email,
        password
      );

      setSuccess(true);

      setTimeout(() => {

        onLoginSuccess();

      }, 1000);

    } catch (error: any) {

      setErrorMessage(
        error.message
      );

    } finally {

      setIsSubmitting(false);

    }

  };

  const handleLoginSubmit = async (
    e: React.FormEvent
  ) => {

    e.preventDefault();

    setErrorMessage("");

    if (!email.trim() || !email.includes("@")) {

      setErrorMessage(
        "Please enter a valid email address."
      );

      return;
    }

    if (!password) {

      setErrorMessage(
        "Please enter your password."
      );

      return;
    }

    try {

      setIsSubmitting(true);

      await login(
        email,
        password
      );

      setSuccess(true);

      setTimeout(() => {

        onLoginSuccess();

      }, 800);

    } catch (error: any) {

      setErrorMessage(
        error.message
      );

    } finally {

      setIsSubmitting(false);

    }

  };

  return (
    <div id="login_container" className="relative w-full min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col items-center justify-center overflow-hidden px-4 select-none transition-colors duration-200">
      {/* Absolute top-right Theme Switcher */}
      <div className="absolute top-4 right-4 z-50">
        <button
          id="theme_toggle_login"
          onClick={onToggleTheme}
          className="p-2.5 rounded-xl border border-slate-200/60 dark:border-slate-800/80 bg-white/75 dark:bg-slate-900/75 backdrop-blur-md text-slate-600 dark:text-slate-350 hover:text-slate-900 dark:hover:text-white shadow-xs cursor-pointer active:scale-95 transition-all"
          title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
        >
          {theme === "dark" ? <Sun className="w-4 h-4 text-amber-500" /> : <Moon className="w-4 h-4 text-slate-600" />}
        </button>
      </div>

      {/* Google Antigravity Background Floating Widgets */}
      <div className="absolute inset-0 pointer-events-none z-0">
        {MOCK_BADGES.map((badge) => (
          <FloatingBadgeItem
            key={badge.id}
            badge={badge}
            springX={springX}
            springY={springY}
            renderIcon={renderIcon}
            getLabel={getLabel}
          />
        ))}
      </div>

      {/* Hero Central Block */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="relative z-10 w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-xl shadow-slate-100/80 dark:shadow-slate-950/40 border border-slate-100 dark:border-slate-800 p-8 md:p-10 text-center transition-all duration-200"
      >
        {/* Minimal Symbol */}
        <div className="flex justify-center mb-5">
          <div className="relative w-14 h-14 flex items-center justify-center select-none">
            {/* Outer glowing aura */}
            <div className="absolute inset-1 bg-blue-500/10 rounded-[18px] blur-md" />

            {/* Gradient container */}
            <div className="absolute inset-0 bg-gradient-to-tr from-blue-600 to-indigo-500 rounded-[16px] border border-white/10 flex items-center justify-center shadow-md shadow-blue-500/10">
              <div className="w-full h-full rounded-[14px] border border-white/5 flex items-center justify-center relative overflow-hidden">
                <div className="absolute w-8 h-8 rounded-full border border-dashed border-white/15 opacity-60" />
                <div className="relative w-6.5 h-6.5 bg-white/10 border border-white/15 rounded-lg flex items-center justify-center">
                  <Search className="w-3.5 h-3.5 text-white" />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Brand Name */}
        <h1 id="brand_title" className="font-display text-4xl font-bold text-slate-800 dark:text-white tracking-tight mb-6 transition-colors duration-200">
          CogniSeek
        </h1>

        <AnimatePresence mode="wait">
          {authView === "options" && (
            <motion.div
              key="options_view"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="space-y-3.5"
            >

              <button
                id="btn_email_sign_in"
                onClick={() => setAuthView("sign_in")}
                className="w-full py-3 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-755 text-slate-800 dark:text-slate-200 rounded-xl text-sm font-semibold transition-all duration-200 border border-slate-200/55 dark:border-slate-750 cursor-pointer active:scale-98"
              >
                Sign In with Email
              </button>

              <div className="pt-4 border-t border-slate-100 dark:border-slate-850 mt-4">
                <p className="text-xs text-slate-450 dark:text-slate-500">
                  Don't have an account?&nbsp;
                  <button onClick={() => setAuthView("sign_up")} className="text-blue-600 dark:text-blue-550 hover:text-blue-750 dark:hover:text-blue-400 hover:underline font-semibold cursor-pointer transition-colors">
                    Create Account
                  </button>
                </p>
              </div>
            </motion.div>
          )}

          {authView === "sign_in" && (
            <motion.div
              key="sign_in_view"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="text-left"
            >
              <div className="flex items-center gap-2 mb-4">
                <button
                  onClick={() => setAuthView("options")}
                  className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400"
                >
                  <ArrowLeft className="w-4 h-4" />
                </button>
                <h2 className="text-lg font-bold text-slate-800 dark:text-white">Sign In</h2>
              </div>

              {success ? (
                <div className="flex flex-col items-center justify-center py-6 text-center">
                  <motion.div
                    initial={{ scale: 0.5, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="w-12 h-12 rounded-full bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-emerald-650 dark:text-emerald-400 mb-3"
                  >
                    <CheckCircle2 className="w-6 h-6 fill-emerald-100 dark:fill-emerald-950/20" />
                  </motion.div>
                  <p className="text-sm font-semibold text-slate-850 dark:text-white">Successfully Authenticated</p>
                  <p className="text-xs text-slate-400 mt-1">Connecting index portals...</p>
                </div>
              ) : (
                <form onSubmit={handleLoginSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold font-mono text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-1.5">Email Address</label>
                    <div className="relative">
                      <Mail className="absolute left-3.5 top-3 w-4 h-4 text-slate-400" />
                      <input
                        type="email"
                        placeholder="you@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl py-2.5 pl-10 pr-4 text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold font-mono text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-1.5">Password</label>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-3 w-4 h-4 text-slate-400" />
                      <input
                        type="password"
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl py-2.5 pl-10 pr-4 text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    </div>
                  </div>

                  {errorMessage && (
                    <div className="p-3 bg-red-50 dark:bg-red-950/20 border border-red-150 dark:border-red-900/40 text-red-650 dark:text-red-400 text-xs rounded-lg">
                      {errorMessage}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl text-sm transition-all duration-200 cursor-pointer shadow-xs active:scale-98 flex items-center justify-center gap-2"
                  >
                    {isSubmitting ? "Authenticating..." : "Sign In"}
                  </button>

                  <p className="text-center text-xs text-slate-400 dark:text-slate-500 pt-2">
                    Don't have an account?&nbsp;
                    <button type="button" onClick={() => setAuthView("sign_up")} className="text-blue-600 dark:text-blue-500 font-semibold hover:underline">
                      Create Account
                    </button>
                  </p>
                </form>
              )}
            </motion.div>
          )}

          {authView === "sign_up" && (
            <motion.div
              key="sign_up_view"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="text-left"
            >
              <div className="flex items-center gap-2 mb-4">
                <button
                  onClick={() => setAuthView("options")}
                  className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400"
                >
                  <ArrowLeft className="w-4 h-4" />
                </button>
                <h2 className="text-lg font-bold text-slate-800 dark:text-white">Create Account</h2>
              </div>

              {success ? (
                <div className="flex flex-col items-center justify-center py-6 text-center">
                  <motion.div
                    initial={{ scale: 0.5, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="w-12 h-12 rounded-full bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-emerald-650 dark:text-emerald-400 mb-3"
                  >
                    <CheckCircle2 className="w-6 h-6 fill-emerald-100 dark:fill-emerald-950/20" />
                  </motion.div>
                  <p className="text-sm font-semibold text-slate-850 dark:text-white">Account Created Successfully!</p>
                  <p className="text-xs text-slate-400 mt-1">Welcome {name}! Directing you to integrations setup...</p>
                </div>
              ) : (
                <form onSubmit={handleRegisterSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold font-mono text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-1.5">Full Name</label>
                    <div className="relative">
                      <User className="absolute left-3.5 top-3 w-4 h-4 text-slate-400" />
                      <input
                        type="text"
                        placeholder="John Doe"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="w-full text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl py-2.5 pl-10 pr-4 text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold font-mono text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-1.5">Email Address</label>
                    <div className="relative">
                      <Mail className="absolute left-3.5 top-3 w-4 h-4 text-slate-400" />
                      <input
                        type="email"
                        placeholder="you@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl py-2.5 pl-10 pr-4 text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold font-mono text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-1.5">Password</label>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-3 w-4 h-4 text-slate-400" />
                      <input
                        type="password"
                        placeholder="At least 6 characters"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl py-2.5 pl-10 pr-4 text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    </div>
                  </div>

                  {errorMessage && (
                    <div className="p-3 bg-red-50 dark:bg-red-950/20 border border-red-150 dark:border-red-900/40 text-red-650 dark:text-red-400 text-xs rounded-lg">
                      {errorMessage}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl text-sm transition-all duration-200 cursor-pointer shadow-xs active:scale-98 flex items-center justify-center gap-2"
                  >
                    {isSubmitting ? "Creating account..." : "Create Account"}
                  </button>

                  <p className="text-center text-xs text-slate-400 dark:text-slate-500 pt-2">
                    Already have an account?&nbsp;
                    <button type="button" onClick={() => setAuthView("sign_in")} className="text-blue-600 dark:text-blue-500 font-semibold hover:underline">
                      Sign In
                    </button>
                  </p>
                </form>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Bottom Legal Credit */}
      <div className="absolute bottom-6 text-center text-[11px] text-slate-400 dark:text-slate-500 tracking-wide">
        CogniSeek © 2026. Premium Enterprise Unified Search indexer.
      </div>
    </div>
  );
}