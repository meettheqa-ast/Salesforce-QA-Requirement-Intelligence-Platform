/**
 * Minimal typed client for the SFQA API.
 *
 * The token is held in memory + localStorage by the auth store (see auth.tsx).
 * This client is deliberately thin: in Sprint 1, generated types from
 * @sfqa/shared-types replace the hand-written response shapes here.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface DevTokenRequest {
  user_id: string;
  tenant_id: string;
  email?: string;
  role?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface WhoAmI {
  user_id: string;
  tenant_id: string;
  email: string;
  role: string;
}

async function request<T>(
  path: string,
  options: RequestInit & { token?: string } = {},
): Promise<T> {
  const { token, headers, ...rest } = options;
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      // non-JSON error body; keep statusText
    }
    throw new ApiError(res.status, detail);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  mintDevToken(body: DevTokenRequest): Promise<TokenResponse> {
    return request<TokenResponse>("/auth/dev-token", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  whoami(token: string): Promise<WhoAmI> {
    return request<WhoAmI>("/auth/me", { token });
  },
  health(): Promise<{ status: string }> {
    return request<{ status: string }>("/healthz");
  },
};
