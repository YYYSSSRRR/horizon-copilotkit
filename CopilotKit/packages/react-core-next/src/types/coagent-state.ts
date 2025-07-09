export interface CoagentState {
  /**
   * The name of the coagent.
   */
  name: string;

  /**
   * The current state data of the coagent.
   */
  state: any;

  /**
   * Whether the coagent is currently running.
   */
  running: boolean;

  /**
   * The thread ID associated with this coagent.
   */
  threadId: string;

  /**
   * The current node name in the coagent's workflow.
   */
  nodeName?: string;

  /**
   * The run ID of the current execution.
   */
  runId?: string;

  /**
   * Whether the coagent is active.
   */
  active: boolean;

  /**
   * Additional metadata for the coagent.
   */
  metadata?: Record<string, any>;

  /**
   * Timestamp when the state was last updated.
   */
  lastUpdated?: Date;
} 