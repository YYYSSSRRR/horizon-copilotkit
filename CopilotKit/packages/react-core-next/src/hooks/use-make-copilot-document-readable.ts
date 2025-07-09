import { useEffect, useRef } from "react";
import { useCopilotDocumentPointers } from "../context/copilot-context";
import { DocumentPointer } from "../types/document-pointer";
import { randomId } from "@copilotkit/shared";

/**
 * 使文档对 Copilot 可读的 Hook
 * 
 * @param document 要使其可读的文档
 * @param categories 与文档关联的分类
 * @param dependencies 用于重新注册的依赖数组
 * @returns 文档的 ID
 */
export function useMakeCopilotDocumentReadable(
  document: DocumentPointer,
  categories?: string[],
  dependencies: any[] = [],
): string | undefined {
  const { setDocumentPointer, removeDocumentPointer } = useCopilotDocumentPointers();
  const idRef = useRef<string>();

  useEffect(() => {
    // 生成文档 ID
    if (!idRef.current) {
      idRef.current = `document-${randomId()}`;
    }

    const id = idRef.current;

    // 添加文档指针
    setDocumentPointer(id, {
      ...document,
      // 可以在这里添加分类信息到文档的元数据中
      sourceApplication: document.sourceApplication + (categories ? ` [${categories.join(', ')}]` : ''),
    });

    return () => {
      removeDocumentPointer(id);
    };
  }, [setDocumentPointer, removeDocumentPointer, document.name, document.sourceApplication, ...dependencies]);

  return idRef.current;
} 