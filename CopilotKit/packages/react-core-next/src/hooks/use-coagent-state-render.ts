import { useEffect, useRef } from "react";
import { randomId } from "@copilotkit/shared";
import { useCopilotCoAgentStateRenders } from "../context/copilot-context";
import { CoAgentStateRender } from "../types/coagent-action";

/**
 * CoAgent 状态渲染 Hook，用于注册自定义的状态渲染器
 * 
 * @param render CoAgent 状态渲染配置
 * @param dependencies 依赖数组，当依赖变化时重新注册渲染器
 */
export function useCoAgentStateRender<T = any>(
  render: CoAgentStateRender<T>,
  dependencies?: React.DependencyList
) {
  const { setCoAgentStateRender, removeCoAgentStateRender } = useCopilotCoAgentStateRenders();
  const renderIdRef = useRef<string>();

  useEffect(() => {
    // 生成唯一的渲染器 ID
    if (!renderIdRef.current) {
      renderIdRef.current = `coagent-render-${render.name}-${render.nodeName || 'default'}-${randomId()}`;
    }

    const renderId = renderIdRef.current;

    // 注册渲染器
    setCoAgentStateRender(renderId, render);

    // 清理函数：移除渲染器
    return () => {
      removeCoAgentStateRender(renderId);
    };
  }, dependencies ? [...dependencies, render.name, render.nodeName] : [render.name, render.nodeName, render.render, render.handler]);

  // 返回渲染器 ID
  return renderIdRef.current;
} 