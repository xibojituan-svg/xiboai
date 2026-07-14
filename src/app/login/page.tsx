"use client";

import { motion } from "framer-motion";
import { signIn } from "next-auth/react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";

export default function Login() {
    const router = useRouter();
    const [data, setData] = useState({ email: "", password: "" });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const loginUser = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");

        signIn("credentials", {
            ...data,
            redirect: false,
        }).then((callback) => {
            setLoading(false);
            if (callback?.error) {
                setError(callback.error);
            } else if (callback?.ok && !callback?.error) {
                router.push("/");
            }
        });
    };

    return (
        <div
            style={{
                minHeight: "100vh",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                position: "relative",
                background: "radial-gradient(circle at 10% 20%, rgba(10, 132, 255, 0.15) 0%, rgba(0, 0, 0, 1) 90%)",
                overflow: "hidden",
            }}
        >
            {/* Background Decorators */}
            <div style={{ position: "absolute", top: "-10%", right: "-10%", width: "50vw", height: "50vw", background: "radial-gradient(circle, rgba(94, 92, 230, 0.4) 0%, transparent 60%)", filter: "blur(100px)", zIndex: 0 }} />
            <div style={{ position: "absolute", bottom: "-20%", left: "-10%", width: "60vw", height: "60vw", background: "radial-gradient(circle, rgba(48, 209, 88, 0.15) 0%, transparent 60%)", filter: "blur(120px)", zIndex: 0 }} />

            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.6, ease: "easeOut" }}
                className="glass animate-fade"
                style={{
                    width: "100%",
                    maxWidth: "460px",
                    padding: "3rem",
                    borderRadius: "var(--radius-lg)",
                    zIndex: 10,
                    display: "flex",
                    flexDirection: "column",
                    gap: "2rem",
                    boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
                }}
            >
                <button
                    onClick={() => router.push("/")}
                    style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--text-dim)", alignSelf: "flex-start", fontSize: "0.9rem" }}
                >
                    <ArrowLeft size={16} /> 返回首页
                </button>

                <div style={{ textAlign: "center" }}>
                    <h1 className="gradient-text" style={{ fontSize: "2.5rem", fontWeight: 700, marginBottom: "0.5rem", letterSpacing: "-0.02em" }}>欢迎回来</h1>
                    <p style={{ color: "var(--text-dim)", fontSize: "1.1rem" }}>登录您的喜畔健康中心账户</p>
                </div>

                {error && (
                    <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} style={{ padding: "1rem", background: "rgba(255, 59, 48, 0.1)", border: "1px solid rgba(255, 59, 48, 0.3)", borderRadius: "var(--radius)", color: "#ff453a", fontSize: "0.9rem", textAlign: "center" }}>
                        {error}
                    </motion.div>
                )}

                <form onSubmit={loginUser} style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                        <label style={{ fontSize: "0.9rem", color: "var(--text-dim)", fontWeight: 500 }}>电子邮箱</label>
                        <input
                            type="email"
                            required
                            value={data.email}
                            onChange={(e) => setData({ ...data, email: e.target.value })}
                            style={{
                                width: "100%",
                                padding: "1rem 1.2rem",
                                background: "rgba(0, 0, 0, 0.2)",
                                border: "1px solid var(--border)",
                                borderRadius: "var(--radius)",
                                color: "var(--text)",
                                fontSize: "1rem",
                                transition: "all 0.2s",
                            }}
                            placeholder="hello@example.com"
                            onFocus={(e) => (e.target.style.borderColor = "var(--primary)")}
                            onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
                        />
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                        <label style={{ fontSize: "0.9rem", color: "var(--text-dim)", fontWeight: 500, display: "flex", justifyContent: "space-between" }}>
                            密码
                            <a href="#" style={{ color: "var(--primary)", fontWeight: 400 }}>忘记密码？</a>
                        </label>
                        <input
                            type="password"
                            required
                            value={data.password}
                            onChange={(e) => setData({ ...data, password: e.target.value })}
                            style={{
                                width: "100%",
                                padding: "1rem 1.2rem",
                                background: "rgba(0, 0, 0, 0.2)",
                                border: "1px solid var(--border)",
                                borderRadius: "var(--radius)",
                                color: "var(--text)",
                                fontSize: "1rem",
                                transition: "all 0.2s",
                            }}
                            placeholder="••••••••"
                            onFocus={(e) => (e.target.style.borderColor = "var(--primary)")}
                            onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="glow"
                        style={{
                            marginTop: "0.5rem",
                            width: "100%",
                            padding: "1rem",
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
                        {loading ? <Loader2 className="animate-spin" /> : "立即登录"}
                    </button>
                </form>

                <p style={{ textAlign: "center", color: "var(--text-dim)", fontSize: "0.95rem" }}>
                    还没有账号？{" "}
                    <button onClick={() => router.push("/register")} style={{ color: "var(--primary)", fontWeight: 600 }}>
                        立即注册
                    </button>
                </p>
            </motion.div>
        </div>
    );
}
