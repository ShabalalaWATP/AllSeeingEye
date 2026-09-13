import { http, HttpResponse } from 'msw';

import { ukraineBoard, ukraineControl } from './fixtures.ukraine';
import { ukraineReference } from './fixtures.ukraineReference';

export const ukraineHandlers = [
  http.get('/api/conflicts/ukraine', () => HttpResponse.json(ukraineBoard)),
  http.get('/api/conflicts/ukraine/control', () => HttpResponse.json(ukraineControl)),
  http.get('/api/conflicts/ukraine/reference', () => HttpResponse.json(ukraineReference)),
  http.get('/api/conflicts/ukraine/images/:id.jpg', () =>
    HttpResponse.arrayBuffer(new Uint8Array([0xff, 0xd8, 0xff, 0xd9]).buffer, {
      headers: { 'Content-Type': 'image/jpeg' },
    }),
  ),
];
