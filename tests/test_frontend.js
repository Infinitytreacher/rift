// SPDX-FileCopyrightText: 2026 Siddhant Tiwari
// SPDX-License-Identifier: AGPL-3.0-only
// Run with: node --test tests/test_frontend.js

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const root = path.resolve(__dirname, '..');
const appSource = fs.readFileSync(path.join(root, 'static/app.js'), 'utf8');

function loadUtilities(fetch) {
    const context = vm.createContext({ window: {}, FormData, fetch });
    vm.runInContext(appSource, context);
    return context.window.FeedbackSystem;
}

test('JSON requests keep the JSON content type', async () => {
    let options;
    const api = loadUtilities(async (url, opts) => {
        options = opts;
        return new Response('{"success":true}', { headers: { 'Content-Type': 'application/json' } });
    });
    const response = await api.fetchAPI('/submit-feedback', { method: 'POST', body: '{}' });
    assert.equal(response.success, true);
    assert.equal(options.headers['Content-Type'], 'application/json');
});

test('multipart uploads let the browser create the content type boundary', async () => {
    let options;
    const api = loadUtilities(async (url, opts) => {
        options = opts;
        return new Response('{"success":true}', { headers: { 'Content-Type': 'application/json' } });
    });
    await api.uploadAudio(new File(['synthetic'], 'synthetic.wav', { type: 'audio/wav' }));
    assert.equal(options.headers['Content-Type'], undefined);
    assert.ok(options.body instanceof FormData);
});

test('API errors preserve the server error message', async () => {
    const api = loadUtilities(async () => new Response('{"error":"Synthetic validation failure"}', {
        status: 400, headers: { 'Content-Type': 'application/json' },
    }));
    await assert.rejects(api.fetchAPI('/synthetic'), { message: 'Synthetic validation failure' });
});

test('inline browser scripts parse and pages expose legal notices', () => {
    for (const filename of ['student.html', 'record.html', 'dashboard.html', 'topic-details.html']) {
        const html = fs.readFileSync(path.join(root, 'static', filename), 'utf8');
        for (const match of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) {
            new vm.Script(match[1], { filename });
        }
        assert.ok(html.includes('href="/source"'));
        assert.ok(html.includes('href="/license"'));
        assert.ok(html.includes('SPDX-License-Identifier: AGPL-3.0-only'));
    }
});

test('untrusted query parameters and errors are escaped before HTML interpolation', () => {
    const details = fs.readFileSync(path.join(root, 'static/topic-details.html'), 'utf8');
    assert.ok(details.includes('${escapeHtml(rawIdParam)}'));
    for (const filename of ['student.html', 'dashboard.html']) {
        const html = fs.readFileSync(path.join(root, 'static', filename), 'utf8');
        assert.ok(!html.includes('${error.message}'));
    }
});
