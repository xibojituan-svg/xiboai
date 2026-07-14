import type { Metadata } from "next";
import "./globals.css";
import AuthProvider from "./providers";

export const metadata: Metadata = {
  title: "喜畔健康 | AI 驱动个性化健康综合解决方案",
  description: "基于人工智能的喜畔健康预测与综合解决方案平台，守护每一位用户的长久健康。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
