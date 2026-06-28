import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ChenForge AI | 企业 AI Agent 落地咨询与交付",
  description:
    "ChenForge AI 为企业设计、构建并交付可监控、可审批、可持续迭代的 AI Agent 系统。",
  openGraph: {
    title: "ChenForge AI | 企业 AI Agent 落地咨询与交付",
    description:
      "由资深软件工程师主导，帮助企业把重复流程、知识问答、数据查询和运营动作，改造成可监控、可审批、可持续迭代的 AI Agent 系统。",
    type: "website",
    locale: "zh_CN",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <div className="grain" aria-hidden="true" />
        {children}
      </body>
    </html>
  );
}
