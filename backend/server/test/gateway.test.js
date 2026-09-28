import { test, describe, before, after } from 'node:test';
import assert from 'node:assert';
import http from 'node:http';
import { createApp } from '../src/app.js';
import { orcaQuerySchema } from '../src/validators/orcaSchemas.js';

describe('ORCA Server Test Suite', () => {
  let server;
  let baseUrl;

  before((_, done) => {
    const app = createApp();
    server = http.createServer(app);
    server.listen(0, () => {
      const addr = server.address();
      if (addr && typeof addr === 'object') {
        baseUrl = `http://127.0.0.1:${addr.port}`;
      }
      done();
    });
  });

  after((_, done) => {
    server.close(done);
  });

  test('GET /health returns 200 and healthy JSON response', async () => {
    const res = await fetch(`${baseUrl}/health`);
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.status, 'ok');
    assert.strictEqual(data.service, 'orca-gateway');
    assert.ok(data.components);
    assert.ok(data.timestamp);
  });

  test('GET /api/v1/health returns 200 and structured service status', async () => {
    const res = await fetch(`${baseUrl}/api/v1/health`);
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.status, 'ok');
    assert.strictEqual(data.service, 'orca-gateway');
  });

  test('GET unknown route returns 404 with structured error response', async () => {
    const res = await fetch(`${baseUrl}/api/v1/unknown-endpoint-xyz`);
    assert.strictEqual(res.status, 404);
    const data = await res.json();
    assert.strictEqual(data.success, false);
    assert.ok(data.error);
    assert.strictEqual(data.error.code, 'NOT_FOUND');
  });

  test('orcaQuerySchema validates correct query payload', () => {
    const valid = {
      query: 'Is it safe to depart from Sassoon Docks Mumbai?',
      location: { latitude: 18.92, longitude: 72.83, name: 'Sassoon Docks' },
      userProfile: { role: 'fisherman', vesselClass: 'motorized_fiberglass', language: 'en' },
    };
    const parsed = orcaQuerySchema.parse(valid);
    assert.strictEqual(parsed.query, valid.query);
    assert.strictEqual(parsed.location?.latitude, 18.92);
  });

  test('orcaQuerySchema rejects invalid or empty query payload', () => {
    const invalid = {
      query: '', // Empty query is invalid
    };
    assert.throws(() => {
      orcaQuerySchema.parse(invalid);
    });
  });
});
