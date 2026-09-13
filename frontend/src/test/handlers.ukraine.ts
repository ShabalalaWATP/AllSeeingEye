import { http, HttpResponse } from 'msw';

import { ukraineBoard, ukraineControl } from './fixtures.ukraine';

export const ukraineHandlers = [
  http.get('/api/conflicts/ukraine', () => HttpResponse.json(ukraineBoard)),
  http.get('/api/conflicts/ukraine/control', () => HttpResponse.json(ukraineControl)),
];
