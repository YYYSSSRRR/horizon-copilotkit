export interface CoAgentStateRenderHandlerArguments {
  /**
   * The name of the coagent.
   */
  name: string;

  /**
   * The name of the current node.
   */
  nodeName?: string;

  /**
   * The state of the coagent.
   */
  state: any;

  /**
   * The running status of the coagent.
   */
  running?: boolean;

  /**
   * Additional metadata.
   */
  metadata?: Record<string, any>;
}

export interface CoAgentStateRender<T = any> {
  /**
   * The name of the coagent this render is for.
   */
  name: string;

  /**
   * The name of the node this render is for.
   */
  nodeName?: string;

  /**
   * The handler function to render the coagent state.
   */
  handler?: (args: CoAgentStateRenderHandlerArguments) => Promise<void> | void;

  /**
   * A render function for the coagent state.
   */
  render?: (props: CoAgentStateRenderProps<T>) => React.ReactElement | string | null | undefined;
}

export interface CoAgentStateRenderProps<T = any> {
  /**
   * The state of the coagent.
   */
  state: T;

  /**
   * The name of the current node.
   */
  nodeName?: string;

  /**
   * The running status of the coagent.
   */
  running?: boolean;

  /**
   * Additional metadata.
   */
  metadata?: Record<string, any>;
} 