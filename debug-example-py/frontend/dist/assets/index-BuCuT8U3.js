import{u as g,j as e,C as f,a as y}from"./copilotkit-CDxiLL3x.js";import{a as N,r as o,R as b}from"./vendor-Mhodlkjv.js";(function(){const a=document.createElement("link").relList;if(a&&a.supports&&a.supports("modulepreload"))return;for(const s of document.querySelectorAll('link[rel="modulepreload"]'))c(s);new MutationObserver(s=>{for(const t of s)if(t.type==="childList")for(const i of t.addedNodes)i.tagName==="LINK"&&i.rel==="modulepreload"&&c(i)}).observe(document,{childList:!0,subtree:!0});function l(s){const t={};return s.integrity&&(t.integrity=s.integrity),s.referrerPolicy&&(t.referrerPolicy=s.referrerPolicy),s.crossOrigin==="use-credentials"?t.credentials="include":s.crossOrigin==="anonymous"?t.credentials="omit":t.credentials="same-origin",t}function c(s){if(s.ep)return;s.ep=!0;const t=l(s);fetch(s.href,t)}})();var p={},u=N;p.createRoot=u.createRoot,p.hydrateRoot=u.hydrateRoot;/**
 * @license lucide-react v0.400.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const v=r=>r.replace(/([a-z0-9])([A-Z])/g,"$1-$2").toLowerCase(),j=(...r)=>r.filter((a,l,c)=>!!a&&c.indexOf(a)===l).join(" ");/**
 * @license lucide-react v0.400.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */var k={xmlns:"http://www.w3.org/2000/svg",width:24,height:24,viewBox:"0 0 24 24",fill:"none",stroke:"currentColor",strokeWidth:2,strokeLinecap:"round",strokeLinejoin:"round"};/**
 * @license lucide-react v0.400.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const w=o.forwardRef(({color:r="currentColor",size:a=24,strokeWidth:l=2,absoluteStrokeWidth:c,className:s="",children:t,iconNode:i,...d},m)=>o.createElement("svg",{ref:m,...k,width:a,height:a,stroke:r,strokeWidth:c?Number(l)*24/Number(a):l,className:j("lucide",s),...d},[...i.map(([n,x])=>o.createElement(n,x)),...Array.isArray(t)?t:[t]]));/**
 * @license lucide-react v0.400.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const h=(r,a)=>{const l=o.forwardRef(({className:c,...s},t)=>o.createElement(w,{ref:t,iconNode:a,className:j(`lucide-${v(r)}`,c),...s}));return l.displayName=`${r}`,l};/**
 * @license lucide-react v0.400.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const A=h("Activity",[["path",{d:"M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2",key:"169zse"}]]);/**
 * @license lucide-react v0.400.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const S=h("Database",[["ellipse",{cx:"12",cy:"5",rx:"9",ry:"3",key:"msslwz"}],["path",{d:"M3 5V19A9 3 0 0 0 21 19V5",key:"1wlel7"}],["path",{d:"M3 12A9 3 0 0 0 21 12",key:"mv7ke4"}]]);/**
 * @license lucide-react v0.400.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const C=h("MessageSquare",[["path",{d:"M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",key:"1lielz"}]]);/**
 * @license lucide-react v0.400.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const R=h("Settings",[["path",{d:"M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z",key:"1qme2f"}],["circle",{cx:"12",cy:"12",r:"3",key:"1v7zrd"}]]);function V(){const[r,a]=o.useState("loading"),[l,c]=o.useState([]),[s,t]=o.useState(null);return o.useEffect(()=>{const i=async()=>{try{const n=await fetch("http://localhost:3001/health");if(n.ok){a("connected");const x=await n.json();t(x)}else a("disconnected")}catch{a("disconnected")}},d=async()=>{try{const n=await fetch("http://localhost:3001/api/actions");if(n.ok){const x=await n.json();c(x.actions)}}catch(n){console.error("获取 Actions 失败:",n)}};i(),d();const m=setInterval(i,3e4);return()=>clearInterval(m)},[]),g({name:"showNotification",description:"显示前端通知消息",parameters:[{name:"message",description:"通知消息内容",type:"string",required:!0},{name:"type",description:"通知类型: success, error, warning, info",type:"string",required:!1}],handler:({message:i,type:d="info"})=>(alert(`${d.toUpperCase()}: ${i}`),`已显示通知: ${i}`)}),e.jsxs("div",{className:"flex h-screen bg-gradient-to-br from-blue-50 to-indigo-100",style:{"--copilot-kit-primary-color":"#3b82f6"},children:[e.jsxs("div",{className:"flex-1 flex flex-col",children:[e.jsx("header",{className:"bg-white shadow-sm border-b p-4",children:e.jsxs("div",{className:"flex items-center justify-between",children:[e.jsxs("div",{className:"flex items-center space-x-3",children:[e.jsx(C,{className:"text-blue-600",size:24}),e.jsx("h1",{className:"text-xl font-semibold text-gray-800",children:"CopilotKit Debug Example (DeepSeek + Vite)"}),e.jsx("span",{className:`status-indicator ${r}`}),e.jsxs("span",{className:"text-sm text-gray-600",children:["后端状态: ",r==="connected"?"已连接":r==="disconnected"?"断开连接":"连接中..."]})]}),e.jsxs("div",{className:"text-sm text-gray-500",children:["可用 Actions: ",l.length]})]})}),e.jsx("main",{className:"flex-1 p-6",children:e.jsxs("div",{className:"max-w-4xl mx-auto",children:[e.jsxs("div",{className:"bg-white rounded-lg shadow-lg p-6 mb-6",children:[e.jsxs("h2",{className:"text-lg font-semibold mb-4 flex items-center",children:[e.jsx(R,{className:"mr-2",size:20}),"调试信息"]}),e.jsxs("div",{className:"grid grid-cols-1 md:grid-cols-2 gap-4",children:[e.jsxs("div",{className:"debug-panel p-4",children:[e.jsxs("h3",{className:"flex items-center",children:[e.jsx(A,{className:"mr-2",size:16}),"后端健康状态"]}),s?e.jsx("pre",{className:"text-xs",children:JSON.stringify(s,null,2)}):e.jsx("p",{className:"text-gray-500",children:"获取中..."})]}),e.jsxs("div",{className:"debug-panel p-4",children:[e.jsxs("h3",{className:"flex items-center",children:[e.jsx(S,{className:"mr-2",size:16}),"可用 Actions"]}),l.length>0?e.jsx("div",{className:"space-y-2",children:l.map((i,d)=>{var m;return e.jsxs("div",{className:"border rounded p-2 bg-gray-50",children:[e.jsx("div",{className:"font-medium text-sm",children:i.name}),e.jsx("div",{className:"text-xs text-gray-600",children:i.description}),e.jsxs("div",{className:"text-xs text-gray-500",children:["参数: ",((m=i.parameters)==null?void 0:m.length)||0]})]},d)})}):e.jsx("p",{className:"text-gray-500",children:"暂无可用 Actions"})]})]})]}),e.jsxs("div",{className:"bg-white rounded-lg shadow-lg p-6",children:[e.jsx("h2",{className:"text-lg font-semibold mb-4",children:"🔍 调试说明"}),e.jsxs("div",{className:"space-y-4 text-sm text-gray-600",children:[e.jsxs("div",{children:[e.jsx("h3",{className:"font-medium text-gray-800 mb-2",children:"后端调试:"}),e.jsxs("ul",{className:"list-disc list-inside space-y-1",children:[e.jsxs("li",{children:["在 VS Code 中打开 ",e.jsx("code",{className:"bg-gray-100 px-1 rounded",children:"debug-example/backend/src/server.ts"})]}),e.jsx("li",{children:"设置断点在 CopilotRuntime 相关代码中"}),e.jsxs("li",{children:["运行 ",e.jsx("code",{className:"bg-gray-100 px-1 rounded",children:"npm run debug"})," 启动调试模式"]}),e.jsx("li",{children:"在浏览器中发送消息，触发断点进行调试"})]})]}),e.jsxs("div",{children:[e.jsx("h3",{className:"font-medium text-gray-800 mb-2",children:"测试 Actions:"}),e.jsxs("ul",{className:"list-disc list-inside space-y-1",children:[e.jsx("li",{children:'询问当前时间: "现在几点了？"'}),e.jsx("li",{children:'数学计算: "帮我计算 2 + 3 * 4"'}),e.jsx("li",{children:'查询用户: "查询用户ID为1的信息"'}),e.jsx("li",{children:'运行时状态: "获取运行时调试状态"'}),e.jsx("li",{children:'前端通知: "显示一个成功通知"'})]})]}),e.jsxs("div",{children:[e.jsx("h3",{className:"font-medium text-gray-800 mb-2",children:"Runtime 调试:"}),e.jsxs("ul",{className:"list-disc list-inside space-y-1",children:[e.jsxs("li",{children:["在 ",e.jsx("code",{className:"bg-gray-100 px-1 rounded",children:"CopilotKit/packages/runtime"})," 中设置断点"]}),e.jsxs("li",{children:["特别关注 ",e.jsx("code",{className:"bg-gray-100 px-1 rounded",children:"copilot-runtime.ts"})," 的 ",e.jsx("code",{className:"bg-gray-100 px-1 rounded",children:"processRuntimeRequest"})," 方法"]}),e.jsx("li",{children:"查看消息处理、Action 执行等核心流程"})]})]}),e.jsxs("div",{children:[e.jsx("h3",{className:"font-medium text-gray-800 mb-2",children:"Vite 特性:"}),e.jsxs("ul",{className:"list-disc list-inside space-y-1",children:[e.jsx("li",{children:"🚀 快速热重载 (HMR)"}),e.jsx("li",{children:"⚡ 极快的启动速度"}),e.jsx("li",{children:"📦 优化的构建输出"}),e.jsx("li",{children:"🔧 简化的配置"})]})]})]})]})]})})]}),e.jsx(f,{labels:{title:"AI 助手 (DeepSeek + Vite 调试模式)",initial:`👋 你好！我是 CopilotKit + DeepSeek + Vite 调试助手。

🔧 **调试功能:**
- 使用 DeepSeek Chat 模型
- 基于 Vite 构建，启动更快
- 可以执行多种自定义 Actions
- 后端使用 Express + CopilotKit Runtime + DeepSeek Adapter
- 你可以在代码中设置断点进行调试

💡 **试试问我:**
- "现在几点了？"
- "计算 10 + 20 * 3"
- "查询用户1的信息"
- "获取运行时状态"
- "显示一个通知"

⚡ **Vite 优势:**
- 极快的热重载
- 更快的开发体验

让我们开始调试吧！`,placeholder:"输入消息进行调试..."},defaultOpen:!0,clickOutsideToClose:!1,className:"w-96 border-l"})]})}function D(){return e.jsx(y,{runtimeUrl:"http://localhost:3001/api/copilotkit",publicApiKey:"",children:e.jsx(V,{})})}p.createRoot(document.getElementById("root")).render(e.jsx(b.StrictMode,{children:e.jsx(D,{})}));
//# sourceMappingURL=index-BuCuT8U3.js.map
