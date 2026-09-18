export const READING_ASSIST_ZHUYIN_KEY = "ai-guard-reading-assist-zhuyin";

export type ReadingAssistState = {
  zhuyinEnabled: boolean;
  setZhuyinEnabled: (enabled: boolean) => void;
  toggleZhuyin: () => void;
};
