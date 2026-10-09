/** Provider details are local text and links; reading them makes no provider request. */
export const embedProviders = {
  tradingview: {
    name: 'TradingView',
    privacyUrl: 'https://www.tradingview.com/privacy-policy/',
    shared: 'your IP address, browser details and the selected public market symbol',
  },
  youtube: {
    name: 'YouTube',
    privacyUrl: 'https://policies.google.com/privacy',
    shared: 'your IP address, browser details and the selected video',
  },
  ipcamlive: {
    name: 'IPCamLive',
    privacyUrl: 'https://www.ipcamlive.com/privacy',
    shared: 'your IP address, browser details and the selected camera',
  },
} as const;

export type EmbedProvider = keyof typeof embedProviders;
export const embedProviderIds = Object.keys(embedProviders) as EmbedProvider[];
