"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { useEffect } from "react";

export default function LandingPage() {
  useEffect(() => {
    const body = document.body;
    body.dataset.page = "landing";

    const apply = () => {
      const isMobile = window.innerWidth <= 640;
      const img = isMobile
        ? "/assets/main_mobile.png"
        : "/assets/main_desktop.png";

      body.style.backgroundImage = `
        linear-gradient(
          180deg,
          rgba(23,23,23,0.45) 0%,
          rgba(23,23,23,0.20) 30%,
          rgba(23,23,23,0.80) 100%
        ),
        url("${img}")
      `;
      body.style.backgroundSize = "cover";
      body.style.backgroundPosition = "center";
      body.style.backgroundRepeat = "no-repeat";
      body.style.backgroundAttachment = "fixed";
    };

    apply();
    window.addEventListener("resize", apply);

    return () => {
      window.removeEventListener("resize", apply);
      delete body.dataset.page;
      body.style.backgroundImage = "";
      body.style.backgroundSize = "";
      body.style.backgroundPosition = "";
      body.style.backgroundRepeat = "";
      body.style.backgroundAttachment = "";
    };
  }, []);

  return (
    <div
      style={{
        position: "relative",
        zIndex: 1,
        minHeight: "100dvh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        paddingTop: "clamp(48px, 10vh, 140px)",
        paddingBottom: "clamp(100px, 14vh, 160px)",
        paddingLeft: "clamp(20px, 5vw, 60px)",
        paddingRight: "clamp(20px, 5vw, 60px)",
        gap: 40,
      }}
    >
      <motion.h1
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        style={{
          margin: 0,
          textAlign: "center",
          fontFamily: "'Inter', sans-serif",
          fontSize: "clamp(30px, 7vw, 64px)",
          fontWeight: 700,
          lineHeight: 1.15,
          letterSpacing: "-0.02em",
        }}
      >
        <span style={{ color: "#EB0000" }}>A</span>
        <span style={{ color: "#E5E5E5" }}>BSOLUTE </span>
        <span style={{ color: "#EB0000" }}>C</span>
        <span style={{ color: "#E5E5E5" }}>INEMA</span>
        <br />
        <span style={{ filter: "blur(2px)", display: "inline-block" }}>
          <span style={{ color: "#EB0000" }}>D</span>
          <span style={{ color: "#E5E5E5" }}>UEL</span>
        </span>
      </motion.h1>
      <div style={{ flex: 1 }} />

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        style={{
          width: "min(100%, 332px)",
          display: "flex",
          flexDirection: "column",
          gap: 15,
        }}
      >
        <Link href="/auth/login" style={{ width: "100%" }}>
          <motion.button
            whileHover={{ scale: 1.02, boxShadow: "0px 12px 48px rgba(232,35,35,0.35)" }}
            whileTap={{ scale: 0.97 }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            style={{
              width: "100%",
              height: 60,
              background: "#E82323",
              color: "#fff",
              fontSize: 19,
              fontWeight: 800,
              fontFamily: "'SF Pro', 'Inter', sans-serif",
              borderRadius: 16,
              border: "none",
              cursor: "pointer",
              boxShadow: "0px 8px 40px rgba(0, 0, 0, 0.12)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            Войти
          </motion.button>
        </Link>

        <Link href="/join" style={{ width: "100%" }}>
          <motion.button
            whileHover={{ scale: 1.02, boxShadow: "0px 12px 48px rgba(0,0,0,0.25)" }}
            whileTap={{ scale: 0.97 }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            style={{
              width: "100%",
              height: 60,
              background: "#fff",
              color: "#1A1A1A",
              fontSize: 19,
              fontWeight: 800,
              fontFamily: "'SF Pro', 'Inter', sans-serif",
              borderRadius: 16,
              border: "none",
              cursor: "pointer",
              boxShadow: "0px 8px 40px rgba(0, 0, 0, 0.12)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            Присоединиться к комнате
          </motion.button>
        </Link>
      </motion.div>
    </div>
  );
}
