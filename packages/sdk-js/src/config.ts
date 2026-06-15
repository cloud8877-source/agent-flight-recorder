export type RecorderConfig = {
  appName: string;
  environment: string;
  endpoint: string;
  apiKey?: string;
};

let config: RecorderConfig | null = null;

export function setConfig(next: RecorderConfig): void {
  config = next;
}

export function getConfig(): RecorderConfig {
  if (!config) {
    throw new Error("recorder.init() must be called before using the SDK");
  }
  return config;
}

export function loadFromEnv(appName: string, environment: string): RecorderConfig {
  return {
    appName,
    environment,
    endpoint: (process.env.AFR_ENDPOINT ?? "http://localhost:4318").replace(/\/$/, ""),
    apiKey: process.env.AFR_API_KEY,
  };
}