import { expect, it } from 'vitest';
import { cameraEmbed } from './cameraEmbed';
import { isCameraStreamUrl } from './cameras';

it('accepts catalogue YouTube URLs but renders only the privacy-enhanced host', () => {
  const source = 'https://www.youtube.com/embed/UemFRPrl1hk?autoplay=1&mute=1';
  expect(isCameraStreamUrl(source, true)).toBe(true);
  const target = cameraEmbed(source);
  expect(target).toEqual({
    provider: 'youtube',
    url: source.replace('www.youtube.com', 'www.youtube-nocookie.com'),
  });
  expect(cameraEmbed(target!.url)).toEqual(target);
  expect(isCameraStreamUrl(target!.url, true)).toBe(true);
});

it('keeps the approved IPCamLive player destination', () => {
  const url = 'https://ipcamlive.com/player/player.php?alias=publiccamera';
  expect(cameraEmbed(url)).toEqual({ provider: 'ipcamlive', url });
});

it.each([
  null,
  '',
  'http://www.youtube.com/embed/UemFRPrl1hk',
  'https://www.youtube.com.evil.test/embed/UemFRPrl1hk',
  'https://user:secret@www.youtube.com/embed/UemFRPrl1hk',
  'https://www.youtube.com:8443/embed/UemFRPrl1hk',
  'https://www.youtube.com/watch?v=UemFRPrl1hk',
  'https://www.youtube-nocookie.com/embed/invalid',
  'https://ipcamlive.com/other',
  'https://pics.smartburgas.eu/embed/UemFRPrl1hk',
])('refuses unsupported input %s', (value) => expect(cameraEmbed(value)).toBeNull());
