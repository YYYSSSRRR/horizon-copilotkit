import React, { useState } from "react";
import { useLangGraphInterrupt } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";
import { Plus } from "lucide-react";

const HumanInTheLoopPage: React.FC = () => {
  // 直接复用demo-viewer的useLangGraphInterrupt实现
  useLangGraphInterrupt({
    render: ({ event, resolve }) => {
      const [newStep, setNewStep] = useState("");

      const handleAddStep = () => {
        const trimmed = newStep.trim();
        if (trimmed.length === 0) return;
        setLocalSteps((prevSteps: any) => [
          ...prevSteps,
          { description: trimmed, status: "enabled" },
        ]);
        setNewStep("");
      };

      const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter") {
          handleAddStep();
        }
      };
      
      // 确保有有效的步骤数据
      let initialSteps: any[] = [];
      if (event.value && event.value.steps && Array.isArray(event.value.steps)) {
        initialSteps = event.value.steps.map((step: any) => ({
          description: typeof step === 'string' ? step : step.description || '',
          status: (typeof step === 'object' && step.status) ? step.status : 'enabled'
        }));
      }

      const [localSteps, setLocalSteps] = useState<{
        description: string;
        status: "disabled" | "enabled" | "executing";
      }[]>(initialSteps);

      const handleCheckboxChange = (index: number) => {
        setLocalSteps((prevSteps) =>
          prevSteps.map((step, i) =>
            i === index
              ? {
                ...step,
                status: step.status === "enabled" ? "disabled" : "enabled",
              }
              : step
          )
        );
      };

      return (
        <div className="flex flex-col gap-4 w-[500px] bg-gray-100 rounded-lg p-8 mb-4">
          <div className="text-black space-y-2">
            <h2 className="text-lg font-bold mb-4">选择任务步骤</h2>
            {localSteps.map((step, index) => (
              <div key={index} className="text-sm flex items-center">
                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={step.status === "enabled"}
                    onChange={() => handleCheckboxChange(index)}
                    className="mr-2"
                  />
                  <span
                    className={
                      step.status !== "enabled" ? "line-through" : ""
                    }
                  >
                    {step.description}
                  </span>
                </label>
              </div>
            ))}
            <div className="flex items-center gap-2 mb-4">
              <input
                type="text"
                className="flex-1 rounded py-2 px-3 focus:outline-none"
                placeholder="添加新步骤..."
                value={newStep}
                onChange={(e) => setNewStep(e.target.value)}
                onKeyDown={handleInputKeyDown}
              />
              <button
                onClick={handleAddStep}
                disabled={!newStep.trim()}
                className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center space-x-1"
              >
                <Plus size={16} />
                <span>添加</span>
              </button>
            </div>
            <button
              className="mt-4 bg-gradient-to-r from-purple-400 to-purple-600 text-white py-2 px-4 rounded cursor-pointer w-48 font-bold"
              onClick={() => {
                const selectedSteps = localSteps
                  .filter((step) => step.status === "enabled")
                  .map((step) => step.description);
                resolve("用户选择了以下步骤: " + selectedSteps.join(", "));
              }}
            >
              ✨ 执行选定步骤
            </button>
          </div>
        </div>
      );
    },
  });

  return (
    <div className="flex justify-center items-center h-screen w-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="w-4/5 h-4/5">
        <CopilotSidebar
          labels={{
            title: "AI 助手 (LangGraph Human-in-the-Loop)",
            initial: "👋 你好！我是支持 Human-in-the-Loop 的AI助手。\n\n🗺️ **功能特色:**\n- 使用真正的 LangGraph 后端\n- Human-in-the-Loop 任务确认\n- 步骤选择和自定义\n\n💡 **试试问我:**\n- \"帮我规划学习Python的步骤\"\n- \"制定一个网站开发计划\"\n- \"给我一个减肥的行动方案\"\n- \"帮我安排搬家的任务清单\"\n\n🔄 **工作流程:**\n1. 我会为您的任务生成步骤\n2. 您可以选择、修改步骤\n3. 确认后我会根据您的选择提供指导\n\n让我们开始吧！",
            placeholder: "输入您的任务或请求...",
          }}
          defaultOpen={true}
          clickOutsideToClose={false}
          className="w-full border rounded-lg"
          instructions="你是一个任务规划助手。当用户请求帮助时，你需要调用 generate_task_steps 函数为他们生成可行的步骤列表。确保步骤具体、可执行。"
        />
      </div>
    </div>
  );
};

export default HumanInTheLoopPage;