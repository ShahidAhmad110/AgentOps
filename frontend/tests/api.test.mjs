import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError, apiRequest } from "../lib/api.ts";

test("apiRequest sends the bearer token and JSON content type", async (context) => {
  context.mock.method(globalThis, "fetch", async (_url, init) => {
    assert.equal(new Headers(init.headers).get("Authorization"), "Bearer session-token");
    assert.equal(new Headers(init.headers).get("Content-Type"), "application/json");
    assert.equal(init.body, JSON.stringify({ request: "hello" }));
    return new Response(JSON.stringify({ status: "completed" }), { status: 200 });
  });

  const result = await apiRequest("/agent", "session-token", {
    method: "POST",
    body: JSON.stringify({ request: "hello" }),
  });

  assert.deepEqual(result, { status: "completed" });
});

test("apiRequest leaves multipart content type to the browser", async (context) => {
  context.mock.method(globalThis, "fetch", async (_url, init) => {
    assert.equal(new Headers(init.headers).has("Content-Type"), false);
    assert.ok(init.body instanceof FormData);
    return new Response(JSON.stringify({ filename: "policy.md" }), { status: 201 });
  });

  const form = new FormData();
  form.set("file", new Blob(["policy"]), "policy.md");
  const result = await apiRequest("/documents", "session-token", { method: "POST", body: form });

  assert.deepEqual(result, { filename: "policy.md" });
});

test("apiRequest preserves structured unauthorized errors", async (context) => {
  context.mock.method(globalThis, "fetch", async () => new Response(
    JSON.stringify({ error: { code: "AUTHENTICATION_REQUIRED", message: "Authentication is required." } }),
    { status: 401 },
  ));

  await assert.rejects(
    apiRequest("/documents", "expired-token"),
    (error) => error instanceof ApiError && error.status === 401 && error.code === "AUTHENTICATION_REQUIRED",
  );
});

test("apiRequest reports backend messages for failed operations", async (context) => {
  context.mock.method(globalThis, "fetch", async () => new Response(
    JSON.stringify({ error: { code: "DOCUMENT_ERROR", message: "Only PDF, TXT, and Markdown documents are supported." } }),
    { status: 400 },
  ));

  await assert.rejects(
    apiRequest("/documents", "session-token"),
    (error) => error instanceof ApiError && error.status === 400 && error.message.includes("Only PDF, TXT, and Markdown"),
  );
});

test("apiRequest reports network failures without exposing internals", async (context) => {
  context.mock.method(globalThis, "fetch", async () => {
    throw new TypeError("socket internals");
  });

  await assert.rejects(
    apiRequest("/tasks", "session-token"),
    (error) => error instanceof ApiError && error.code === "NETWORK_ERROR" && !error.message.includes("socket internals"),
  );
});

test("authenticated 401 responses notify the workspace to invalidate its session", async (context) => {
  const originalWindow = globalThis.window;
  const events = [];
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: { dispatchEvent: (event) => events.push(event) },
  });
  context.after(() => {
    if (originalWindow === undefined) delete globalThis.window;
    else Object.defineProperty(globalThis, "window", { configurable: true, value: originalWindow });
  });
  context.mock.method(globalThis, "fetch", async () => new Response(
    JSON.stringify({ error: { code: "INVALID_TOKEN", message: "The access token is invalid." } }),
    { status: 401 },
  ));

  await assert.rejects(apiRequest("/tasks", "expired-session-token"), ApiError);
  assert.equal(events.length, 1);
  assert.equal(events[0].type, "agentops:unauthorized");
  assert.equal(events[0].detail.token, "expired-session-token");
});

test("apiRequest returns undefined for 204 No Content response", async (context) => {
  context.mock.method(globalThis, "fetch", async () => new Response(null, { status: 204 }));

  const result = await apiRequest("/tasks/task-123", "session-token", { method: "DELETE" });
  assert.equal(result, undefined);
});

test("apiRequest uses fallback status message when error payload has no message", async (context) => {
  context.mock.method(globalThis, "fetch", async () => new Response("Internal error", { status: 500 }));

  await assert.rejects(
    apiRequest("/tasks", "session-token"),
    (error) => error instanceof ApiError && error.status === 500 && error.message === "Request failed (500).",
  );
});

test("ApiError retains message, status, and code properties", () => {
  const error = new ApiError("Custom error", 403, "FORBIDDEN");
  assert.equal(error.name, "ApiError");
  assert.equal(error.message, "Custom error");
  assert.equal(error.status, 403);
  assert.equal(error.code, "FORBIDDEN");
});