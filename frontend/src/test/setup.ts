import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./server";

// jsdom에는 스크롤이 없다(ScrollRestoration이 부름)
window.scrollTo = () => undefined;

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  cleanup();
  window.localStorage.clear();
});
afterAll(() => server.close());
