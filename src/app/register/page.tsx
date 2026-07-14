"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2, Target, Shield, Zap } from "lucide-react";

export default function Register() {
    const router = useRouter();
    const [data, setData] = useState({ name: "", email: "", password: "" });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const registerUser = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");

        try {
            const response = await fetch("/api/register", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorMsg = await response.text();
                throw new Error(errorMsg);
            }

            router.push("/login");
        } catch (err: any) {
            setError(err.message || "Something went wrong.");
            setLoading(false);
        }
    };

    const FeatureItem = ({ icon: Icon, title, desc }: any) => (
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }} style={{ display: "flex", gap: "1rem", alignItems: "flex-start", marginBottom: "1.5rem" }}>
            <div style={{ padding: "0.8rem", background: "rgba(94, 92, 230, 0.15)", borderRadius: "var(--radius)", color: "var(--accent)" }}>
                <Icon size={24} />
            </div>
            <div>
                <h3 style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--text)", marginBottom: "0.2rem" }}>{title}</h3>
                <p style={{ color: "var(--text-dim)", fontSize: "0.95rem", lineHeight: 1.5 }}>{desc}</p>
            </div>
        </motion.div>
    );

    return (
        <div
            style={{
                minHeight: "100vh",
                display: "flex",
                alignItems: "stretch",
                background: "var(--bg)",
                position: "relative",
            }}
        >
            {/* Left Marketing Side (Hidden on mobile by default context, but we use inline for simplicity) */}
            <div
                className="glass"
                style={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "center",
                    padding: "5rem",
                    background: "radial-gradient(circle at 50% 50%, rgba(94, 92, 230, 0.1) 0%, rgba(0, 0, 0, 1) 100%)",
                    borderRight: "1px solid var(--border)",
                }}
            >
                <div style={{ maxWidth: "480px", margin: "0 auto" }}>
                    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                        <h1 className="gradient-text" style={{ fontSize: "3.5rem", fontWeight: 800, lineHeight: 1.1, marginBottom: "1.5rem", letterSpacing: "-0.03em" }}>解锁 AI 健康未来</h1>
                        <p style={{ fontSize: "1.2rem", color: "var(--text-dim)", marginBottom: "3rem", lineHeight: 1.6 }}>开启精准医疗与个性化调理的新纪元。加入喜畔健康，全方位为您和家人的健康保驾护航。</p>
                    </motion.div>

                    <FeatureItem icon={Target} title="个性化 AI 方案" desc="分析您的生活习惯与体征数据，生成定制营养及运动方案。" />
                    <FeatureItem icon={Zap} title="实时数据追踪" desc="设备互联，秒级响应，将潜在健康隐患扼杀于萌芽阶段。" />
                    <FeatureItem icon={Shield} title="金融级数据安全" desc="隐私数据多重加密，符合全行业最高标准体系。" />
                </div>
            </div>

            {/* Right Form Side */}
            <div
                style={{
                    flex: 1,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "3rem",
                    position: "relative",
                    overflow: "hidden"
                }}
            >
                <div style={{ position: "absolute", top: "10%", right: "-10%", width: "40vw", height: "40vw", background: "radial-gradient(circle, rgba(10, 132, 255, 0.2) 0%, transparent 60%)", filter: "blur(100px)", zIndex: 0 }} />

                <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.6 }}
                    className="glass"
                    style={{
                        width: "100%",
                        maxWidth: "460px",
                        padding: "3rem",
                        borderRadius: "var(--radius-lg)",
                        zIndex: 10,
                        display: "flex",
                        flexDirection: "column",
                        gap: "2rem",
                        boxShadow: "0 20px 40px rgba(0,0,0,0.6)"
                    }}
                >
                    <button
                        onClick={() => router.push("/")}
                        style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--text-dim)", alignSelf: "flex-start", fontSize: "0.9rem" }}
                    >
                        <ArrowLeft size={16} /> 返回首页
                    </button>

                    <div style={{ textAlign: "center" }}>
                        <h2 style={{ fontSize: "2.2rem", fontWeight: 700, marginBottom: "0.5rem", color: "white" }}>创建账户</h2>
                        <p style={{ color: "var(--text-dim)", fontSize: "1rem" }}>开启您的专属数字健康档案</p>
                    </div>

                    {error && (
                        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} style={{ padding: "1rem", background: "rgba(255, 59, 48, 0.1)", border: "1px solid rgba(255, 59, 48, 0.3)", borderRadius: "var(--radius)", color: "#ff453a", fontSize: "0.9rem", textAlign: "center" }}>
                            {error}
                        </motion.div>
                    )}

                    <form onSubmit={registerUser} style={{ display: "flex", flexDirection: "column", gap: "1.2rem" }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                            <label style={{ fontSize: "0.9rem", color: "var(--text-dim)", fontWeight: 500 }}>姓名 / 称呼</label>
                            <input
                                type="text"
                                required
                                value={data.name}
                                onChange={(e) => setData({ ...data, name: e.target.value })}
                                placeholder="王小明"
                                style={{
                                    width: "100%", padding: "1rem 1.2rem", background: "rgba(0, 0, 0, 0.2)", border: "1px solid var(--border)", borderRadius: "var(--radius)", color: "var(--text)", fontSize: "1rem", transition: "all 0.2s"
                                }}
                                onFocus={(e) => (e.target.style.borderColor = "var(--primary)")}
                                onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
                            />
                        </div>

                        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                            <label style={{ fontSize: "0.9rem", color: "var(--text-dim)", fontWeight: 500 }}>电子邮箱</label>
                            <input
                                type="email"
                                required
                                value={data.email}
                                onChange={(e) => setData({ ...data, email: e.target.value })}
                                placeholder="hello@example.com"
                                style={{
                                    width: "100%", padding: "1rem 1.2rem", background: "rgba(0, 0, 0, 0.2)", border: "1px solid var(--border)", borderRadius: "var(--radius)", color: "var(--text)", fontSize: "1rem", transition: "all 0.2s"
                                }}
                                onFocus={(e) => (e.target.style.borderColor = "var(--primary)")}
                                onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
                            />
                        </div>

                        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                            <label style={{ fontSize: "0.9rem", color: "var(--text-dim)", fontWeight: 500 }}>设置密码</label>
                            <input
                                type="password"
                                required
                                value={data.password}
                                onChange={(e) => setData({ ...data, password: e.target.value })}
                                placeholder="至少 8 位包含字母与数字"
                                style={{
                                    width: "100%", padding: "1rem 1.2rem", background: "rgba(0, 0, 0, 0.2)", border: "1px solid var(--border)", borderRadius: "var(--radius)", color: "var(--text)", fontSize: "1rem", transition: "all 0.2s"
                                }}
                                onFocus={(e) => (e.target.style.borderColor = "var(--primary)")}
                                onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="glow"
                            style={{
                                marginTop: "1rem",
                                width: "100%",
                                padding: "1.1rem",
                                background: "linear-gradient(135deg, var(--primary), var(--accent))",
                                color: "white",
                                borderRadius: "var(--radius)",
                                fontSize: "1.05rem",
                                fontWeight: 600,
                                display: "flex",
                                justifyContent: "center",
                                alignItems: "center",
                                gap: "0.5rem",
                                opacity: loading ? 0.7 : 1,
                                transform: loading ? "scale(0.98)" : "scale(1)",
                            }}
                        >
                            {loading ? <Loader2 className="animate-spin" /> : "开启健康之旅"}
                        </button>
                    </form>

                    <p style={{ textAlign: "center", color: "var(--text-dim)", fontSize: "0.95rem" }}>
                        已有账号？{" "}
                        <button onClick={() => router.push("/login")} style={{ color: "var(--primary)", fontWeight: 600 }}>
                            直接登录
                        </button>
                    </p>
                </motion.div>
            </div>
        </div>
    );
}
