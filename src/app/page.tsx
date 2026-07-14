"use client";

import { motion } from "framer-motion";
import { useSession, signOut } from "next-auth/react";
import { useRouter } from "next/navigation";
import { ArrowRight, Activity, Cpu, ShieldCheck, Target } from "lucide-react";

export default function Home() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const handleSignOut = async () => {
    await signOut({ redirect: false });
    router.refresh();
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", position: "relative", overflow: "hidden" }}>
      {/* Dynamic Grid Background */}
      <div style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", backgroundImage: "radial-gradient(var(--border) 1px, transparent 1px)", backgroundSize: "40px 40px", opacity: 0.3, zIndex: 0 }} />

      {/* Nav */}
      <nav style={{ position: "fixed", top: 0, width: "100%", zIndex: 50, padding: "1.5rem 2rem", borderBottom: "1px solid var(--border)", background: "rgba(0, 0, 0, 0.4)", backdropFilter: "blur(12px)" }}>
        <div style={{ maxWidth: "1200px", margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Activity className="gradient-text" style={{ background: "linear-gradient(135deg, var(--secondary), var(--primary))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }} size={28} />
            <span style={{ letterSpacing: "-0.05em" }}>喜畔健康 <span style={{ color: "var(--primary)", fontSize: "1rem", fontWeight: 500 }}>AI</span></span>
          </div>

          <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
            {status === "loading" ? (
              <div style={{ width: "100px", height: "30px", background: "var(--border)", borderRadius: "var(--radius)", animation: "pulse 2s infinite" }} />
            ) : session ? (
              <>
                <span style={{ color: "var(--text-dim)", fontSize: "0.95rem" }}>欢迎, {session.user?.name}</span>
                <button
                  onClick={handleSignOut}
                  style={{ padding: "0.6rem 1.2rem", borderRadius: "var(--radius)", fontSize: "0.9rem", color: "var(--text)", border: "1px solid var(--border)", background: "rgba(255, 255, 255, 0.05)", transition: "all 0.2s" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255, 255, 255, 0.1)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)")}
                >
                  退出登录
                </button>
                <button
                  onClick={() => router.push("/dashboard")}
                  className="glow"
                  style={{ padding: "0.6rem 1.5rem", borderRadius: "var(--radius)", fontSize: "0.9rem", color: "white", background: "var(--primary)", fontWeight: 600, display: "flex", alignItems: "center", gap: "0.5rem" }}
                >
                  工作台 <ArrowRight size={16} />
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => router.push("/complaints")}
                  style={{ color: "var(--text-dim)", fontSize: "0.95rem", fontWeight: 500, marginRight: "1.5rem" }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text)")}
                  onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-dim)")}
                >
                  投诉管理
                </button>
                <button
                  onClick={() => router.push("/strategy")}
                  style={{ color: "var(--text-dim)", fontSize: "0.95rem", fontWeight: 500, marginRight: "0.5rem" }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text)")}
                  onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-dim)")}
                >
                  战略规划
                </button>
                <button
                  onClick={() => router.push("/login")}
                  style={{ padding: "0.6rem 1.2rem", color: "var(--text-dim)", fontSize: "0.95rem", fontWeight: 500 }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text)")}
                  onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-dim)")}
                >
                  登录
                </button>
                <button
                  onClick={() => router.push("/register")}
                  className="glow"
                  style={{ padding: "0.6rem 1.5rem", borderRadius: "100px", fontSize: "0.95rem", color: "white", background: "linear-gradient(135deg, var(--primary), var(--accent))", fontWeight: 600 }}
                >
                  开始体验
                </button>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <main style={{ position: "relative", zIndex: 10, paddingTop: "12rem", paddingBottom: "6rem", maxWidth: "1200px", margin: "0 auto", paddingLeft: "2rem", paddingRight: "2rem" }}>

        {/* Glow Spheres */}
        <div style={{ position: "absolute", top: "15%", left: "50%", transform: "translate(-50%, 0)", width: "60vw", height: "60vw", borderRadius: "50%", background: "radial-gradient(circle, rgba(10, 132, 255, 0.15) 0%, transparent 70%)", filter: "blur(60px)", zIndex: -1 }} />

        <div style={{ textAlign: "center", maxWidth: "800px", margin: "0 auto" }}>
          <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.8, ease: "easeOut" }}>
            <div style={{ display: "inline-block", padding: "0.5rem 1rem", background: "rgba(10, 132, 255, 0.1)", color: "var(--primary)", borderRadius: "100px", fontSize: "0.9rem", fontWeight: 600, marginBottom: "2rem", border: "1px solid rgba(10, 132, 255, 0.2)" }}>
              Introducing 喜畔健康 AI v2.0
            </div>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1, ease: "easeOut" }}
            style={{ fontSize: "clamp(3rem, 6vw, 5rem)", fontWeight: 800, lineHeight: 1.1, marginBottom: "1.5rem", letterSpacing: "-0.04em" }}
          >
            以<span className="gradient-text">数据</span>对话身体，用<span style={{ color: "var(--secondary)" }}>智能</span>定义健康。
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
            style={{ fontSize: "1.25rem", color: "var(--text-dim)", marginBottom: "3rem", lineHeight: 1.6, padding: "0 1rem" }}
          >
            喜畔健康依托顶尖的 AI 预测模型与医学知识图谱，通过持续动态监测，为您量身定制疾病预防、营养摄入与生活方式的综合健康解决方案。
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3, ease: "easeOut" }}
            style={{ display: "flex", gap: "1rem", justifyContent: "center" }}
          >
            <button
              onClick={() => router.push(session ? "/dashboard" : "/register")}
              className="glow"
              style={{ padding: "1.1rem 2.5rem", borderRadius: "100px", fontSize: "1.1rem", color: "black", background: "white", fontWeight: 600, display: "flex", alignItems: "center", gap: "0.5rem" }}
            >
              {session ? "进入健康看板" : "建立健康档案"} <ArrowRight size={20} />
            </button>
            <button
              onClick={() => router.push("/strategy")}
              style={{ padding: "1.1rem 2.5rem", borderRadius: "100px", fontSize: "1.1rem", color: "white", border: "1px solid var(--border)", background: "rgba(255, 255, 255, 0.05)", fontWeight: 600, display: "flex", alignItems: "center", gap: "0.5rem" }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255, 255, 255, 0.1)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)")}
            >
              战略蓝图 <Target size={20} color="var(--primary)" />
            </button>
          </motion.div>
        </div>

        {/* Feature Cards Grid */}
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.5, ease: "easeOut" }}
          style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "2rem", marginTop: "8rem" }}
        >
          <div className="glass" style={{ padding: "2.5rem", borderRadius: "var(--radius-lg)", borderTop: "1px solid rgba(255,255,255,0.2)" }}>
            <div style={{ width: "50px", height: "50px", borderRadius: "12px", background: "linear-gradient(135deg, var(--primary), var(--accent))", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "1.5rem" }}>
              <Cpu color="white" size={24} />
            </div>
            <h3 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem" }}>全维度 AI 分析</h3>
            <p style={{ color: "var(--text-dim)", lineHeight: 1.6 }}>集成百万级精准医学病理数据，实时分析体征变化，提前预知亚健康隐患，拒绝粗放型健康管理。</p>
          </div>

          <div className="glass" style={{ padding: "2.5rem", borderRadius: "var(--radius-lg)", borderTop: "1px solid rgba(255,255,255,0.2)" }}>
            <div style={{ width: "50px", height: "50px", borderRadius: "12px", background: "linear-gradient(135deg, var(--secondary), #0fa43a)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "1.5rem" }}>
              <Activity color="white" size={24} />
            </div>
            <h3 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem" }}>个性化持续演进</h3>
            <p style={{ color: "var(--text-dim)", lineHeight: 1.6 }}>基于用户长期的睡眠、心率、饮食与作息反馈，健康模型将每日自我迭代，生成最契合体质的干预建议。</p>
          </div>

          <div className="glass" style={{ padding: "2.5rem", borderRadius: "var(--radius-lg)", borderTop: "1px solid rgba(255,255,255,0.2)" }}>
            <div style={{ width: "50px", height: "50px", borderRadius: "12px", background: "linear-gradient(135deg, #ff9f0a, #ff3b30)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "1.5rem" }}>
              <ShieldCheck color="white" size={24} />
            </div>
            <h3 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem" }}>权威级数字隐私</h3>
            <p style={{ color: "var(--text-dim)", lineHeight: 1.6 }}>严格遵照医疗数据安全级别加密，每一次生物信息交换均在去中心化的隐匿网络中完成。</p>
          </div>
        </motion.div>
      </main>
    </div>
  );
}
