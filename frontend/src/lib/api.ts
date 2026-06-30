import { getAccessToken, refreshAccessToken, clearTokens } from "./auth";

export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: { code: string; message: string } | null;
  timestamp: string;
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
  const headers = new Headers(options.headers || {});

  // Attach token if exists
  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const fetchOptions: RequestInit = {
    ...options,
    headers,
  };

  try {
    let response = await fetch(path, fetchOptions);

    // 401 Unauthorized handling
    if (response.status === 401) {
      const newAccessToken = await refreshAccessToken();
      if (newAccessToken) {
        // Retry once with new token
        headers.set("Authorization", `Bearer ${newAccessToken}`);
        response = await fetch(path, fetchOptions);
      } else {
        if (typeof window !== "undefined") {
          clearTokens();
          window.location.href = "/login";
        }
        throw new Error("Session expired. Please login again.");
      }
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        success: false,
        data: null,
        error: {
          code: errorData.error?.code || "HTTP_ERROR",
          message: errorData.error?.message || errorData.detail || `HTTP error! Status: ${response.status}`,
        },
        timestamp: new Date().toISOString(),
      };
    }

    return await response.json();
  } catch (error: any) {
    return {
      success: false,
      data: null,
      error: {
        code: "CONNECTION_FAILED",
        message: error.message || "Could not connect to the API server",
      },
      timestamp: new Date().toISOString(),
    };
  }
}
