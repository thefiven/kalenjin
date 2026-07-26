import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";
import { proxy } from "@/proxy";

function makeRequest(path: string, cookie?: string): NextRequest {
  const headers = new Headers();
  if (cookie) headers.set("cookie", cookie);
  return new NextRequest(new Request(`http://localhost:3000${path}`, { headers }));
}

describe("proxy", () => {
  it("redirects an unauthenticated visitor to /login", () => {
    const response = proxy(makeRequest("/dashboard"));

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost:3000/login");
  });

  it("passes an authenticated visitor through to the requested page", () => {
    const response = proxy(makeRequest("/dashboard", "kalenjin_session=abc"));

    expect(response.headers.get("location")).toBeNull();
  });

  it("does not redirect an unauthenticated visitor away from /login", () => {
    const response = proxy(makeRequest("/login"));

    expect(response.headers.get("location")).toBeNull();
  });

  it("redirects an already-authenticated visitor away from /login", () => {
    const response = proxy(makeRequest("/login", "kalenjin_session=abc"));

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost:3000/");
  });
});
