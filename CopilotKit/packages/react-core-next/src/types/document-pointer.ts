export interface DocumentPointer {
  name: string;
  sourceApplication: string;
  getContents(): string;
  relativePosition?: {
    startPercentage: number;
    endPercentage: number;
  };
} 